import sys
import os
from utils.core.configuration_specific import JdkConfiguration
from utils.mock.mock_executor import DefaultMock
import config.runtime_config
import config.global_config as gc
import utils.core.unknown_java_exception as ex
import outputControl.logging_access as la
import utils.core.base_xtest
import utils.rpm_list
import utils.pkg_name_split
import utils.mock.mock_execution_exception
from utils.test_constants import *
from utils.test_utils import log_failed_test, rename_default_subpkg, passed_or_failed
from outputControl import dom_objects as do
import config.verbosity_config as vc

PREFIX_111 = "111"
PREFIX_160 = "160"
PREFIX_170 = "170"
PREFIX_180 = "180"
PREFIX_190 = "190"
PREFIX_1100 = "1100"
LEN_4 = 4
LEN_5 = 5
LEN_6 = 6
LEN_7 = 7
LEN_8 = 8


class PriorityTest(JdkConfiguration):

    _success_list = []
    _debug_check_fail_list = []

    rpms = config.runtime_config.RuntimeConfig().getRpmList()

    def __init__(self, length, prefix):
        super(PriorityTest, self).__init__()
        self.length = length
        self.prefix = prefix
        self.list_of_failed_tests = []

    def _get_priority(self, master):
        """ This method calls chroot in mock and gets priority from pre-configured methods. """
        priority = DefaultMock().get_priority(master)
        if priority is None:
            PriorityCheck.instance.log("Priority not found in output for master " + master + ", output is invalid.",
                                       vc.Verbosity.TEST)
            return None
        return priority

    def check_length(self, priority):
        """ This method checks whether the length of priority is as expected. """
        self._document("Priority for {} should be ".format(self.rpms.getMajorPackage()) + str(self.length) + " digit.")
        PriorityCheck.instance.log("Checking priority length.", vc.Verbosity.TEST)
        return passed_or_failed(self, len(priority) == self.length, "Priority should be {}-digit, but is {}.".format(self.length, len(priority)))

    def check_prefix(self, priority):
        """ This method checks if the prefix is as expected. In general, the prefix is based on major version. """
        self._document("Prefix is based on major version, in this case it should be " + self.prefix + ".")
        PriorityCheck.instance.log("Checking priority prefix.", vc.Verbosity.TEST)
        return passed_or_failed(self, priority.startswith(self.prefix, 0, len(self.prefix)),
                                "Priority prefix not as expected, should be {}.".format(self.prefix))

    def check_debug_packages(self, pkg_priorities):
        """ Debug packages must have lower priority than normal packages. The standard difference is +-1."""
        self._document("Debug package should have lower priority than normal package.")
        pkgs = pkg_priorities.keys()

        for pkg in pkgs:
            wasdebug = False
            for suffix in get_debug_suffixes():
                if suffix in pkg:
                    name = pkg.replace(suffix, "")
                    break
            if not wasdebug:
                continue

            for p in pkgs:
                if name == p:
                    master_and_priority_debug = pkg_priorities[pkg]
                    master_and_priority = pkg_priorities[p]
                else:
                    continue
                master = master_and_priority.keys()

                for m in master:
                    passed_or_failed(self, int(master_and_priority[m]) > int(master_and_priority_debug[m]),
                                     "Debug subpackage priority check failed for " + name +
                                     ", master " + m + ". Debug package should have lower priority. " +
                                     "Main package priority: {} Debug package"
                                     " priority: {}".format(master_and_priority[m],
                                                            master_and_priority_debug[m]))


