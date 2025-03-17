import os
import sys
import outputControl.logging_access as la
import config.runtime_config as rc
import utils.core.base_xtest as bt
from utils.core.configuration_specific import JdkConfiguration
from utils.mock.mock_executor import DefaultMock
from utils.test_utils import rename_default_subpkg, passed_or_failed, log_failed_test, get_arch
from utils.test_utils import two_lists_diff as diff
import utils.pkg_name_split as pkgsplit
from utils.test_constants import subpackages_without_alternatives
from enum import Enum
from outputControl import dom_objects as do
import config.verbosity_config as vc

OPENJFXDIR = "/usr/lib/jvm/openjfx"


class SymlinkTypes(Enum):
    """This enum represents type of symlink objects. It serves as a safety check in case there is some unexpected
    output. In that case, the check should fail on TypeError.
    """
    RELATIVE = 'relative'
    DANGLING = 'dangling'
    ABSOLUTE = 'absolute'
    MESSY = 'messy'
    LENGTHY = 'lengthy'
    OTHER_FS = 'other_fs'


class Symlink(object):
    """This class represents a symlinks as an object, with attributes: type_of_symlink - symlink type from enum,
    points_at - target of the symlink and path_to_symlink - the location of the symlink.
    """
    def __init__(self, type_of, path, points):
        self.path_to_symlink = path
        self.points_at = points
        self.type_of_symlink = SymlinkTypes(type_of)

    def __str__(self):
        return "Link: {}, pointing at: {} is {}.".format(self.path_to_symlink, self.points_at,
                                                         self.type_of_symlink.value)


def make_symlink(symlink):
    """Parses the output of commandline into symlink object"""
    split = symlink.split(" ")
    link = Symlink(split[0].strip(":"), split[1], split[3])
    return link


