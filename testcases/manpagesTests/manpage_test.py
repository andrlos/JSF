import copy

import outputControl.logging_access as la
import sys
import utils.core.base_xtest as bt
import utils
import utils.core.configuration_specific as cs
import os
import utils.pkg_name_split as pkgsplit
import utils.test_utils as tu
import utils.core.unknown_java_exception as ex
import utils.mock.mock_executor as mexe
import config.runtime_config as rc
import config.global_config as gc
import utils.test_constants as tc
import config.verbosity_config as vc
import utils.pkg_name_split as ns


MANPAGE_SUFFIX = ".1.gz"
TEMURIN_MANPAGE_SUFFIX = ".1"
SUBPACKAGE = "subpackage"
MANPAGE = "Man page"
SDK_BINARIES = "SDK binaries"
MANPAGE_FOR_BINARY = MANPAGE + " file for binary"
FILE = 1
LINK = 0

# TODO: if there are any manpages extra, this suite should recognize it and fail


class ManpageTestMethods(cs.JdkConfiguration):

    """
    This test expects that binaries are equal to its slaves (checked in binaries_test). Only binaries are used as a
    source of expected manpages.

    This checks if all binaries have its manpages and if all the manpages have links.

    IBM java does not have any manpages, so the test is skipped.
    """
    def __init__(self):
        super().__init__()
        self.list_of_failed_tests = []
        self.missing_manpages = dict()
        self.checked_subpackages = []

    skipped = []
    rpms = rc.RuntimeConfig().getRpmList()

    def _remove_excludes(self, binaries):
        excludes = self._get_excludes()
        if len(excludes) == 0:
            return binaries
        for e in excludes:
            if e in binaries:
                binaries.remove(e)
        return binaries

    def binaries_without_manpages(self, binaries=None):
        manpages_list = self.missing_manpages
        subpackages_list = self.checked_subpackages
        if manpages_list.__len__() == 0 or subpackages_list.__len__() == 0:
            return binaries
        self._document("There are multiple binaries, that are missing manpages in " +
                       " and ".join(manpages_list.keys()) + " subpackage:")
        for subpackage in manpages_list.keys():
            self._document(subpackage + ": " + ", ".join(manpages_list[subpackage]))
        for subpackage in subpackages_list:
            for item in manpages_list[subpackage]:
                try:
                    binaries[subpackage].remove(item)
                except KeyError:
                    tu.passed_or_failed(self, False, subpackage + " is not present.")
                except ValueError:
                    tu.passed_or_failed(self, False, item + " is not present in binaries! This is unexpected behaviour.")

        return binaries

    def _get_extra_bins(self, plugin_bin_content):
        return []

    def iced_tea_web_check(self, manpages_with_postcript=None, manpages_without_postscript=None):
        return

    def _get_manpage_files_names(self, list_of_bins, usr_bin_content):
        return list_of_bins

    def _get_manpage_link_names(self, list_of_links):
        return list_of_links

    def _get_checked_masters(self):
        return []

    def _get_manpage_suffixes(self, subpackage):
        return [MANPAGE_SUFFIX, "-" + self.rpms.getMajorPackage() + MANPAGE_SUFFIX]

    # this is a hack accomodating for temurins having manpages in jvm dir, this should be gone once it gets fixed by adoptium
    def _get_manpages_without_postscript(self, default_mans, subpkg):
        return self._clean_default_mpges(default_mans,
                                  mexe.DefaultMock().execute_ls(tc.MAN_DIR)[0]
                                  .split("\n"))

    def _get_subpackages(self):
        return []

    def _clean_up_binaries(self, binaries, master, usr_bin):
        return binaries

    def _get_arch(self):
        return gc.get_32b_arch_identifiers_in_scriptlets(ManpageTests.instance.getCurrentArch())

    def _clean_default_mpges(self, default_mans, all_mpgs):
        extracted_mpges = list(set(all_mpgs) - set(default_mans))
        return extracted_mpges

    def _clean_debug_subpackages(self, bins):
        return

    # wont be doc-ed, is already handled in binary test
    def _remove_java_rmi_cgi(self, binaries):
        if tc.JAVA_RMI_CGI in binaries:
            binaries.remove(tc.JAVA_RMI_CGI)
        return binaries

    def _get_target(self, master):
        return mexe.DefaultMock().get_target(master).strip(master)

    def _itw_plugin_bin_location(self):
        return "/usr/lib"

    def _get_excludes(self):
        return []

    def _clean_sdk_from_jre(self, bins, packages):
        ManpageTests.instance.log("Cleaning {} from JRE binaries "
                                  "(JRE bins do not have man pages in {}.)".format(SDK_BINARIES, tc.DEVEL),
                                  vc.Verbosity.TEST)

        devel_bins = []
        ManpageTests.instance.log("Original " + SDK_BINARIES + ": " + ", ".join(bins[tc.DEVEL]), vc.Verbosity.TEST)

        for b in bins[packages[1]]:
            if b not in bins[packages[0]]:
                devel_bins.append(b)
        self._clean_debug_subpackages(bins)
        ManpageTests.instance.log(SDK_BINARIES + " without JRE binaries: " + ", ".join(devel_bins), vc.Verbosity.TEST)
        bins[packages[1]] = devel_bins
        return bins

    def manpage_file_check(self, bins, subpackage=None, plugin_bin_content=None, manpages_without_postscript=None):
        """
        Each man page is a file, located in /usr/shared/man, it has a specified name bin-nvra.1.gz. It must be present
        for every binary in the given subpackages. JDK 10 has some of the pages missing, this is
        solved as exclude. Any exclude must be always documented in _document.
        """
        self._document("When rpm is installed, man page file exists for each binary "
                       "with {} suffix.".format(tu.replace_archs_with_general_arch(self._get_manpage_suffixes(tc.DEFAULT),
                                                self._get_arch())[FILE]))
        binaries = self._get_manpage_files_names(bins[subpackage], plugin_bin_content)
        manpage_contents = manpages_without_postscript[subpackage]
        # now check that every binary has a man file
        manpage_files = []
        for b in binaries:
            manpage = b + self._get_manpage_suffixes(subpackage)[FILE]
            if tu.passed_or_failed(self, manpage in manpage_contents, manpage + " man page file not in " + subpackage):
                manpage_files.append(manpage)
        return manpage_files

    def manpage_links_check(self, bins, subpackage=None, manpages_with_postscript=None, manpage_files=None):
        """
        Each man page has a link, that is located in /usr/shared/man/ and has a specific name bin.1.gz. This link
        points to alternatives. It must be present for every binary in given subpackages (except exludes).
        """
        self._document("Each man page slave has {} suffix.".format(self._get_manpage_suffixes(tc.DEFAULT)[LINK]))
        links = self._get_manpage_link_names(bins[subpackage])
        # now remove all files from man pages
        try:
            manpage_links = list(set(manpages_with_postscript[subpackage]) - set(manpage_files))
        except KeyError:
            tu.passed_or_failed(self, False, "No manpages or links found in " + tc.MAN_DIR + " for " + subpackage)
            return

        for l in links:
            link = l + self._get_manpage_suffixes(subpackage)[LINK]
            tu.passed_or_failed(self, link in manpage_links, link + " man page link not in " + subpackage)

    def man_page_test(self, pkgs):
        self._document("Every binary must have a man page. If binary has a slave, then man page has also its slave."
                       " \n - Man pages are in {} directory.".format(tc.MAN_DIR))
        bins = {}
        manpages_without_postscript = {}
        manpages_with_postscript = {}

        mexe.DefaultMock().provideCleanUsefullRoot()
        default_mans = mexe.DefaultMock().execute_ls(tc.MAN_DIR)[0].split("\n")
        usr_bin_content = mexe.DefaultMock().execute_ls("/usr/bin")[0].split("\n")
        plugin_bin_content = mexe.DefaultMock().execute_ls(self._itw_plugin_bin_location())[0].split("\n")

        for pkg in pkgs:
            name = os.path.basename(pkg)
            _subpkg = tu.rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            # expects binaries are only in devel/default/headless subpackage, is consistent with binaries test
            if _subpkg not in self._get_subpackages():
                continue

            # first check links
            if not mexe.DefaultMock().run_all_scriptlets_for_install(pkg):
                self.skipped.append(_subpkg)
                continue
            masters = mexe.DefaultMock().get_masters()

            checked_masters = self._get_checked_masters()

            for m in masters:
                if m not in checked_masters:
                    continue
                tg = self._get_target(m)
                binaries = mexe.DefaultMock().execute_ls(tg)[0].split("\n")
                binaries = self._clean_up_binaries(binaries, m, usr_bin_content)
                binaries = self._remove_java_rmi_cgi(binaries)
                binaries = self._remove_excludes(binaries)
                try:
                    plugin_binaries = self._get_extra_bins(plugin_bin_content)
                except NotADirectoryError:
                    tu.passed_or_failed(self, False, "/usr/bin directory not found, this is unexpected "
                                                  "behaviour and the test will not be executed.")
                    return

                ManpageTests.instance.log("Binaries found for {}: ".format(tg) + ", ".join(binaries + plugin_binaries))
                bins[_subpkg] = copy.deepcopy(binaries + plugin_binaries)

            # check links
            manpages = self._clean_default_mpges(default_mans, mexe.DefaultMock().execute_ls(tc.MAN_DIR)[0].split("\n"))

            if len(manpages) != 0:
                manpages_with_postscript[_subpkg] = manpages
                ManpageTests.instance.log("Manpages found: " + ", ".join(manpages))
            else:
                ManpageTests.instance.log("Warning: {} subpackage does not contain any binaries".format(_subpkg))

            # then check files
            mexe.DefaultMock().importRpm(pkg)
            manpages_without_postscript[_subpkg] = self._get_manpages_without_postscript(default_mans, _subpkg)
        try:
            bins = self._clean_sdk_from_jre(bins, self._get_subpackages())
            bins = self.binaries_without_manpages(bins)
        except KeyError as e:
            tu.passed_or_failed(self, False, "This type of failure usually means missing package in tested rpm set."
                                  " Text of the error: " + str(e))

        # then compare man files with binaries and man links with links
        for subpackage in bins.keys():
            manpage_files = self.manpage_file_check(bins, subpackage, plugin_bin_content, manpages_without_postscript)
            self.manpage_links_check(bins, subpackage, manpages_with_postscript, manpage_files)

        self.iced_tea_web_check(manpages_with_postscript, manpages_without_postscript)

        ManpageTests.instance.log("Failed tests summary: " + ", ".join(self.list_of_failed_tests), vc.Verbosity.ERROR)
        return self.passed, self.failed

        # only doc-used method, does not execute any tests whatsoever
    def manpages_file_debug_subpackages_doc(self, args):
        if tc.get_debug_suffixes():
            self._document(" For debug subpackages, man page file is suffixed "
                           "with {}.".format(tu.replace_archs_with_general_arch((self._get_manpage_suffixes(tc.get_debug_suffixes())),
                                                                             self._get_arch())[FILE]))
        return


