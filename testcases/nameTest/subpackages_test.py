import ntpath
import sys

from utils.core.configuration_specific import JdkConfiguration
import config.global_config as gc
import config.runtime_config
import outputControl.logging_access
import utils.core.base_xtest
import utils.core.unknown_java_exception as ex
from utils.test_constants import *
import outputControl.logging_access as la
from utils import pkg_name_split as split
from utils.test_utils import passed_or_failed
import config.verbosity_config as vc


class MainPackagePresent(JdkConfiguration):

    def __init__(self):
        super().__init__()

    def _getSubPackages(self):
        return set([""])

    def _mainCheck(self, subpkgs):
        expected = self._getSubPackages()
        subpkgSetExpected= sorted(expected)
        ssGiven = sorted(set(subpkgs))
        SubpackagesTest.instance.log("Checking number of subpackages " + str(len(ssGiven)) +
                                     " of " + SubpackagesTest.instance.current_arch + " against "
                                     + str(len(subpkgSetExpected)), vc.Verbosity.TEST)
        SubpackagesTest.instance.log("Presented: " + str(ssGiven), vc.Verbosity.TEST)
        SubpackagesTest.instance.log("Expected:  " + str(subpkgSetExpected), vc.Verbosity.TEST)
        #if not ssGiven == subpkgSetExpected:
        if not passed_or_failed(self, ssGiven == subpkgSetExpected,
                               "Set of subpkgs not as expected. Differences will follow."):
            missingSubpackages = []
            for subpkg in subpkgSetExpected:
                SubpackagesTest.instance.log(
                    "Checking `" + subpkg + "` of " + SubpackagesTest.instance.current_arch, vc.Verbosity.TEST)
                if subpkg in ssGiven:
                    ssGiven.remove(subpkg)
                else:
                    missingSubpackages.append(subpkg)
            passed_or_failed(self, False, "Set of subpackages not as expected. \nextra subpkgs: " + str(ssGiven) + "\nmissing subpkgs: " + str(missingSubpackages))


class BaseSubpackages(MainPackagePresent):
    # providing just utility methods common for jdk packages
    def _subpkgsToString(self):
        return "`" + "`,`".join(
            self._getSubPackages()) + "`. Where `` is main package " + config.runtime_config.RuntimeConfig().getRpmList().getMajorPackage()

    def checkSubpackages(self, subpackages=None):
        rpms = config.runtime_config.RuntimeConfig().getRpmList()
        self._document(
            rpms.getVendor() + " should have exactly " + str(
                len(self._getSubPackages())) + " subpackages: " + self._subpkgsToString())
        self._mainCheck(subpackages)
        return self.passed, self.failed

    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.add("debuginfo")
        return subpackages


class JDKBase(BaseSubpackages):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update({DEVEL, "demo", "src"})
        return  subpackages


class ItwSubpackages(MainPackagePresent):
    def _getSubPackages(self):
        subpackages = super(ItwSubpackages, self)._getSubPackages()
        subpackages.update({JAVADOC, DEVEL})
        return subpackages

    def checkSubpackages(self, subpackages=None):
        self._document("IcedTea-Web has exactly following subpackages: `" + "`,`".join(
            self._getSubPackages()) + "`. Where `` is main package " + gc.ITW)
        self._mainCheck(subpackages)
        return self.passed, self.failed


class ItwEl7Subpackages(ItwSubpackages):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.add("debuginfo")
        return subpackages


class OpenJdk8(JDKBase):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.add(JAVADOC)
        subpackages.update({"accessibility", HEADLESS})
        subpackages.add("javadoc-zip")
        return subpackages

    def _get_debuginfo(self):
        return {"demo-debuginfo",
                "devel-debuginfo",
                "headless-debuginfo"}

    def _get_debug_debuginfo(self):
        subpkgs = set()
        for suffix in get_debug_suffixes():
            subpkgs.update({"demo" + suffix + "-debuginfo",
                "devel" + suffix + "-debuginfo",
                "headless" + suffix + "-debuginfo",
                suffix.replace("-", "", 1) + "-debuginfo"})
        return subpkgs

    def _get_debug_subpackages(self):
        subpkgs = set()
        for suffix in get_debug_suffixes():
            subpkgs.update({"accessibility" + suffix,
                "demo" + suffix,
                "devel" + suffix,
                "headless" + suffix,
                "src" + suffix,
                suffix.replace("-", "", 1)})
        return subpkgs

    def _get_javadoc_debug(self):
        subpkgs = set()
        for suffix in get_debug_suffixes():
            subpkgs.update({JAVADOC + suffix,JAVADOCZIP + suffix})
        return subpkgs


class OpenJdk8Debug(OpenJdk8):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update(super()._get_debug_subpackages())
        return subpackages


class OpenJdk8JFX(OpenJdk8Debug):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update({"openjfx", "openjfx-devel"})
        for suffix in get_debug_suffixes():
            subpackages.update({"openjfx" + suffix, "openjfx-devel" + suffix})
        return subpackages


