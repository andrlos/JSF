import outputControl.logging_access as la
import sys
import utils.core.base_xtest as bt
from utils.core.configuration_specific import JdkConfiguration
import utils.rpmbuild_utils as rbu
import os
import config.global_config as gc
import config.runtime_config as rc
import utils.core.unknown_java_exception as ex
import utils.pkg_name_split as pkgsplit
import utils
from utils.mock.mock_executor import DefaultMock
from config.global_config import get_32b_arch_identifiers_in_scriptlets as get_id
from utils.test_utils import rename_default_subpkg, passed_or_failed, get_arch
from utils.test_constants import *
from outputControl import dom_objects as do
import config.verbosity_config as vc

# TODO check if the masters are directories + doc that those are directories

JAVADOCZIP = 'javadoczip'
JAVADOCDIR = 'javadocdir'
JAVADOC_ZIP = "javadoc-zip"


class BasePackages(JdkConfiguration):
    rpms = rc.RuntimeConfig().getRpmList()

    def __init__(self):
        super().__init__()

    def _get_arch(self):
        return PostinstallScriptTest.instance.getCurrentArch()

    def _generate_masters(self):
        return {}

    def _get_vendor(self):
        return self.rpms.getVendor()

    def _get_version(self):
        return self.rpms.getMajorVersion()

    def _get_masters_arch_copy(self, master):
        """Some of the masters have arch at the end, this method appends it automatically."""
        master = master + "." + str(get_id(self._get_arch()))
        return master

    def _add_plugin(self):
        return [LIBJAVAPLUGIN]


class CheckPostinstallScript(BasePackages):
    def document_all(self, arg):
        """ Just a simple documenting method, has no other functionality."""
        doc = ["Subpackages should contain following masters: "]
        masters = self._generate_masters()
        for k in masters.keys():
            whitespace = "    - "
            if self._get_vendor() == gc.ITW:
                name = self._get_vendor() + " " + k
            elif DEFAULT in k:
                name = self.rpms.getMajorPackage() + " " + k
            else:
                name = k
            doc.append(whitespace + name + " package: " + ", ".join(masters[k]))

        self._document("\n".join(doc))

    def _check_post_in_script(self, pkgs=None):
        """
        This method executes post install script and then looks for masters in /var/lib/alternatives. Checks whether
        it matches expected set of masters, that is generated for each JDK.
        """
        passed = []
        failed = []

        # skipped should contain only subpackages that does not have postscript
        skipped = []

        # we need to delete the already existing masters so we get only the installed ones
        _default_masters = DefaultMock().get_default_masters()

        # correct set of masters
        expected_masters = self._generate_masters()

        # masters installed in mock
        actual_masters = {}

        for pkg in pkgs:
            _subpackage = rename_default_subpkg(utils.pkg_name_split.get_subpackage_only(os.path.basename(pkg)))

            PostinstallScriptTest.instance.log("Searching for " + rbu.POSTINSTALL + " in " + os.path.basename(pkg),
                                               vc.Verbosity.TEST)
            PostinstallScriptTest.instance.log("Checking master for " + os.path.basename(pkg), vc.Verbosity.TEST)
            if "-debuginfo" in _subpackage:
                PostinstallScriptTest.instance.log("Skipping " + _subpackage + " subpackage, because debuginfo "
                                                                               "subpackages does not contain "
                                                                               "any postinstall.")
                continue
            if not DefaultMock().run_all_scriptlets_for_install(pkg):
                skipped.append(_subpackage)
                continue
            pkg_masters = DefaultMock().get_masters()

            for m in _default_masters:
                pkg_masters.remove(m)

            actual_masters[_subpackage] = pkg_masters

        PostinstallScriptTest.instance.log("Postinstall script does not exist for: " + str(skipped) + ".",
                                           vc.Verbosity.TEST)
        PostinstallScriptTest.instance.log("Postinstall expected in " + str(len(expected_masters)) +
                                           " : " + ", ".join(expected_masters), vc.Verbosity.TEST)
        PostinstallScriptTest.instance.log("Postinstall present in " + str(len(actual_masters)) + " : " +
                                           ", ".join(actual_masters), vc.Verbosity.TEST)
        for subpkg in expected_masters.keys():
            if not passed_or_failed(self, subpkg in actual_masters.keys(), "There is no such subpackage as " +
                                                                           subpkg + " that contains masters."):
                continue
            PostinstallScriptTest.instance.log("Expected masters for " + subpkg + " : " +
                                               ", ".join(sorted(expected_masters[subpkg])), vc.Verbosity.TEST)
            PostinstallScriptTest.instance.log("Presented masters for " + subpkg + " : " +
                                               ", ".join(sorted(actual_masters[subpkg])), vc.Verbosity.TEST)
            missing_masters = set(expected_masters[subpkg]).difference(set(actual_masters[subpkg]))
            extra_masters = set(actual_masters[subpkg]).difference(set(expected_masters[subpkg]))
            passed_or_failed(self, len(missing_masters) == 0 and len(extra_masters) == 0,
                             "Expected masters do not match actual ones for {}. Extra masters: {}. Missing masters: {}.".format(subpkg, extra_masters, missing_masters))

        return self.passed, self.failed