class OpenJdk8(ManpageTestMethods):
    def __init__(self):
        super().__init__()
        self.checked_subpackages = [tc.DEVEL]
        for suffix in tc.get_debug_suffixes():
            self.checked_subpackages.append(tc.DEVEL + suffix)

    def _clean_debug_subpackages(self, bins):
        devel_bins = []
        if len(tc.get_debug_suffixes()) > 0:
            ManpageTests.instance.log("Original debug " + SDK_BINARIES + ": " + ", ".join(bins[self._get_subpackages()[3]]),
                                      vc.Verbosity.TEST)
            for b in bins[self._get_subpackages()[3]]:
                if b not in bins[self._get_subpackages()[2]]:
                    devel_bins.append(b)
            for suffix in tc.get_debug_suffixes():
                bins[tc.DEVEL + suffix] = copy.copy(devel_bins)
        return

    def _get_subpackages(self):
        subpkgs = [tc.HEADLESS, tc.DEVEL]
        for suffix in tc.get_debug_suffixes():
            for subpkg in subpkgs.copy():
                subpkgs.append(subpkg + suffix)
        return subpkgs

    def _get_manpage_suffixes(self, subpackage):
        for suffix in list(tc.get_debug_suffixes()) + [""]:
            if suffix in subpackage:
                return [MANPAGE_SUFFIX, "-" + self.rpms.getNvr() + "." + self._get_arch() + suffix + MANPAGE_SUFFIX]
        else:
            return [MANPAGE_SUFFIX, "-" + self.rpms.getNvr() + "." + self._get_arch() + MANPAGE_SUFFIX]

    def _clean_up_binaries(self, binaries, master, usr_bin):
        if master == tc.JAVA:
            binaries.append(tc.POLICYTOOL)
        return binaries

    def _get_excludes(self):
        excludes = super()._get_excludes()
        excludes.extend(["hsdb", "clhsdb"])
        return excludes

    def _get_checked_masters(self):
        return [tc.JAVA, tc.JAVAC]