class OpenJdk8DebugDebuginfo(OpenJdk8Debug):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update(self._get_debuginfo())
        subpackages.update(self._get_debug_debuginfo())
        subpackages.add("debugsource")
        return subpackages


class OpenJdk8Debuginfo(OpenJdk8):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update(self._get_debuginfo())
        subpackages.add("debugsource")
        return subpackages


class OpenJdk8JFXDebuginfo(OpenJdk8JFX):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update(self._get_debuginfo())
        subpackages.update(self._get_debug_debuginfo())
        subpackages.add("debugsource")
        return subpackages


    def _get_debug_debuginfo(self):
        subpackages = set()
        for suffix in get_debug_suffixes():
            subpackages.update({"devel" + suffix + "-debuginfo",
                "headless" + suffix + "-debuginfo"})
        return subpackages


class OpenJdk11(OpenJdk8):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.discard("accessibility")
        subpackages.add('static-libs')
        return subpackages


class OpenJdk11armv7hl(OpenJdk11):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update({"debugsource", DEVEL + "-debuginfo", HEADLESS + "-debuginfo", "jmods"})
        return subpackages


class OpenJdk11DebugFc(OpenJdk8Debug):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.discard("accessibility")
        for suffix in get_debug_suffixes():
            subpackages.discard("accessibility" + suffix)
            subpackages.update({"jmods" + suffix})
        subpackages.update({"jmods", "debugsource"})
        subpackages.update(self._get_debuginfo())
        subpackages.update(self._get_debug_debuginfo())
        subpackages.update({'static-libs'})
        for suffix in get_debug_suffixes():
            subpackages.add("static-libs" + suffix)
        return subpackages

    def _get_debug_debuginfo(self):
        subpackages = super()._get_debug_debuginfo()
        for suffix in get_debug_suffixes():
            subpackages.discard("demo" + suffix + "-debuginfo")
        return subpackages

    def _get_debuginfo(self):
        subpackages = super()._get_debuginfo()
        subpackages.discard("demo-debuginfo")
        return subpackages


class OpenJdk11DebugRhel(OpenJdk11DebugFc):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        return subpackages


class OpenJdkLatest(OpenJdk11DebugFc):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        for suffix in get_debug_suffixes():
            subpackages.update(self._get_debug_subpackages())
            subpackages.update(self._get_debug_debuginfo())
            subpackages.update(self._get_debuginfo())
            subpackages.update({"src" + suffix})
            subpackages.discard('accessibility' + suffix)

        subpackages.discard("demo")
        return subpackages


class OpenJdkLatestarmv7hl(OpenJdk11DebugFc):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        for suffix in get_debug_suffixes():
            subpackages.update({JAVADOCZIP + suffix, JAVADOC + suffix})
        subpackages.update(self._get_debug_subpackages())
        subpackages.update(self._get_debug_debuginfo())
        subpackages.update(self._get_debuginfo())

        i = 0
        iterations = len(subpackages)
        subpackagelist = list(subpackages)
        while i < iterations:
            if subpackagelist[i].count("debug") > 1 or subpackagelist[i].endswith("debug"):
                subpackagelist.remove(subpackagelist[i])
                iterations = len(subpackagelist)
                i -= 1
            i += 1
        subpackages = set(subpackagelist)
        return subpackages


class OpenJdkLatestel7(OpenJdkLatest):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.discard("debugsource")
        subpackages.discard("debug-debuginfo")
        subpackages.discard(DEVEL + "-debug-debuginfo")
        subpackages.discard(DEVEL + "-debuginfo")
        subpackages.discard(HEADLESS + "-debug-debuginfo")
        subpackages.discard(HEADLESS + "-debuginfo")
        return subpackages


class OracleAndIbmBase(JDKBase):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.update({"jdbc", HEADLESS})
        subpackages.discard("debuginfo")
        return subpackages


class Ibm8El7(OracleAndIbmBase):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.discard(HEADLESS)
        subpackages.discard("webstart")
        return subpackages


class OracleAndIbmAddPlugin(OracleAndIbmBase):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.add(PLUGIN)
        return subpackages


class Ibm8El7withPlugin(Ibm8El7):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.add(PLUGIN)
        return subpackages


class Ibm8withWS(OracleAndIbmAddPlugin):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.add("webstart")
        return subpackages


class Oracle7and8(OracleAndIbmAddPlugin):
    def _getSubPackages(self):
        subpackages = super()._getSubPackages()
        subpackages.discard("demo")
        subpackages.add(JAVAFX)
        return subpackages


class BaseTemurinPackages(BaseSubpackages):
    def _getSubPackages(self):
        subpackages = ["jre", "jdk"]
        return subpackages


