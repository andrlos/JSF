import testcases.alternativesTests.binaries_test_methods as bsm
import utils.pkg_name_split as ns
import testcases.alternativesTests.binaries_test_paths as btp
import utils.test_constants as tc
import utils.test_utils as tu
import utils.mock.mock_executor as mexe
import outputControl.logging_access as la

# This script should contain only configuration specific implemetation of the method and overriden methods code.
# Default methods should be always placed in methods or paths files.
# Respect the class naming purpose, inheritance (if possible), and class placement (or this gets very messy)!!!


class OpenJdk8(bsm.BinarySlaveTestMethods):
    def _policytool_binary_subpackages(self):
        subpkgs = [tc.DEFAULT, tc.DEVEL]
        for suffix in tc.get_debug_suffixes():
            subpkgs.extend([tc.DEVEL + suffix, tc.DEFAULT + suffix])
        return subpkgs

    def _get_binary_directory(self, name):
        return super(btp.PathTest, self)._get_binary_directory(name)

    def handle_policytool(self, args=None):
        self._document(tc.POLICYTOOL + " is a binary that behaves differently than normal binaries. It has binaries in {} "
                                    "subpackages, but slaves are in {} "
                                    "subpackages.".format(" and ".join(self._policytool_binary_subpackages()),
                                                          " and ".join(self._policytool_slave_subpackages())))
        for subpackage in self._policytool_binary_subpackages():
            try:
                self.installed_binaries[subpackage].remove(tc.POLICYTOOL)
                tu.passed_or_failed(self, True, "")
            except KeyError:
                 la.LoggingAccess().log(subpackage + " - subpkg not present. This should be handled by subpkg_test")
            except ValueError:
                tu.passed_or_failed(self, False, tc.POLICYTOOL + " binary not present in " + subpackage)
        for subpkg in self._policytool_slave_subpackages():
            try:
                self.installed_slaves[subpkg].remove(tc.POLICYTOOL)
                tu.passed_or_failed(self, True, "")
            except KeyError:
                la.LoggingAccess().log(subpkg + " - subpkg not present. This should be handled by subpkg_test")
            except ValueError:
                tu.passed_or_failed(self, False, tc.POLICYTOOL + " slave not present in " + subpkg)
        return

    def _policytool_slave_subpackages(self):
        subpkgs = [tc.HEADLESS]
        for suffix in tc.get_debug_suffixes():
            subpkgs.extend([tc.HEADLESS + suffix])
        return subpkgs

    def _get_subpackages_with_binaries(self):
        subpkgs = [tc.DEFAULT, tc.HEADLESS, tc.DEVEL]
        for suffix in tc.get_debug_suffixes():
            subpkgs.extend([tc.HEADLESS + suffix, tc.DEVEL + suffix, tc.DEFAULT + suffix])
        return subpkgs

    def _get_jre_subpackage(self):
        subpkgs = [tc.HEADLESS]
        for suffix in tc.get_debug_suffixes():
            subpkgs.extend([tc.HEADLESS + suffix])
        return subpkgs

    def _get_sdk_subpackage(self):
        subpkgs = []
        for suffix in tc.get_debug_suffixes():
            subpkgs.extend([tc.DEVEL + suffix])
        return super()._get_sdk_subpackage() + subpkgs


class OpenJdk8Jfx(OpenJdk8):
    def _jfx_check(self, list_of_elements, subpackage, slave_or_bin):
        """
        OpenJFX packaging is broken by design - binaries are in ojfx-devel, links are in headless.
        This is fixed by this method and documented.
        """
        jfx_bins = tc.get_openjfx_binaries()
        for jfxbin in jfx_bins:
            try:
                list_of_elements[subpackage].remove(jfxbin)
                tu.passed_or_failed(self, True, "")
            except ValueError:
                tu.passed_or_failed(self, False, jfxbin + " " + slave_or_bin + " not found in " + subpackage)
        return

    def remove_binaries_without_slaves(self, args=None):
        for subpackage in self.installed_binaries.keys():
            if "openjfx-devel" in subpackage:
                self._jfx_check(self.installed_binaries, subpackage, "binary")
        return


class OpenJdk8NoExports(OpenJdk8):
    def check_exports_slaves(self, args=None):
        return


class OpenJdk8NoExportsJfx(OpenJdk8Jfx):
    def check_exports_slaves(self, args=None):
        return

# TODO: check whether these last two exports classes are indeed needed