class OpenJdk8JfrArchs(OpenJdk8):
    def __init__(self):
        super().__init__()
        for package in self.checked_subpackages:
            self.missing_manpages[package] = ["jfr"]


class OpenJdk11(OpenJdk8):
    def __init__(self):
        super().__init__()
        for package in self.checked_subpackages:
            self.missing_manpages[package] = ["jdeprscan", "jhsdb", "jimage", "jlink", "jmod", "jshell", "jfr"]

    def _clean_up_binaries(self, binaries, master, usr_bin):
        return binaries


class OpenJdk11NoJaotcMan(OpenJdk11):
    def __init__(self):
        super().__init__()
        for package in self.checked_subpackages:
            self.missing_manpages[package].append("jaotc")


class OpenJdk11s390x(OpenJdk11):
    def __init__(self):
        super().__init__()
        self.checked_subpackages = [tc.DEVEL]
        for suffix in tc.get_debug_suffixes():
            for subpkg in self.checked_subpackages.copy():
                self.checked_subpackages.append(subpkg + suffix)
        for package in self.checked_subpackages:
            self.missing_manpages[package].remove("jhsdb")


class OpenJdk11JfrArchs(OpenJdk11):
    def __init__(self):
        super().__init__()
        for package in self.checked_subpackages:
            self.missing_manpages[package].append("jfr")