class SubpackagesTest(utils.core.base_xtest.BaseTest):
    instance = None

    def test_checkAllSubpackages(self):
        rpms = self.getBuild()
        subpackages = set()
        for rpm in rpms:
            subpackages.add(split.get_subpackage_only(ntpath.basename(rpm)))
        return self.csch.checkSubpackages(subpackages)

    def setCSCH(self):
        SubpackagesTest.instance = self
        rpms = config.runtime_config.RuntimeConfig().getRpmList()
        if rpms.getJava() == gc.ITW:
            if rpms.getOsVersionMajor() == 7:
                self.csch = ItwEl7Subpackages()
                return
            self.csch = ItwSubpackages()
            return

        if rpms.getVendor() == gc.OPENJDK or rpms.getVendor() == gc.OPENJ9:
            if rpms.getMajorVersionSimplified() == "8":
                if rpms.isRhel():
                    if self.getCurrentArch() in gc.getPpc32Arch() + gc.getS390Arch() + gc.getS390xArch():
                        self.csch = OpenJdk8Debuginfo()
                        return
                    else:
                        self.csch = OpenJdk8DebugDebuginfo()
                        return
                elif rpms.isFedora():
                    if int(rpms.getOsVersion()) < 27:
                        if self.getCurrentArch() in gc.getArm32Achs():
                            self.csch = OpenJdk8()
                            return
                        elif self.getCurrentArch() in gc.getAarch64Arch() + gc.getPower64Achs():
                            self.csch = OpenJdk8Debug()
                            return
                        elif self.getCurrentArch() in gc.getIx86archs() + gc.getX86_64Arch():
                            self.csch = OpenJdk8JFX()
                            return
                        else:
                            raise ex.UnknownJavaVersionException("Check for this arch is not implemented for given OS.")
                    if int(rpms.getOsVersion()) > 26:
                        if self.getCurrentArch() in gc.getIx86archs() + gc.getX86_64Arch():
                            self.csch = OpenJdk8JFXDebuginfo()
                            return
                        elif self.getCurrentArch() in gc.getArm32Achs() + gc.getS390xArch():
                            self.csch = OpenJdk8Debuginfo()
                            return
                        elif self.getCurrentArch() in gc.getAarch64Arch() + gc.getPower64Achs():
                            self.csch = OpenJdk8DebugDebuginfo()
                            return
                        else:
                            raise ex.UnknownJavaVersionException("Check for this arch is not implemented for given OS.")

                else:
                    raise ex.UnknownJavaVersionException("Unrecognized OS.")

            elif rpms.getMajorVersionSimplified() == '11':
                if self.getCurrentArch() in gc.getPpc32Arch() + gc.getS390Arch():
                    self.csch = OpenJdk11()
                    return
                elif self.getCurrentArch() in gc.getArm32Achs():
                    self.csch = OpenJdk11armv7hl()
                    return
                elif rpms.getOs() == gc.RHEL:
                    self.csch = OpenJdk11DebugRhel()
                    return
                else:
                    self.csch = OpenJdk11DebugFc()
                    return
            elif int(rpms.getMajorVersionSimplified()) >= 13:
                if self.getCurrentArch() in gc.getArm32Achs():
                    self.csch = OpenJdkLatestarmv7hl()
                    return
                elif rpms.getOs() == gc.RHEL:
                    if rpms.getOsVersionMajor() == 7:
                        self.csch = OpenJdkLatestel7()
                        return
                self.csch = OpenJdkLatest()
                return
            else:
                raise ex.UnknownJavaVersionException("Unknown OpenJDK version.")

        if rpms.getVendor() == gc.SUN:
            self.csch = OracleAndIbmAddPlugin()
            return
        if rpms.getVendor() == gc.ORACLE:
            self.csch = Oracle7and8()
            return
        if rpms.getVendor() == gc.IBM:
            if rpms.getMajorVersionSimplified() == "7":
                if self.getCurrentArch() in gc.getPpc32Arch() + gc.getIx86archs() + gc.getX86_64Arch():
                    self.csch = OracleAndIbmAddPlugin()
                    return
                else:
                    self.csch = OracleAndIbmBase()
                    return
            elif rpms.getMajorVersionSimplified() == "8":
                if rpms.getOs() == "RHEL" and rpms.getOsVersionMajor() == 7:
                    if self.getCurrentArch() in gc.getPpc32Arch() + gc.getIx86archs() + gc.getX86_64Arch() + \
                         gc.getPower64BeAchs():
                        self.csch = Ibm8El7withPlugin()
                        return
                    self.csch = Ibm8El7()
                    return
                elif self.getCurrentArch() in gc.getPpc32Arch() + gc.getIx86archs() + gc.getX86_64Arch() +\
                                            gc.getPower64BeAchs() + gc.getPower64LeAchs():
                    self.csch = Ibm8withWS()
                    return
                else:
                    self.csch = OracleAndIbmBase()
                    return
            else:
                raise ex.UnknownJavaVersionException("Ibm java version unknown.")
        if rpms.getVendor() == gc.ADOPTIUM:
            self.csch = BaseTemurinPackages()
            return
        raise ex.UnknownJavaVersionException("Java version or OS was not recognized by this framework.")


def testAll():
    return SubpackagesTest().execute_tests()


def documentAll():
    outputControl.logging_access.LoggingAccess().stdout("Subpackage conventions:")
    return SubpackagesTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