class OpenJdk11(OpenJdk8):
    DEFAULT_BINARIES = []
    DEVEL_BINARIES = ['jar', 'jarsigner', 'javac', 'javadoc', 'javap', 'jcmd',
                      'jconsole',
                      'jdb', 'jdeprscan', 'jdeps', 'jhsdb', 'jimage', 'jinfo', 'jlink', 'jmap', 'jmod', 'jps',
                      'jrunscript',
                      'jshell', 'jstack', 'jstat', 'jstatd', 'rmic', 'serialver', "jfr"]
    HEADLESS_BINARIES = ["java", "jjs", "keytool", "pack200",
                         "rmid", "rmiregistry", "unpack200", 'alt-java']

    def _get_binaries_as_dict(self):
        dict = {tc.DEFAULT: self.DEFAULT_BINARIES,
                tc.DEVEL: self.DEVEL_BINARIES,
                tc.HEADLESS: self.HEADLESS_BINARIES}
        for suffix in tc.get_debug_suffixes():
            for subpkg in [tc.DEFAULT, tc.DEVEL, tc.HEADLESS]:
                dict[subpkg + suffix] = dict[subpkg]
        return dict

    def _get_binary_directory_path(self, name):
        for suffix in tc.get_debug_suffixes():
            if suffix in name:
                return tc.JVM_DIR + "/" + tu.get_32bit_id_in_nvra(ns.get_nvra(name)) + suffix + tc.SDK_DIRECTORY
        return tc.JVM_DIR + "/" + tu.get_32bit_id_in_nvra(ns.get_nvra(name)) + tc.SDK_DIRECTORY

    def _check_binaries_against_hardcoded_list(self, binaries, subpackage):
        hardcoded_binaries = self._get_binaries_as_dict()
        if not tu.passed_or_failed(self, subpackage in hardcoded_binaries.keys(), "Binaries in unexpected subpackage: "
                                                                                  + subpackage):
            return
        tu.passed_or_failed(self, sorted(binaries) == sorted(hardcoded_binaries[subpackage]),
                                   "Hardcode check: binaries are not as expected in {} subpackage. Missing binaries: {}."
                                   " Extra binaries: {}".format(subpackage, tu.two_lists_diff(hardcoded_binaries[subpackage],
                                                                                  binaries),
                                                                tu.two_lists_diff(binaries,
                                                                                  hardcoded_binaries[subpackage])))
        return

    def check_exports_slaves(self, args=None):
        return

    def all_jre_in_sdk_check(self, args=None):
        # binaries from jre pkg not permitted in sdk pkg since ojdk11 as this is handeled by install dependency
        jre_subpackages = self._get_jre_subpackage()
        sdk_subpackages = self._get_sdk_subpackage()
        self._document("Jre binaries must be present in {} subpackages. Jre slaves are in {} subpackages. "
                       "Sdk binaries must be present in {} subpackages. Sdk slaves are in {} "
                       "subpackages. ".format(" and ".join(jre_subpackages + sdk_subpackages),
                                              " and ".join(jre_subpackages),
                                              " and ".join(sdk_subpackages),
                                              " and ".join(sdk_subpackages)))
        current_subpkg = ""
        for subpkg in jre_subpackages:
            for sdk_subpkg in sdk_subpackages:
                try:
                    if self._extract_suffix_from_subpkg(subpkg) == self._extract_suffix_from_subpkg(sdk_subpkg):
                        current_subpkg = subpkg
                        jre = self.installed_binaries[current_subpkg].copy()
                        current_subpkg = sdk_subpkg
                        sdk = self.installed_binaries[current_subpkg].copy()
                    else:
                        continue
                except KeyError:
                    la.LoggingAccess().log("Subpkg " + current_subpkg + " not containing binaries or is missing.")
                    continue
                for j in jre:
                    tu.passed_or_failed(self, j not in sdk, "Binary {} in both jre and sdk subpkgs, this is unwanted since ojdk11".format(j))
        return

    def _policytool_slave_subpackages(self):
        return [tc.HEADLESS] + [tc.HEADLESS + suffix for suffix in tc.get_debug_suffixes()]

    def _policytool_binary_subpackages(self):
        return [tc.DEFAULT] + [tc.DEFAULT + suffix for suffix in tc.get_debug_suffixes()]

    def document_jre_sdk(self, args=None):
        return

    def check_java_cgi(self, args=None):
        return

    def handle_policytool(self, args=None):
        self._document("From JDK 10, there is no policytool.")
        return

    def _get_subpackages_with_binaries(self):
        subpackages = super()._get_subpackages_with_binaries()
        for pkg in subpackages:
            if tc.DEFAULT in pkg:
                subpackages.remove(pkg)
        return subpackages