class OpenJdk17(OpenJdk11):
    pass


class OpenJdk17s390x(OpenJdk17):
    def __init__(self):
        super().__init__()
        self.checked_subpackages = [tc.DEVEL]
        for suffix in tc.get_debug_suffixes():
            for subpkg in self.checked_subpackages.copy():
                self.checked_subpackages.append(subpkg + suffix)
        for package in self.checked_subpackages:
            self.missing_manpages[package].remove("jhsdb")


class OpenJdk17JaotcMan(OpenJdk17):
    pass


class ITW(ManpageTestMethods):
    def _clean_sdk_from_jre(self, bins, packages):
        return bins

    def _clean_up_binaries(self, binaries, master, usr_bin):
        bins = self._clean_default_mpges(usr_bin, binaries)
        bs = []
        for b in bins:
            bs.append(b.replace(".itweb", ""))
        return bs

    def _get_subpackages(self):
        return [tc.DEFAULT]

    def _get_checked_masters(self):
        return [tc.LIBJAVAPLUGIN + "." + self._get_arch()]

    def _get_target(self, master):
        return "/usr/bin"

    def _get_manpage_suffixes(self, subpackage):
        return [MANPAGE_SUFFIX, "-itweb" + MANPAGE_SUFFIX]

    def _itw_plugin_bin_location(self):
        return "/usr/lib"

    def _itw_plugin_link_location(self):
        return "/usr/lib/mozilla/plugins"

    def _get_extra_bins(self, plugin_bin_content):
        ls = mexe.DefaultMock().execute_ls(self._itw_plugin_bin_location())
        if ls[1] != 0:
            raise NotADirectoryError("dir not found")
        plugin_bin = list(set(ls[0].split("\n")) - set(plugin_bin_content))
        return plugin_bin

    # manpage files might differ from binary names
    def _get_manpage_files_names(self, list_of_bins, plugin_bin_content):
        bins = []
        for binary in list_of_bins:
            if binary == tc.ICED_TEA_PLUGIN_SO:
                bins.append("icedteaweb-plugin")
            else:
                bins.append(binary)

        return bins

    # bin links might differ from binaries
    def _get_manpage_link_names(self, list_of_bins):
        links = []
        for binary in list_of_bins:
            if binary == "itweb-settings":
                links.append("ControlPanel")
            elif binary == tc.ICED_TEA_PLUGIN_SO:
                links.append("javaplugin")
            else:
                links.append(binary)

        # binary links
        return links

    def iced_tea_web_check(self, manpages_with_postcript=None, manpages_without_postscript=None):
        itw_manpage_link = "icedtea-web.1.gz"
        itw_manpage_file = "icedtea-web.1.gz"
        self._document("IcedTea Web has an " + itw_manpage_file + " man page, that has no binary and " +
                       itw_manpage_link + " man page, that has no slave.")
        tu.passed_or_failed(self, itw_manpage_file in manpages_without_postscript[tc.DEFAULT],
                         itw_manpage_file + " manpage file missing in " + tc.DEFAULT)
        tu.passed_or_failed(self, itw_manpage_link in manpages_with_postcript[tc.DEFAULT],
                         itw_manpage_link + " manpage link missing in " + tc.DEFAULT)
        return