class OpenJdk6(CheckPostinstallScript):
    def _generate_masters(self):
        masters = super(OpenJdk6, self)._generate_masters()
        masters[DEFAULT] = ['java', 'jre_' + self._get_vendor(), 'jre_' + self._get_version()]
        masters[JAVADOC] = [JAVADOCDIR]
        masters[DEVEL] = ['javac', 'java_sdk_' + self._get_vendor(), 'java_sdk_' + self._get_version()]
        return masters


class OpenJdk7(OpenJdk6):
    def _generate_masters(self):
        masters = super(OpenJdk7, self)._generate_masters()
        masters[HEADLESS] = masters[DEFAULT] + ["jre_" + self._get_version() + "_" + self._get_vendor()]
        masters[DEFAULT] = []
        masters[DEVEL].append("java_sdk_" + self._get_version() + "_" + self._get_vendor())
        return masters


class OpenJdk8S390(OpenJdk7):
    def _generate_masters(self):
        masters = super(OpenJdk8S390, self)._generate_masters()
        masters[JAVADOC_ZIP] = [JAVADOCZIP]
        return masters


class OpenJdk8OtherArchs(OpenJdk8S390):
    def _generate_masters(self):
        masters = super(OpenJdk8OtherArchs, self)._generate_masters()
        #masters.pop(JAVADOC, None)
        #masters.pop(JAVADOC_ZIP, None)
        for subpkg in [DEVEL, HEADLESS, DEFAULT]:
            for suffix in get_debug_suffixes():
                masters[subpkg + suffix] = masters[subpkg]
        return masters


class OpenJdk8Intel(OpenJdk8OtherArchs):
    pass


class OpenJdk9Armvhl(OpenJdk7):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters[JAVADOC_ZIP] = [JAVADOCZIP]
        return masters


class OpenJdk9OtherArchs(OpenJdk9Armvhl):
    def _generate_masters(self):
        masters = super()._generate_masters()
        for subpkg in [DEVEL, HEADLESS, DEFAULT]:
            for suffix in get_debug_suffixes():
                masters[subpkg + suffix] = masters[subpkg]
        return masters


class OpenJdk11Armv7hl(OpenJdk8S390):
    def _generate_masters(self):
        masters = super()._generate_masters()
        return masters


class OpenJdk11OtherArches(OpenJdk11Armv7hl):
    def _generate_masters(self):
        masters = super()._generate_masters()
        for subpkg in [DEVEL, HEADLESS, DEFAULT]:
            for suffix in get_debug_suffixes():
                masters[subpkg + suffix] = masters[subpkg]
        return masters