class OpenJdk11x64(OpenJdk11):
    DEFAULT_BINARIES = []
    DEVEL_BINARIES = ['jar', 'jaotc', 'jarsigner', 'javac', 'javadoc', 'javap', 'jcmd',
                      'jconsole',
                      'jdb', 'jdeprscan', 'jdeps', 'jhsdb', 'jimage', 'jinfo', 'jlink', 'jmap', 'jmod', 'jps',
                      'jrunscript',
                      'jshell', 'jstack', 'jstat', 'jstatd', 'rmic', 'serialver', "jfr"]
    HEADLESS_BINARIES = ["java", "jjs", "keytool", "pack200",
                         "rmid", "rmiregistry", "unpack200", 'alt-java']


class OpenJdk11NoJhsdb(OpenJdk11):
    DEFAULT_BINARIES = []
    DEVEL_BINARIES = ['jar', 'jarsigner', 'javac', 'javadoc', 'javap', 'jcmd',
                      'jconsole',
                      'jdb', 'jdeprscan', 'jdeps', 'jimage', 'jinfo', 'jlink', 'jmap', 'jmod', 'jps',
                      'jrunscript',
                      'jshell', 'jstack', 'jstat', 'jstatd', 'rmic', 'serialver', "jfr"]
    HEADLESS_BINARIES = ["java", "jjs", "keytool", "pack200",
                         "rmid", "rmiregistry", "unpack200", 'alt-java']


class OpenJdkLatest(OpenJdk11):
    DEFAULT_BINARIES = []
    DEVEL_BINARIES = ['jar', 'jarsigner', 'javac', 'javadoc', 'javap', 'jcmd',
                      'jconsole',
                      'jdb', 'jdeprscan', 'jdeps', 'jhsdb', 'jimage', 'jinfo', 'jlink', 'jmap', 'jmod', 'jps',
                      'jrunscript',
                      'jshell', 'jstack', 'jstat', 'jstatd', 'serialver', 'jfr', 'jpackage', 'jwebserver']
    HEADLESS_BINARIES = ["java", "keytool", "rmiregistry"]

    def remove_binaries_without_slaves(self, args=None):
        subpackage = self._get_jre_subpackage()[0]
        if "devel" in subpackage:
            self.installed_binaries[subpackage].remove("jfr")


class OpenJdkLatestNoJhsdb(OpenJdkLatest):
    DEFAULT_BINARIES = []
    DEVEL_BINARIES = ['jar', 'jarsigner', 'javac', 'javadoc', 'javap', 'jcmd',
                      'jconsole',
                      'jdb', 'jdeprscan', 'jdeps', 'jimage', 'jinfo', 'jlink', 'jmap', 'jmod', 'jps',
                      'jrunscript',
                      'jshell', 'jstack', 'jstat', 'jstatd', 'serialver', 'jfr', 'jpackage']
    HEADLESS_BINARIES = ["java", "keytool", "rmiregistry", 'alt-java']