class Itw64Bit(ITW):
    def _itw_plugin_bin_location(self):
        return "/usr/lib64"

    def _itw_plugin_link_location(self):
        return "/usr/lib64/mozilla/plugins"


class Oracle(ManpageTestMethods):
    def _get_subpackages(self):
        return [tc.DEFAULT, tc.DEVEL, tc.PLUGIN]

    def _clean_up_binaries(self, binaries, master, usr_bin):
        return binaries

    def _get_checked_masters(self):
        return [tc.JAVA, tc.JAVAC]

    def _get_manpage_suffixes(self, subpackage):
        return [MANPAGE_SUFFIX, "-" + self.rpms.getNvr() + "." + self._get_arch() + MANPAGE_SUFFIX]

    def _get_excludes(self):
        return tc.oracle_exclude_list()


class Oracle6(Oracle):
    def _get_manpage_suffixes(self, subpackage):
        return [MANPAGE_SUFFIX, "-" + self.rpms.getMajorPackage() + "." + self._get_arch() + MANPAGE_SUFFIX]

    def _get_excludes(self):
        return []


class Ibm(ManpageTestMethods):
    def man_page_test(self, pkgs):
        self._document("Ibm binaries do not have manpages.")
        return self.passed, self.failed

    def manpage_file_check(self, bins, subpackage=None, plugin_bin_content=None, manpages_without_postscript=None):
        return

    def manpage_links_check(self, bins, subpackage=None, manpages_with_postscript=None, manpage_files=None):
        return


class Temurin8(ManpageTestMethods):
    def __init__(self):
        super().__init__()
        self.missing_manpages[tc.JDK] = ["jfr", "clhsdb", "hsdb"]
        self.checked_subpackages = [tc.JDK]

    def _get_subpackages(self):
        return [tc.JDK, tc.JRE]

    def _get_checked_masters(self):
        return [tc.JAVA]

    def _clean_sdk_from_jre(self, bins, packages):
        return bins

    def _get_manpage_suffixes(self, subpackage):
        return [TEMURIN_MANPAGE_SUFFIX, TEMURIN_MANPAGE_SUFFIX]

    def manpage_file_check(self, bins, subpackage=None, plugin_bin_content=None, manpages_without_postscript=None):
        """
        temurins are treated a little differently, as manpage files and links have the same naming, therefore the
        manpage_file_check which is normally returning list of manpage files to be subtracted from manpage dir contents
        in order to get the manpage links list, must be empty
        """
        super().manpage_file_check(bins, subpackage, plugin_bin_content, manpages_without_postscript)
        return []

    def _get_manpages_without_postscript(self, default_mans, subpkg):
        return self._clean_default_mpges(default_mans,
                                  mexe.DefaultMock().execute_ls(tc.JVM_DIR + "/" + self.rpms.getMajorPackage() + "-" + subpkg + "/man/man1")[0]
                                  .split("\n"))