class OpenJdk11OtherArchesRhel(OpenJdk11OtherArches):
    def _generate_masters(self):
        masters = super()._generate_masters()
        return masters


class OpenJdk12OtherArches(OpenJdk9OtherArchs):
    def _generate_masters(self):
        masters = super(OpenJdk12OtherArches, self)._generate_masters()
        for suffix in get_debug_suffixes():
            masters[JAVADOC + suffix] = [JAVADOCDIR]
            masters[JAVADOC_ZIP + suffix] = [JAVADOCZIP]
        return masters


class OpenJdk17(OpenJdk9OtherArchs):
    def _generate_masters(self):
        masters = super(OpenJdk17, self)._generate_masters()
        return masters


class OpenJdk17arm7vhl(OpenJdk9Armvhl):
    def _generate_masters(self):
        masters = super(OpenJdk17arm7vhl, self)._generate_masters()
        return masters


class OpenJdk21(OpenJdk17):
    def _generate_masters(self):
        masters = super(OpenJdk21, self)._generate_masters()
        masters[JAVADOC].append(JAVADOCDIR + "_" + self._get_version() + "_" + self._get_vendor())
        masters[JAVADOC].append(JAVADOCDIR + "_" + self._get_version())
        masters[JAVADOC].append(JAVADOCDIR + "_" + self._get_vendor())
        masters[JAVADOC_ZIP].append(JAVADOCZIP + "_" + self._get_vendor())
        masters[JAVADOC_ZIP].append(JAVADOCZIP + "_" + self._get_version())
        masters[JAVADOC_ZIP].append(JAVADOCZIP + "_" + self._get_version() + "_" + self._get_vendor())
        return masters


class OpenJdk21arm7vhl(OpenJdk17arm7vhl):
    def _generate_masters(self):
        masters = super(OpenJdk21arm7vhl, self)._generate_masters()
        masters[JAVADOC].append(JAVADOCDIR + "_" + self._get_version() + "_" + self._get_vendor())
        masters[JAVADOC].append(JAVADOCDIR + "_" + self._get_version())
        masters[JAVADOC].append(JAVADOCDIR + "_" + self._get_vendor())
        masters[JAVADOC_ZIP].append(JAVADOCZIP + "_" + self._get_vendor())
        masters[JAVADOC_ZIP].append(JAVADOCZIP + "_" + self._get_version())
        masters[JAVADOC_ZIP].append(JAVADOCZIP + "_" + self._get_version() + "_" + self._get_vendor())
        return masters


class IcedTeaWeb(CheckPostinstallScript):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters[DEFAULT] = [JAVAWS + ".noarch"]
        return masters


class ProprietaryJava6(OpenJdk6):
    def _generate_masters(self):
        masters = super(ProprietaryJava6, self)._generate_masters()
        masters[DEFAULT].append(self._add_local_policy())
        masters[PLUGIN] = self._add_plugin()
        masters.pop(JAVADOC)
        return masters

    def _add_plugin(self):
        return [LIBJAVAPLUGIN]

    def _add_local_policy(self):
        return "jce_" + self._get_version() + "_" + self._get_vendor() + "_local_policy"


# s390x, x86, ppc64
class ProprietaryJava6WithArch(ProprietaryJava6):
    def _add_local_policy(self):
        return self._get_masters_arch_copy(super()._add_local_policy())


class Oracle6(ProprietaryJava6):
        # oracle packages do not have plugin subpackage with postinstall script
    def _add_plugin(self):
        return []

    def _generate_masters(self):
        masters = super()._generate_masters()
        masters.pop(PLUGIN)
        return masters


class Oracle6WithArch(Oracle6):
    def _add_local_policy(self):
        return self._get_masters_arch_copy(super()._add_local_policy())