class Ibm(bsm.BinarySlaveTestMethods):
    def _policytool_slave_subpackages(self):
        return ["headless"]

    def _policytool_binary_subpackages(self):
        return [tc.DEFAULT, tc.DEVEL]

    def handle_policytool(self, args=None):
        OpenJdk8.handle_policytool(self)
        return
    # classic and j9vm are folders, not binaries
    def _remove_excludes(self):
        subpackage = self._get_jre_subpackage()[0]
        excludes = tc.get_ibm_folders()
        try:
            for e in excludes:
                self.installed_binaries[subpackage].remove(e)
        except ValueError:
            pass
        finally:
            return

    def remove_binaries_without_slaves(self, args=None):
        subpackage = self._get_jre_subpackage()[0]
        excludes = tc.get_ibm_k_bins() + tc.get_ibm_ikey_bins()
        self._document(" and ".join(excludes) + " are binaries present in {} subpackage. They are not in {} subpackage "
                                                "and have no slaves in alternatives.".format(subpackage,
                                                                                           self._get_sdk_subpackage()[0]))
        for e in excludes:
            try:
                self.installed_binaries[subpackage].remove(e)
                tu.passed_or_failed(self, True, "")
            except ValueError:
                tu.passed_or_failed(self, False, e + " not present in " + subpackage + " binaries.")
        return

    def handle_plugin_binaries(self, args=None):
        plugin_binaries = tc.get_plugin_binaries()
        ssubpackages = self._get_jre_subpackage()
        bsubpackages = self._get_jre_subpackage() + self._get_sdk_subpackage()
        self._document("{} are binaries replacing {} subpackage. They are present in {} subpackages and their slaves"
                       " are in {} subpackages.".format(" and ".join(plugin_binaries), tc.PLUGIN,
                                                        " and ".join(bsubpackages)
                                                        , "".join(ssubpackages)))
        self._check_plugin_binaries_and_slaves_are_present(bsubpackages, ssubpackages)
        return

    def _check_plugin_binaries_and_slaves_are_present(self, bsubpackages, ssubpackages):
        for pbinary in tc.get_plugin_binaries():
            for subpackage in bsubpackages:
                tu.passed_or_failed(self, pbinary in self.installed_binaries[subpackage], "Missing plugin binary " + pbinary + " in " + subpackage)
            for subpackage in ssubpackages:
                tu.passed_or_failed(self, pbinary not in self.installed_slaves[subpackage], "Missing plugin slave " + pbinary + " in " + subpackage)

    def _check_plugin_bins_and_slaves_are_not_present(self, subpackages):
        for pbinary in tc.get_plugin_binaries():
            for subpackage in subpackages:
                if not tu.passed_or_failed(self, pbinary not in self.installed_binaries[subpackage],
                                           pbinary + " should not be in " + subpackage +
                                           " because this subpackage must not contain any plugin binaries."):
                    self.installed_binaries[subpackage].remove(pbinary)
                if not tu.passed_or_failed(self, pbinary not in self.installed_slaves[subpackage],
                                           pbinary + " should not be in " + subpackage +
                                           " because this subpackage must not contain plugin slaves."):
                    self.installed_slaves[subpackage].remove(pbinary)
        return


class Ibm390Architectures(Ibm):
    def handle_plugin_binaries(self, args=None):
        plugin_binaries = tc.get_plugin_binaries()
        self._document("{} are not present in binaries in any subpackage. This architecture "
                       "also has no {} subpackages.".format(" and ".join(plugin_binaries), tc.PLUGIN))
        self._check_plugin_bins_and_slaves_are_not_present(self._get_subpackages_with_binaries())
        return


class IbmWithPluginSubpackage(Ibm):
    def _get_checked_masters(self):
        return super()._get_checked_masters() + [tc.LIBJAVAPLUGIN]

    def _get_subpackages_with_binaries(self):
        return super()._get_subpackages_with_binaries() + [tc.PLUGIN]

    def handle_plugin_binaries(self, args=None):
        plugin_binaries = tc.get_plugin_binaries()
        subpackages_without_pbins = self._get_jre_subpackage() + self._get_sdk_subpackage()
        self._document("{} are binaries related with {}. They are present and have slaves only in {} "
                       "subpackages.".format(" and ".join(plugin_binaries), tc.PLUGIN, tc.PLUGIN))
        self._check_plugin_bins_and_slaves_are_not_present(subpackages_without_pbins)
        self._check_plugin_binaries_and_slaves_are_present([tc.PLUGIN], [tc.PLUGIN])
        return


class IbmArchMasterPlugin(IbmWithPluginSubpackage):
    def _get_checked_masters(self):
        return [tc.JAVA, tc.JAVAC, tc.LIBJAVAPLUGIN + "." + self._get_arch()]


class Ibm8Rhel8(IbmArchMasterPlugin):

    def _get_exports_slaves_jre(self):
        return []

    def _get_exports_slaves_sdk(self):
        return []

    def check_java_cgi(self, args=None):
        return

    def _get_jre_subpackage(self):
        return [tc.HEADLESS]

    def _check_plugin_binaries_and_slaves_are_present(self, bsubpackages, ssubpackages):
        return

class Ibm8Rhel8S390X(Ibm390Architectures):
    def _get_exports_slaves_jre(self):
        return []

    def _get_exports_slaves_sdk(self):
        return []

    def check_java_cgi(self, args=None):
        return

    def _get_jre_subpackage(self):
        return [tc.HEADLESS]

    def _check_plugin_binaries_and_slaves_are_present(self, bsubpackages, ssubpackages):
        return