class BaseMethods(JdkConfiguration):
    def __init__(self):
        super().__init__()
        self.list_of_failed_tests = []
        self.rpms = rc.RuntimeConfig().getRpmList()

    # symlinks -r / have struct: typeOfSymlink: path -> points_at, split[2] = '->'
    def _symlink_parser(self, symlink_list):
        symlinks = []
        for symlink in symlink_list:
            link = make_symlink(symlink)
            symlinks.append(link)
        return symlinks

    def check_dangling_symlinks(self, link, subpackage=None):
        """Even though the symlink is dangling, it can be valid for various reasons mentioned under. Most 'fake' fails
         are a result of missing dependencies (e.g. devel -> headless). We can not install these dependencies, as it
         would kill the framework idea.
         """
        self._document("There are several types of links, that can be broken by design:\n "
                       "    - For links pointing at " + OPENJFXDIR + "/*, targets are provided by another "
                                                                     "subpackage.\n "
                       "    - Policytool binary is in JRE package, but policytool slave is in SDK, so the link is "
                       "broken in case of single subpackage install. \n "
                       "    - Files in jvm-exports have links in SDK package and files in JRE package,"
                       " therefore the links must be broken in single subpackage install. \n "
                       "    - For links in proprietary JDK devel package in bin directory,"
                       " that point at /jre/bin directory, targets are"
                       " provided by the JRE subpackage, so the links must be broken."

                       )
        valid_link = False
        # check openjfx links, that are expected to be broken (binary in ojfx-devel, but link in headless)
        # TODO: add additional check
        if OPENJFXDIR in link.points_at:
            SymlinkTest.instance.log("Links pointing at " + OPENJFXDIR + " are targeting files provided by openjfx"
                                     "subpackage. This is not treated as fail.")

            valid_link = True
        # check policytool links - binary is usually in jre, whether link in sdk, it is broken by design, but no way
        # to fix it
        if "policytool" in link.path_to_symlink:
            SymlinkTest.instance.log("Links on policytool binary and slaves are broken by design - the binary is "
                                     "usually present in jre, slave in sdk, this is not ment to be fixed.")
            valid_link = True

        # exports policies are broken by design - jre/sdk binary/link distribution
        if "jvm-exports" in link.path_to_symlink and ".jar" in link.points_at:
            SymlinkTest.instance.log("Export links are broken because links are in devel, whether the binaries are in "
                                     "headless, is not buggy behavior.")
            valid_link = True

        # links on jre binaries are broken in devel subpackages
        if get_arch(SymlinkTest.instance) + "/bin/" in link.path_to_symlink and "/jre/bin" in link.points_at and \
            (subpackage == "devel" or subpackage == "devel-debug"):
            SymlinkTest.instance.log("Links in devel package in bin directory, that point at /jre/bin directory, "
                                     "targets are provided by the JRE subpackage, so the links must be broken.")
            valid_link = True

        # this is a dependency that has around 100 dependencies, installing this into clean chroot is sick
        if "/jre/lib/ext/java-atk-wrapper.jar" in link.path_to_symlink and \
                ("/usr/lib64/java-atk-wrapper/java-atk-wrapper.jar" in link.points_at or
                 "/usr/lib/java-atk-wrapper/java-atk-wrapper.jar" in link.points_at):
            SymlinkTest.instance.log("Java atk wrapper is provided by required package java-atk-wrapper. Installation"
                                     "of this dependency would hurt the test suite, therefore this hardcoded check.")
            valid_link = True

        passed_or_failed(self, valid_link,
                         " Subpackage {}: link {} pointing at {} is invalid.".format(subpackage,
                                                                                     link.path_to_symlink,
                                                                                     link.points_at),
                         "Link {} pointing at {} is valid.".format(link.path_to_symlink, link.points_at))

    def a_symlink_test(self, pkgs):
        """ This test aggregates all of the checks and excludes into one big check. """
        self._document("All symlinks must have valid target.")
        symlink_dict = {}

        pkgs = SymlinkTest.instance.getBuild()

        DefaultMock().provideCleanUsefullRoot()
        SymlinkTest.instance.log("Getting pre-existing symlinks", vc.Verbosity.TEST)
        default_symlink_list = DefaultMock().executeCommand(["symlinks -rvs /"])[0].split("\n")

        for pkg in pkgs:
            name = os.path.basename(pkg)
            _subpkg = rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            if _subpkg in subpackages_without_alternatives():
                continue
            if not DefaultMock().run_all_scriptlets_for_install(pkg):
                continue

            # iterating over all directories recursively (-r) and under all symlinks (-v)
            symlinks_list = DefaultMock().executeCommand(["symlinks -rvs /"])
            symlinks_list = symlinks_list[0].split("\n")
            symlinks = diff(symlinks_list, default_symlink_list)
            symlink_dict[_subpkg] = self._symlink_parser(symlinks)

        for subpackage in symlink_dict.keys():
            for link in symlink_dict[subpackage]:
                if link.type_of_symlink == SymlinkTypes.DANGLING:
                    SymlinkTest.instance.log("Found dangling link in {}: {}. Further check ongoing, determining whether"
                                             " this is expected behavior.".format(subpackage, link.__str__()),
                                             vc.Verbosity.TEST)
                    # dangling links must be checked for excludes
                    self.check_dangling_symlinks(link, subpackage)

                else:
                    # TODO: Must check if the link does not point on other link, if it does, check whether that one is
                    # TODO: not broken
                    passed_or_failed(self, True, "")
                    SymlinkTest.instance.log("Found valid link in {}: ".format(subpackage) + link.__str__(),
                                              vc.Verbosity.TEST)
        SymlinkTest.instance.log("Failed symlinks tests: " + "\n".join(self.list_of_failed_tests), vc.Verbosity.TEST)
        return self.passed, self.failed


class SymlinkTest(bt.BaseTest):
    """ Framework class that runs the testcase. """
    instance = None

    def test_links(self):
        pkgs = self.getBuild()
        return self.csch.a_symlink_test(pkgs)

    def setCSCH(self):
        SymlinkTest.instance = self
        rpms = rc.RuntimeConfig().getRpmList()
        self.log("Checking symlinks for: " + rpms.getMajorPackage(), vc.Verbosity.TEST)
        self.csch = BaseMethods()
        return


def testAll():
    return SymlinkTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Symlink conventions:")
    return SymlinkTest().execute_special_docs()


def main(argv):
    bt.defaultMain(argv, documentAll, testAll)
    return SymlinkTest().execute_special_docs()


if __name__ == "__main__":
    main(sys.argv[1:])