class ProprietaryJava7and8Base(ProprietaryJava6WithArch):
    def _generate_masters(self):
        masters = super(ProprietaryJava7and8Base, self)._generate_masters()
        masters[DEVEL].append("java_sdk_" + self._get_version() + "_" + self._get_vendor())
        masters[DEFAULT].append("jre_" + self._get_version() + "_" + self._get_vendor())
        return masters


class ProprietaryJavaRhel8s390x(OpenJdk7):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters.pop(JAVADOC)
        return masters


class ProprietaryJavaRhel8(ProprietaryJavaRhel8s390x):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters["webstart"] = ["javaws"]
        masters[PLUGIN] = [self._get_masters_arch_copy(LIBJAVAPLUGIN)]
        return masters


class Ibm7(ProprietaryJava7and8Base):
    def _get_version(self):
        return "1.7.0"


class Ibm7x86(Ibm7):
    def _add_plugin(self):
        return [self._get_masters_arch_copy(LIBJAVAPLUGIN)]


class Ibm7WithoutPlugin(Ibm7):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters.pop(PLUGIN)
        return masters


class Oracle7(ProprietaryJava7and8Base):
    def _generate_masters(self):
        masters = super(Oracle7, self)._generate_masters()
        masters[JAVAFX] = [JAVAFXPACKAGER]
        masters.pop(PLUGIN)
        return masters


class Oracle8(Oracle7):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters[PLUGIN] = self._add_plugin()
        return masters


class Ibm8(ProprietaryJava7and8Base):
    def _add_plugin(self):
        return [self._get_masters_arch_copy(LIBJAVAPLUGIN)]


class Ibm8WithoutPlugin(Ibm8):
    def _generate_masters(self):
        masters = super()._generate_masters()
        masters.pop(PLUGIN)
        return masters


class Oracle7a8x86(Oracle7):
    def _add_plugin(self):
        return [self._get_masters_arch_copy(LIBJAVAPLUGIN)]

    def _generate_masters(self):
        masters = super()._generate_masters()
        masters[PLUGIN] = self._add_plugin()
        return masters


class Temurin(CheckPostinstallScript):
    def _generate_masters(self):
        masters = dict()
        masters[JDK] = [JAVA, JAVAC]
        masters[JRE] = [JAVA]
        return masters