class MajorCheck(PriorityTest):
    def _prepare_for_check(self, pkg):
        return DefaultMock().run_all_scriptlets_for_install(pkg)

    def _check_priorities(self, pkgs):

        _default_masters = DefaultMock().get_default_masters()

        # stores a dict of {pkg_name : {master : priority }}
        _pkgPriorities = {}

        for pkg in pkgs:
            pkg_name = rename_default_subpkg(utils.pkg_name_split.get_subpackage_only(os.path.basename(pkg)))

            if pkg_name in subpackages_without_alternatives():
                PriorityCheck.instance.log(pkg + " is not expected to contain postscript, skipping check.")
                continue

            # must be here anyway, since it creates the snapshot
            if not self._prepare_for_check(pkg):
                # logs itself in mock
                continue

            _pkgPriorities[pkg_name] = {}

            masters = DefaultMock().get_masters()
            for m in masters:
                #ignoring libjavaplugin as Jvanek stated is unnecessary for us to check on.
                if m in _default_masters or LIBJAVAPLUGIN in m:
                    continue
                try:
                    priority = self._get_priority(m)
                except utils.mock.mock_execution_exception.MockExecutionException as e:
                    passed_or_failed(self, False, str(e))
                    if "failed " not in str(e):
                        raise e
                if priority is None:
                    PriorityCheck.instance.log("Failed to get priority, skipping check for " + m + " in " + pkg_name)
                    continue

                if (self.check_length(priority) and
                        self.check_prefix(priority)):
                    self._success_list.append(os.path.basename(pkg))
                    PriorityCheck.instance.log("Priority " + priority + " valid for " + pkg_name +
                                               " package, master " + m, vc.Verbosity.TEST)

                    _pkgPriorities[pkg_name].update({m : priority})

                else:
                    passed_or_failed(self, False, "Priority " + priority + " invalid for " + os.path.basename(pkg) +
                                     " package, master " + m)


        PriorityCheck.instance.log("Checking debug packages priorities.", vc.Verbosity.TEST)
        self.check_debug_packages(_pkgPriorities)
        PriorityCheck.instance.log("Successful for: " + str(self._success_list), vc.Verbosity.TEST)
        PriorityCheck.instance.log("Failed for: " + str(self.list_of_failed_tests), vc.Verbosity.ERROR)
        PriorityCheck.instance.log("Debug package priority check failed for: " + str(self._debug_check_fail_list),
                                   vc.Verbosity.ERROR)
        return self.passed, self.failed


class OpenJdk8(MajorCheck):
    def __init__(self):
        super().__init__(LEN_7, PREFIX_180)


class OpenJdk11(MajorCheck):
    def __init__(self):
        super().__init__(LEN_8, PREFIX_1100)


class NonSystemJDK(MajorCheck):
    def __init__(self):
        super().__init__(1, 1)

    def check_prefix(self, priority):
        self._document("Priority for jdk 9 and 10 is always 1 for normal packages and 0 for debug packages.")
        return True


class ProprietaryJava6(MajorCheck):
    def __init__(self):
        super().__init__(LEN_6, PREFIX_160)


class ProprietaryJava7(MajorCheck):
    def __init__(self):
        super().__init__(LEN_6, PREFIX_170)


class ProprietaryJava8(MajorCheck):
    def __init__(self):
        super().__init__(LEN_6, PREFIX_180)


class IcedTeaWeb(MajorCheck):
    def __init__(self):
        super().__init__(LEN_5, PREFIX_180)


class Ibm8Rhel8Java(ProprietaryJava8):
    def _prepare_for_check(self, pkg):
        output = True
        if "plugin" in pkg:
            output = DefaultMock().run_all_scriptlets_for_install(pkg.replace("plugin", "webstart"))
        return DefaultMock().run_all_scriptlets_for_install(pkg) and output


class Temurin(MajorCheck):
    def __init__(self):
        super().__init__(LEN_4, PREFIX_111)


class PriorityCheck(utils.core.base_xtest.BaseTest):
    instance = None

    def test_priority(self):
        pkgs = self.getBuild()
        return self.csch._check_priorities(pkgs)

    def setCSCH(self):
        PriorityCheck.instance = self
        rpms = config.runtime_config.RuntimeConfig().getRpmList()
        self.log("Checking priority for " + rpms.getVendor(), vc.Verbosity.TEST)

        if rpms.getVendor() == gc.OPENJDK or rpms.getVendor() == gc.OPENJ9:
            if rpms.is_system_jdk():
                if rpms.getMajorVersionSimplified() == "8":
                    self.csch = OpenJdk8()
                else:
                    self.csch = OpenJdk11()
            else:
                self.csch = NonSystemJDK()
        elif rpms.getVendor() == gc.SUN:
            if rpms.getMajorVersionSimplified() == "6":
                self.csch = ProprietaryJava6()
                return
        elif rpms.getVendor() == gc.IBM or rpms.getVendor() == gc.ORACLE:
            if rpms.getMajorVersionSimplified() == "7":
                self.csch = ProprietaryJava7()
                return
            elif rpms.getMajorVersionSimplified() == "8":
                self.csch = ProprietaryJava8()
                if rpms.getVendor() == gc.IBM and rpms.getOs() == gc.RHEL and rpms.getOsVersionMajor() == 8:
                    self.csch = Ibm8Rhel8Java()
                return
            else:
                raise ex.UnknownJavaVersionException("Unknown " + rpms.getVendor() + " version.")
        elif rpms.getVendor() == gc.ITW:
            self.csch = IcedTeaWeb()
            return
        elif rpms.getVendor() == gc.ADOPTIUM:
            self.csch = Temurin()
            return
        else:
            raise ex.UnknownJavaVersionException("Unknown platform, java was not identified.")


def testAll():
    return PriorityCheck().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Priority value conventions.")
    return PriorityCheck().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