class Temurin11(Temurin8):
    def __init__(self):
        super().__init__()
        self.missing_manpages[tc.JDK] = ["jfr", "jaotc", "jdeprscan", "jhsdb", "jimage", "jlink", "jmod", "jshell"]
        self.missing_manpages[tc.JRE] = ["jaotc", "jfr", "jrunscript"]
        self.checked_subpackages.append(tc.JRE)

class Temurin17(Temurin11):
    def __init__(self):
        super().__init__()
        for pkg in self.missing_manpages.keys():
            self.missing_manpages[pkg].remove("jaotc")


class ManpageTests(bt.BaseTest):
    instance = None

    def test_manpages(self):
        pkgs = self.getBuild()
        return self.csch.man_page_test(pkgs)

    def setCSCH(self):
        ManpageTests.instance = self
        rpms = rc.RuntimeConfig().getRpmList()
        self.log("Checking man pages for " + rpms.getMajorPackage(), vc.Verbosity.TEST)

        if rpms.getVendor() == gc.OPENJDK or rpms.getVendor() == gc.OPENJ9:
            if rpms.getMajorVersionSimplified() == "8":
                if self.getCurrentArch() in gc.getIx86archs() + gc.getAarch64Arch() + gc.getPower64Achs() + gc.getX86_64Arch():
                    self.csch = OpenJdk8JfrArchs()
                    return
                else:
                    self.csch = OpenJdk8()
                    return
            elif int(rpms.getMajorVersionSimplified()) == 11:
                if self.getCurrentArch() in gc.getX86_64Arch() + gc.getAarch64Arch():
                    self.csch = OpenJdk11NoJaotcMan()
                    return
                else:
                    if rpms.isRhel() and self.getCurrentArch() in gc.getS390Arch() + gc.getPpc32Arch():
                        self.csch = OpenJdk11()
                    elif self.getCurrentArch() in gc.getS390xArch():
                        self.csch = OpenJdk11s390x()
                    else:
                        self.csch = OpenJdk11()
                    return
            elif int(rpms.getMajorVersionSimplified()) >= 17:
                if self.getCurrentArch() in gc.getX86_64Arch() + gc.getAarch64Arch():
                    self.csch = OpenJdk17JaotcMan()
                    return
                else:
                    if rpms.isRhel() and self.getCurrentArch() in gc.getS390Arch() + gc.getPpc32Arch():
                        self.csch = OpenJdk17()
                    elif self.getCurrentArch() in gc.getS390xArch():
                        self.csch = OpenJdk17s390x()
                    else:
                        self.csch = OpenJdk17()
                    return
            else:
                raise ex.UnknownJavaVersionException("Unknown java version.")

        elif rpms.getVendor() == gc.ITW:
            if self.getCurrentArch() in gc.getX86_64Arch() + gc.getPower64Achs() + \
                    gc.getAarch64Arch() + gc.getS390xArch():
                self.csch = Itw64Bit()
                return
            else:
                self.csch = ITW()
                return
        elif rpms.getVendor() == gc.SUN or rpms.getVendor() == gc.ORACLE:
            if rpms.getMajorVersionSimplified() == "6":
                self.csch = Oracle6()
                return
            elif rpms.getMajorVersionSimplified() == "7" or rpms.getMajorVersionSimplified() == "8":
                self.csch = Oracle()
                return
            else:
                raise ex.UnknownJavaVersionException("Unknown java version.")

        elif rpms.getVendor() == gc.IBM:
            self.csch = Ibm()
            return
        elif rpms.getVendor() == gc.ADOPTIUM:
            if int(rpms.getMajorVersionSimplified()) == 8:
                self.csch = Temurin8()
                return
            elif int(rpms.getMajorVersionSimplified()) == 11:
                self.csch = Temurin11()
                return
            else:
                self.csch = Temurin17()
                return
        else:
            raise ex.UnknownJavaVersionException("Unknown platform, java was not identified.")


def testAll():
    return ManpageTests().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Man page conventions:")
    return ManpageTests().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)
    return ManpageTests().execute_special_docs()


if __name__ == "__main__":
    main(sys.argv[1:])