class PostinstallScriptTest(bt.BaseTest):
    instance = None

    def test_contains_postscript(self):
        pkgs = self.getBuild()
        return self.csch._check_post_in_script(pkgs)

    def setCSCH(self):
        PostinstallScriptTest.instance = self
        rpms = rc.RuntimeConfig().getRpmList()
        self.log("Checking post_script and master for " + rpms.getVendor(), vc.Verbosity.TEST)

        if rpms.getVendor() == gc.OPENJDK or rpms.getVendor() == gc.OPENJ9:
            if rpms.getMajorVersionSimplified() == "6":
                self.csch = OpenJdk6()
                return
            elif rpms.getMajorVersionSimplified() == "7":
                self.csch = OpenJdk7()
                return
            elif rpms.getMajorVersionSimplified() == "8":
                if self.getCurrentArch() in gc.getIx86archs() + gc.getX86_64Arch() + \
                        gc.getPower64Achs() + gc.getAarch64Arch():
                    self.csch = OpenJdk8Intel()
                    return
                elif self.getCurrentArch() in gc.getS390xArch() + gc.getS390Arch() + gc.getArm32Achs() or self.getCurrentArch() == "armv7hl":
                    self.csch = OpenJdk8S390()
                    return
                else:
                    self.csch = OpenJdk8OtherArchs()
                    return
            elif rpms.getMajorVersionSimplified() in ["9", "10"]:
                if rpms.getOs() == gc.RHEL and rpms.getOsVersionMajor() == 7:
                    if self.getCurrentArch() in gc.getArm32Achs() + gc.getPpc32Arch() + gc.getS390Arch():
                        self.csch = OpenJdk9Armvhl()
                        return
                    else:
                        self.csch = OpenJdk9OtherArchs()
                        return
                else:
                    if self.getCurrentArch() in gc.getArm32Achs():
                        self.csch = OpenJdk9Armvhl()
                        return
                    else:
                        self.csch = OpenJdk9OtherArchs()
                        return
            elif rpms.getMajorVersionSimplified() == "11":
                if self.getCurrentArch() in gc.getArm32Achs():
                    self.csch = OpenJdk11Armv7hl()
                    return
                if rpms.getOs() == gc.RHEL:
                    self.csch = OpenJdk11OtherArchesRhel()
                    return
                self.csch = OpenJdk11OtherArches()
                return
            elif int(rpms.getMajorVersionSimplified()) == 12:
                self.csch = OpenJdk12OtherArches()
                return
            elif int(rpms.getMajorVersionSimplified()) == 17:
                if self.getCurrentArch() in gc.getArm32Achs():
                    self.csch = OpenJdk17arm7vhl()
                    return
                self.csch = OpenJdk17()
                return
            elif int(rpms.getMajorVersionSimplified()) >= 21:
                if self.getCurrentArch() in gc.getArm32Achs():
                    self.csch = OpenJdk21arm7vhl()
                    return
                self.csch = OpenJdk21()
                return
            else:
                raise ex.UnknownJavaVersionException("Unknown JDK version.")

        elif rpms.getVendor() == gc.ITW:
            self.csch = IcedTeaWeb()
            return

        elif rpms.getVendor() == gc.IBM:
            if rpms.getOsVersionMajor() < 8:
                if rpms.getMajorVersionSimplified() == "7":
                    if self.getCurrentArch() in gc.getS390xArch() + gc.getS390Arch() + \
                            gc.getPower64LeAchs() + gc.getPower64BeAchs():
                        self.csch = Ibm7WithoutPlugin()
                        return
                    elif self.getCurrentArch() in gc.getX86_64Arch():
                        self.csch = Ibm7x86()
                        return
                    else:
                        self.csch = Ibm7()
                        return
                elif rpms.getMajorVersionSimplified() == "8":
                    if self.getCurrentArch() in gc.getS390xArch() + gc.getS390Arch() + gc.getPower64LeAchs():
                        self.csch = Ibm8WithoutPlugin()
                        return
                    else:
                        self.csch = Ibm8()
                        return
                else:
                    raise ex.UnknownJavaVersionException("Unknown IBM java version.")
            else:
                if self.getCurrentArch() in gc.getS390xArch() + gc.getS390Arch() + gc.getPower64LeAchs():
                    self.csch = ProprietaryJavaRhel8s390x()
                    return
                self.csch = ProprietaryJavaRhel8()
                return

        elif rpms.getVendor() == gc.ORACLE or rpms.getVendor() == gc.SUN:
            if rpms.getMajorVersionSimplified() == "6":
                if self.getCurrentArch() in gc.getS390xArch() + gc.getX86_64Arch() + gc.getPower64BeAchs():
                    self.csch = Oracle6WithArch()
                    return
                else:
                    self.csch = Oracle6()
                    return
            elif rpms.getMajorVersionSimplified() == "7":
                self.csch = Oracle7()
                return

            elif rpms.getMajorVersionSimplified() == "8":
                if self.getCurrentArch() in gc.getX86_64Arch():
                    self.csch = Oracle7a8x86()
                    return
                else:
                    self.csch = Oracle8()
                    return
            else:
                raise ex.UnknownJavaVersionException("Unknown Oracle java version.")
        elif rpms.getVendor() == gc.ADOPTIUM:
            self.csch = Temurin()
            return
        else:
            raise ex.UnknownJavaVersionException("Unknown platform, java was not identified.")


def testAll():
    return PostinstallScriptTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Postinstall scriptlet and master conventions:")
    return PostinstallScriptTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)
    return PostinstallScriptTest().execute_special_docs()


if __name__ == "__main__":
    main(sys.argv[1:])

