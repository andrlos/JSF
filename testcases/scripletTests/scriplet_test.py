import ntpath
import sys

import utils.core.base_xtest
import utils.rpmbuild_utils as rpmbu
import outputControl.logging_access as la
from utils.mock.mock_executor import DefaultMock
from utils.rpmbuild_utils import ScripletStarterFinisher
import utils.pkg_name_split as ns
import utils.test_utils as tu
import utils.core.configuration_specific as cs
import config.runtime_config as rc
import config.global_config as gc


class GenericScriptletCsch(cs.JdkConfiguration):
    expected_scriptlets={"devel":[rpmbu.POSTINSTALL, rpmbu.POSTUNINSTALL, rpmbu.POSTTRANS],
                         "default":[rpmbu.POSTINSTALL, rpmbu.POSTUNINSTALL, rpmbu.POSTTRANS],
                         "javadoc":[rpmbu.POSTUNINSTALL, rpmbu.POSTTRANS],
                         "headless":[rpmbu.PRETRANS, rpmbu.POSTINSTALL, rpmbu.POSTUNINSTALL, rpmbu.POSTTRANS],
                         "headless-debug":[rpmbu.POSTINSTALL, rpmbu.POSTUNINSTALL, rpmbu.POSTTRANS]}

    def _get_expected_scriptlets(self, pkg):
        subpkg = ns.get_subpackage_only(pkg)
        if "debuginfo" in subpkg:
            return []
        # headless treats differently normal and debug subpkgs, as normal have pretrans script as well
        if "headless" in subpkg:
            subpkg = subpkg.replace("slow", "").replace("fast", "")
            return self.expected_scriptlets[subpkg]
        else:
            subpkg = subpkg.replace("slowdebug","").replace("fastdebug","")
        if subpkg.endswith("-"):
            subpkg = subpkg[:-1]
        if subpkg == "":
            subpkg = "default"
        if "javadoc" in subpkg:
            subpkg = "javadoc"
        if subpkg in self.expected_scriptlets.keys():
            return self.expected_scriptlets[subpkg]
        else:
            return []


class TemurinScriptletCsch(GenericScriptletCsch):
    def _get_expected_scriptlets(self, pkg):
        return [rpmbu.POSTINSTALL, rpmbu.PREUNINSTALL]


class ScriptletTest(utils.core.base_xtest.BaseTest):
    def __init__(self):
        super().__init__()
        self.passed = 0
        self.failed = 0

    # this test has no asserts, therefore it is not working properly, must be fixed, now gives 0 passes, 0 fails
    def check_allScripletsPresentedAsExpected(self, pkgs):
        for pkg in pkgs:
            expected = self.csch._get_expected_scriptlets(pkg)
            for scriplet in rpmbu.ScripletStarterFinisher.allScriplets:
                self.log("searching for " + scriplet + " in " + ntpath.basename(pkg))
                executor, content = utils.rpmbuild_utils.getSrciplet(pkg, scriplet)
                if len(content) == 0:
                    tu.passed_or_failed(self, scriplet not in expected,
                                        "missing scriptlet {} in {}".format(scriplet, pkg))
                    self.log("is " + str(len(content)) + " lines long")
                    self.log("not found?")
                else:
                    tu.passed_or_failed(self, scriplet in expected,
                                        "extra scriptlet {} in {}".format(scriplet, pkg))
                    self.log("is " + str(len(content)) + " lines long")
        return self.passed, self.failed

    # this test is currently disabled
    def check_allScripletsPReturnsZero(self, pkgs):
        for pkg in pkgs:
            DefaultMock().importRpm(pkg)
            # now applying scriplets in order
            for phase in [ScripletStarterFinisher.installScriptlets, ScripletStarterFinisher.uninstallScriptlets]:
                for scriplet in phase:
                    self.log("searching for " + scriplet + " in " + ntpath.basename(pkg))
                    executor, content = utils.rpmbuild_utils.getSrciplet(pkg, scriplet)
                    if len(content) == 0:
                        self.log(scriplet + " not found in " + ntpath.basename(pkg))
                    else:
                        self.log("is " + str(len(content)) + " lines long")
                        self.log("executing " + scriplet + " in " + ntpath.basename(pkg))
                        arg = "1" if scriplet in ScripletStarterFinisher.installScriptlets else "0"
                        o, r = DefaultMock().executeScriptlet(pkg, scriplet, arg)
                        self.log(scriplet + " returned " + str(r) + " of " + ntpath.basename(pkg))
                        tu.passed_or_failed(self, r == 0,
                                            "scriptlet {} returning non zero value for {}".format(scriplet, pkg))
        return self.passed, self.failed

    def setCSCH(self):
        rpms = rc.RuntimeConfig().getRpmList()
        if rpms.getVendor() == gc.ADOPTIUM:
            self.csch = TemurinScriptletCsch()
        else:
            self.csch = GenericScriptletCsch()
        return

    def test_scriptlets(self):
        pkgs = self.getBuild()
        self.check_allScripletsPresentedAsExpected(pkgs)
        return self.check_allScripletsPReturnsZero(pkgs)


def testAll():
    return ScriptletTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Basic tests on scriplets")
    la.LoggingAccess().stdout(" - All existing scriplets retuns zero")
    return ScriptletTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
