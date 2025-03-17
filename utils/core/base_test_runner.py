import inspect
import sys
import time
import traceback
import datetime as dt
from collections import OrderedDict

import utils.test_utils as tu
import utils.process_utils as pu
import config.global_config
import config.runtime_config
import utils.core.configuration_specific as cs
import outputControl.logging_access as la
import outputControl.dom_objects as do
import config.verbosity_config as vc
import utils.mock.mock_executor as mexe

def lsort(someList):
    if config.global_config.leSort:
        return sorted(someList)
    return someList


# dont missplace with noarch architecture
NON_ARCH_TEST = "Non_Arch"


class Agregator():
    def __init__(self):
        self.lines = []

    def add(self, arch, method, string):
        la.LoggingAccess().log("for " + method + " on " + arch)
        self.lines.append((arch, method, string))
        la.LoggingAccess().log("  got: " + string)

    def agregate1(self):
        """Join all same documentations under set of architectures"""
        mapOfMaps = OrderedDict()
        for l in self.lines:
            if l[2] not in mapOfMaps:
                mapOfMaps[l[2]] = [l[0]]
            else:
                arches = mapOfMaps[l[2]]
                arches.append(l[0])
                sarches = sorted(set(arches))
                mapOfMaps[l[2]] = sarches
        return mapOfMaps

    def agregate2(self, mapOfArches):
        mapResults = OrderedDict()
        for key, svalue in mapOfArches.items():
            value = list(svalue)
            nwKey = None
            if len(value) == 0:
                nwKey = ("Everywhere(?):")
            else:
                if len(value) == 1 and value[0] == NON_ARCH_TEST:
                    nwKey = ("On all architectures:")
                else:
                    verboseKey = ",".join(value)
                    if ( len(value)>1 and
                        ((compareListLaniently(value,config.runtime_config.RuntimeConfig().getRpmList().getNativeArches())) or  #?
                        (compareListLaniently(value, config.runtime_config.RuntimeConfig().getRpmList().getRealNativeArches())))): #?
                        verboseKey = "On all tested architectures"
                    nwKey = ("On - " + verboseKey + ":")
            if nwKey not in mapResults:
                mapResults[nwKey] = [key]
            else:
                mapResults[nwKey].append(key)
        return mapResults

    def out(self):
        mapOfArches = self.agregate1()
        mapResults = self.agregate2(mapOfArches)
        for key, svalue in mapResults.items():
            la.LoggingAccess().stdout(key)
            for value in svalue:
                la.LoggingAccess().stdout(" - " + value)


