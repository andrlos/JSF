""""Test that given set of rpms has the right names."""

import sys

import utils.pkg_name_split as split

import config.general_parser
import config.global_config as gc
import config.runtime_config
import testcases.nameTest.connfigs.nametest_config
import utils.core.base_xtest
import outputControl.logging_access as la
from utils.test_utils import _reinit
from outputControl import dom_objects as do
import utils.test_utils as tu

def aInB(a, b):
    return a in b


def aNotNone(a, b):
    return a is not None

def justCopy(a):
    return a


class NameTest(utils.core.base_xtest.BaseTest):
    """ This class needs the _reinit(self) call, because there are multiple test_* calls in one script,
    resulting in bad testcase passes/fails counting. It would just add the test case passes/fails for each
    test_* method, so the output would look like: test_1 = 37, test_2 = 37*2, test3=37*3 tests in total"""
    def __init__(self):
        super().__init__()

    def aMatchesB(self, a, b):
            return self.csch.checkRegex(a)

    def checkFilesAgainstValues(self, values, function):
        return self.checkFilesAgainstComparator(values, function, aInB)

    def checkWholeName(self):
        return self.checkFilesAgainstComparator(None, justCopy, self.aMatchesB)

    def checkFilesAgainstNone(self, function):
        return self.checkFilesAgainstComparator(None, function, aNotNone)

    def checkFilesAgainstComparator(self, values, function, comparator):
        _reinit(self)
        rpms = config.runtime_config.RuntimeConfig().getRpmList().getAllNames()
        for file in rpms:
            self.log("checking: " + file)
            val = function(file)
            self.log("have: " + val)
            tu.passed_or_failed(self, comparator(val, values), file + " is BAD", file + " is ok")
        return self.passed, self.failed

    def test_prefix(self):
        passed, failed = self.checkFilesAgainstValues([gc.JAVA_STRING, gc.ITW, gc.TEMURIN], split.get_javaprefix)
        return passed, failed

    def test_version(self):
        passed, failed = self.checkFilesAgainstValues(gc.LIST_OF_POSSIBLE_VERSIONS, split.get_major_ver)
        return passed, failed

    def test_vendor(self):
        passed, failed = self.checkFilesAgainstValues(gc.LIST_OF_POSSIBLE_VENDORS, split.get_vendor)
        return passed, failed

    def test_majorPackage(self):
        passed, failed = self.checkFilesAgainstNone(split.get_major_package_name)
        return passed, failed

    def test_package(self):
        passed, failed = self.checkFilesAgainstNone(split.get_package_name)
        return passed, failed

    def test_minorVersion(self):
        passed, failed = self.checkFilesAgainstNone(split.get_minor_ver)
        return passed, failed

    def test_subpackage(self):
        passed, failed = self.checkFilesAgainstNone(split.get_subpackage_only)
        return passed, failed

    def test_release(self):
        passed, failed = self.checkFilesAgainstNone(split.get_release)
        return passed, failed

    def test_arches(self):
        passed, failed = self.checkFilesAgainstValues(gc.getAllArchs(), split.get_arch)
        return passed, failed

    def test_dist(self):
        passed, failed = self.checkFilesAgainstNone(split.get_dist)
        return passed, failed

    def test_wholeName(self):
        """This is testing whole name by regex. It may sound redundant, but:
        The rest of the test checks validity of individual hunks. Not the order.
        The regex catches at least java->version->dashes->dot->arch->.rpm
        """
        passed, failed = self.checkWholeName()
        return passed, failed

    def setCSCH(self):
        if config.runtime_config.RuntimeConfig().getRpmList().getJava() == gc.ITW:
            self.log("Set ItwRegexCheck")
            self.csch = testcases.nameTest.connfigs.nametest_config.ItwRegexCheck()
            return
        if config.runtime_config.RuntimeConfig().getRpmList().getJava() == gc.TEMURIN:
            self.log("Set Temurin Regex Check")
            self.csch = testcases.nameTest.connfigs.nametest_config.TemurinRegexCheck()
            return
        if int(config.runtime_config.RuntimeConfig().getRpmList().getMajorVersionSimplified()) == 9:
            self.log("Set Jdk9RegexCheck")
            self.csch = testcases.nameTest.connfigs.nametest_config.Jdk9RegexCheck()
            return
        if int(config.runtime_config.RuntimeConfig().getRpmList().getMajorVersionSimplified()) >= 10:
            self.log("Set Jdk10RegexCheck. Can contain rolling release packages.")
            self.csch = testcases.nameTest.connfigs.nametest_config.Jdk10RegexCheck()
            return
        self.log("Set OthersRegexCheck")
        self.csch = testcases.nameTest.connfigs.nametest_config.OthersRegexCheck()

    def getTestedArchs(self):
        return None



def testAll():
    return NameTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Package naming conventions:")
    return NameTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