class Oracle6(IbmWithPluginSubpackage):
    def _get_binary_directory(self, name):
        path = self._get_32bit_id_in_nvra(ns.get_nvra(name))
        release = path.split("-")[-1]
        path = path.replace("-" + release, "")
        return path

    def _remove_excludes(self):
        return

    def remove_binaries_without_slaves(self, args=None):
        return

    def handle_plugin_binaries(self, args=None):
        plugin_binaries = tc.get_plugin_binaries()
        self._document("{} are no longer present in binaries in any subpackage.".format(" and ".join(plugin_binaries)))
        self._check_plugin_bins_and_slaves_are_not_present(self._get_subpackages_with_binaries())
        return

    def _get_subpackages_with_binaries(self):
        return bsm.BinarySlaveTestMethods(self.binaries_test)._get_subpackages_with_binaries()


class OracleNoArchPlugin(Oracle6):
    def _get_checked_masters(self):
        return [tc.JAVA, tc.JAVAC, tc.LIBNSSCKBI_SO]


class Oracle6ArchPlugin(Oracle6):
    def _get_checked_masters(self):
        return [tc.JAVA, tc.JAVAC, tc.LIBNSSCKBI_SO + "." + self._get_arch()]

    def _get_binary_directory(self, name):
        return super()._get_binary_directory(name) + "." + self._get_arch()


class Oracle7(Oracle6ArchPlugin):
    def _remove_excludes(self):
        exclude_list = tc.oracle_exclude_list()
        for exclude in exclude_list:
            self._document("{} is not a binary. It is present in {} subpackages binaries. It has "
                           "no slave in alternatives.".format(exclude, tc.DEVEL))
            try:
                self.installed_binaries[tc.DEVEL].remove(exclude)
                tu.passed_or_failed(self, True, "")
            except ValueError:
                tu.passed_or_failed(self, False, exclude + " not present in " + tc.DEVEL)
        return

    def _get_subpackages_with_binaries(self):
        subpackages = bsm.BinarySlaveTestMethods(self.binaries_test)._get_subpackages_with_binaries()
        subpackages.append(tc.JAVAFX)
        return subpackages

    def _get_checked_masters(self):
        masters = super()._get_checked_masters()
        return masters

    def _get_binary_directory(self, name):
        return btp.PathTest(self.binaries_test)._get_binary_directory(name)


class Oracle8(Oracle7):
    def handle_plugin_binaries(self, args=None):
        return IbmWithPluginSubpackage(self.binaries_test).handle_plugin_binaries()


class Itw(bsm.BinarySlaveTestMethods):
    def check_java_cgi(self, args=None):
        return

    def all_jre_in_sdk_check(self, args=None):
        return

    def check_exports_slaves(self, args=None):
        self._document("ITW has no exports slaves.")
        return

    def _get_subpackages_with_binaries(self):
        return [tc.DEFAULT]

    def handle_plugin_binaries(self, args=None):
        self._document("ITW replaces plugin package for OpenJDK")
        return

    def document_jre_sdk(self, args=None):
        return

    def doc_extra_binary(self, args=None):
        self._document(tc.ITWEB_SETTINGS + " is an iced-tea binary. Its slave is " + tc.CONTROL_PANEL)

    def check_subdirectory_slaves(self, args=None):
        return

    def _get_all_binaries_and_slaves(self, pkgs):
        mexe.DefaultMock().provideCleanUsefullRoot()
        original_binaries = mexe.DefaultMock().execute_ls(tc.USR_BIN)[0].split("\n")
        installed_binaries, installed_slaves = super()._get_all_binaries_and_slaves(pkgs)
        installed_binaries = self._remove_links_from_usr_bin(installed_binaries)
        for subpackage in installed_binaries.keys():
            all_binaries = installed_binaries[subpackage]
            installed_binaries[subpackage] = tu.two_lists_diff(all_binaries, original_binaries)

        settings = tc.ITWEB_SETTINGS
        bins = []
        for b in installed_binaries[tc.DEFAULT]:
            bins.append(b.replace(".itweb", ""))
        installed_binaries[tc.DEFAULT] = bins
        try:
            installed_binaries[tc.DEFAULT].append(tc.CONTROL_PANEL)
            tu.passed_or_failed(self, True, "")
        except ValueError:
            tu.passed_or_failed(self, False, settings + " binary not in " + tc.DEFAULT + " subpackage")
        return installed_binaries, installed_slaves
    
    def _get_binary_directory_path(self, name):
        return tc.USR_BIN

    def _get_checked_masters(self):
        return [tc.JAVAWS + "." + tu.validate_arch_for_rpms(self._get_arch())]

    def _remove_links_from_usr_bin(self, installed_binaries):
        # perhaps doc
        links = []
        for b in installed_binaries[tc.DEFAULT]:
            if ".itweb" not in b:
                links.append(b)
        for l in links:
            installed_binaries[tc.DEFAULT].remove(l)
        return installed_binaries