class BaseTestRunner:
    def __init__(self):
        self.indent = ""
        # configuration specific checks
        self.csch = None
        self.current_arch = None

    def _cleanArchs(self):
        r = self.getTestedArchs()
        if r is None or len(r) == 0:
            return [NON_ARCH_TEST]
        else:
            return r

    def execute_tests(self):
        """Call all test_ prefixed methods in overwritting class"""
        pu.executeShell("mkdir -p jtregLogs")
        passed = 0
        failed = 0
        methodOnlyCounter = 0
        self.indent = "  "
        suiteStart = time.process_time()
        self.log("started tests in suite: " + type(self).__name__ + ":")
        archs = self._cleanArchs()
        methods = lsort(inspect.getmembers(self, predicate=inspect.ismethod))
        for i, arch in enumerate(archs):
            la.LoggingAccess().log("", vc.Verbosity.JTREG, type(self).__name__ + "_" + arch)
            self.current_arch = arch
            config.runtime_config.RuntimeConfig().current_arch = arch
            for a, b in methods:
                methodOnly = False
                if str(a).startswith("test_"):
                    methodStart = time.process_time()
                    if not methodOnly:
                        methodOnlyCounter += 1
                        methodOnly = True
                    self.indent = "    "
                    self.log("Setting configuration-specific-checks")
                    self.setCSCH()
                    self.log("using: " + str(type(self.csch).__name__))
                    self.log("running: " + a + "[" + self.current_arch + "] " + str(i + 1) + "/" + str(len(archs)))
                    self.indent = "      "
                    calllable = getattr(self, a)
                    try:
                        self.indent = "        "
                        p, f = calllable()
                        passed += p
                        failed += f
                        if f == 0:
                            la.LoggingAccess().stdout(
                                    tu.result(True) + " testsuite: " + type(self).__name__ + "." + a + "[" + arch + "]"
                                    + " passed tests: {} failed tests: {}".format(p, f))
                        else:
                            m = tu.result(False) + " testsuite: " + type(self).__name__ + "." + a + "[" + arch + "]"\
                                + " passed tests: {} failed tests: {}".format(p, f)
                            la.LoggingAccess().stdout(m)
                    except BaseException as ex:
                        m = tu.result(False) + ": " + type(self).__name__ + "." + a + "[" + arch + "]" + " (" + str(
                            ex) + ") from " + \
                            inspect.stack()[1][1]
                        la.LoggingAccess().stdout(m)
                        failed += 1
                        # print(m, file=sys.stderr)
                        # traceback.print_exc()
                    methodEnd = time.process_time()
                    ms = (methodEnd)*1000-(methodStart*1000)
            rpms = config.runtime_config.RuntimeConfig().getRpmList()
            la.LoggingAccess().log("<?xml version=\"1.0\"?>\n<testsuites>", vc.Verbosity.JTREG,
                                           type(self).__name__)
            failed_for_architecture = do.Tests().count_failed()
            passed_for_architecture = len(do.Tests().get_tests()) - do.Tests().count_failed()
            la.LoggingAccess().log(
                    tu.xmltestsuite(0, failed_for_architecture, passed_for_architecture, passed_for_architecture +
                                    failed_for_architecture, 0, type(self).__name__, mexe.DefaultMock().os
                                    + mexe.DefaultMock().version + "-vagrant", ms, dt.datetime.now().isoformat()),
                    vc.Verbosity.JTREG, type(self).__name__)
            for testcase in do.Tests().get_tests():
                    la.LoggingAccess().log(testcase.print_test_case(), vc.Verbosity.JTREG, type(self).__name__)
            la.LoggingAccess().log("    <system-out></system-out>\n    " +
                                       "<system-err></system-err>\n  </testsuite>\n</testsuites>",
                                       vc.Verbosity.JTREG, type(self).__name__)
            self.indent = "    "
            self.log("finished: " + a + "[" + self.current_arch + "] " + str(i + 1) + "/" + str(len(archs)) +
                         " in "+str(round(ms,3))+"ms")
            do.Tests().clear_tests()
        suiteEnd = time.process_time()
        ms = (suiteEnd) * 1000 - (suiteStart * 1000)
        la.LoggingAccess().log(
            "finished testing suite: " + type(self).__name__ +
            " - failed/total: " + str(failed) + "/" + str(failed + passed) + " in "+str(round(ms,3))+"ms")
        return passed, failed, methodOnlyCounter

    def execute_special_docs(self):
        """Call and document all public methods in csch"""
        documented = 0
        ignored = 0
        failed = 0
        self.indent = "  "
        self.log("started special docs for suite: " + type(self).__name__ + ":")
        archs = self._cleanArchs()
        agregator = Agregator()
        for i, arch in enumerate(archs):
            self.current_arch=arch
            config.runtime_config.RuntimeConfig().current_arch = arch
            self.indent = "    "
            self.log("Setting configuration-specific-checks")
            self.setCSCH()
            if self.csch is None:
                self.log("configuration-specific-checks are not set. Nothing to do")
            else:
                # on contrary with execute_tests, this walks methods on csch!!!
                methods = lsort(inspect.getmembers(self.csch, predicate=inspect.ismethod))
                for a, b in methods:
                    self.current_arch = arch
                    if not str(a).startswith("_"):
                        self.indent = "      "
                        self.log("using: " + str(type(self.csch).__name__))
                        self.csch.documenting = True
                        self.log(
                            "documenting: " + a + "[" + self.current_arch + "] " + str(i + 1) + "/" + str(len(archs)))
                        calllable = getattr(self.csch, a)
                        try:
                            self.indent = "        "
                            calllable(self.csch)
                            self.log("Ignored : " + type(self.csch).__name__ + "." + a + "[" + arch + "]")
                            ignored += 1
                        except cs.DocumentationProcessing as doc:
                            agregator.add(arch, a, str(doc))
                            self.log("Processed : " + type(self.csch).__name__ + "." + a + "[" + arch + "]")
                            documented += 1
                        except Exception as ex:
                            m = "Error: " + type(self.csch).__name__ + "." + a + "[" + arch + "]" + " (" + str(
                                ex) + ") from " + \
                                inspect.stack()[1][1]
                            failed += 1
                            self.log(m)
                            print(m, file=sys.stderr)
                            traceback.print_exc()
                        self.indent = "    "
                        self.log("finished: " + a + "[" + self.current_arch + "] " + str(i + 1) + "/" + str(len(archs)))
        agregator.out()
        la.LoggingAccess().log(
            "finished documenting suite: " + type(self).__name__ +
            " - documented/ignored/failed: " + str(documented) + "/" + str(ignored) + "/" + str(failed))
        return documented, ignored, failed

    def log(self, arg, verbosity=vc.Verbosity.ERROR):
        la.LoggingAccess().log(self.indent + arg, verbosity)


def compareListLaniently(list1, list2):
    if len(set(list1)) != len(set(list2)):
        return False
    for val in list1:
        if not val in list2:
            return False
    for val in list2:
        if not val in list1:
            return False
    return True