class Temurin8(bsm.BinarySlaveTestMethods):
    JDK_BINARIES = ["appletviewer", "javac", "jdeps", "jsadebugd", "policytool", "unpack200",
                    "clhsdb", "javadoc", "jfr", "jstack", "rmic", "wsgen",
                    "extcheck", "javah", "jhat", "jstat", "rmid", "wsimport",
                    "hsdb", "javap", "jinfo", "jstatd", "rmiregistry", "xjc",
                    "idlj", "jjs", "keytool", "schemagen",
                    "jar", "jcmd", "jmap", "native2ascii", "serialver",
                    "jarsigner", "jconsole", "jps", "orbd", "servertool",
                    "java", "jdb", "jrunscript", "pack200", "tnameserv"]

    JRE_BINARIES = ["java", "keytool", "pack200", "rmid", "servertool", "unpack200",
                    "jjs", "orbd", "policytool", "rmiregistry", "tnameserv"]
    def _get_subpackages_with_binaries(self):
        return [tc.JRE, tc.JDK]

    def _get_binary_directory_path(self, name):
        return tc.JVM_DIR + "/{}/bin".format(ns.get_package_name(name))

    def _get_jre_subpackage(self):
        return [tc.JRE]

    def _get_sdk_subpackage(self):
        return [tc.JDK]

    def check_exports_slaves(self, args=None):
        self._document("Temurin has no exports slaves.")
        return

    def _get_binaries_as_dict(self):
        dict = {tc.JDK: self.JDK_BINARIES,
                tc.JRE: self.JRE_BINARIES}
        for suffix in tc.get_debug_suffixes():
            for subpkg in [tc.DEFAULT, tc.DEVEL, tc.HEADLESS]:
                dict[subpkg + suffix] = dict[subpkg]
        return dict

    def _check_binaries_against_hardcoded_list(self, binaries, subpackage):
        hardcoded_binaries = self._get_binaries_as_dict()
        if not tu.passed_or_failed(self, subpackage in hardcoded_binaries.keys(), "Binaries in unexpected subpackage: "
                                                                                  + subpackage):
            return
        tu.passed_or_failed(self, sorted(binaries) == sorted(hardcoded_binaries[subpackage]),
                                   "Hardcode check: binaries are not as expected in {} subpackage. Missing binaries: {}."
                                   " Extra binaries: {}".format(subpackage, tu.two_lists_diff(hardcoded_binaries[subpackage],
                                                                                  binaries),
                                                                tu.two_lists_diff(binaries,
                                                                                  hardcoded_binaries[subpackage])))
        return


class Temurin11(Temurin8):
    JDK_BINARIES = ["javac", "jdeps", "unpack200",
                    "javadoc", "jfr", "jstack", "rmic", "jstat", "rmid",
                    "javap", "jinfo", "jstatd", "rmiregistry", "jjs", "keytool",
                    "jar", "jcmd", "jmap", "serialver", "jarsigner", "jconsole",
                    "jps", "java", "jdb", "jrunscript", "pack200", "jshell", "jhsdb",
                    "jaotc", "jmod", "jdeprscan", "jimage", "jlink"]
    JRE_BINARIES = ["java", "keytool", "pack200", "rmid", "unpack200",
                    "jjs", "rmiregistry", "jfr", "jrunscript", "jaotc"]


class Temurin17(Temurin11):
    JDK_BINARIES = ["javac", "jdeps", "javadoc", "jfr", "jstack", "jstat",
                    "javap", "jinfo", "jstatd", "rmiregistry", "keytool",
                    "jar", "jcmd", "jmap", "serialver", "jarsigner", "jconsole",
                    "jps", "java", "jdb", "jrunscript", "jshell", "jhsdb",
                    "jmod", "jdeprscan", "jimage", "jlink", "jpackage"]
    JRE_BINARIES = ["java", "keytool", "rmiregistry", "jfr", "jrunscript"]
