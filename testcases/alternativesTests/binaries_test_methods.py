import utils.mock.mock_executor as mexe
import utils.pkg_name_split as pkgsplit
import utils.mock.mock_execution_exception as mexc
import os
import config.runtime_config as rc
import testcases.alternativesTests.binaries_test_paths as btp
import utils.test_constants as tc
import utils.test_utils as tu
import outputControl.logging_access as la
import config.verbosity_config as vc


class GetAllBinariesAndSlaves(btp.PathTest):
    rpms = rc.RuntimeConfig().getRpmList()

    def document_subpackages(self, args=None):
        self._document("Binaries and slaves are present in following subpackages: " +
                       ", ".join(self._get_subpackages_with_binaries()))

    def check_exports_slaves(self, args=None):
        jre_slaves = self._get_exports_slaves_jre()
        sdk_slaves = self._get_exports_slaves_sdk()
        jre_subpackages = self._get_jre_subpackage()
        sdk_subpackages = self._get_sdk_subpackage()
        self._document(" and ".join(jre_slaves + sdk_slaves) + " are slaves, that point at export "
                                                               "directories")
        for jsubpkg in jre_subpackages:
            for jslave in jre_slaves:
                try:
                    self.installed_slaves[jsubpkg].remove(jslave)
                    tu.passed_or_failed(self, True, "")
                except ValueError:
                    tu.passed_or_failed(self, False, jslave + " export slave missing in " + jsubpkg)
                except KeyError:
                    tu.passed_or_failed(self, False, "No slaves in " + jsubpkg + " subpkg.")

        for ssubpkg in sdk_subpackages:
            for sslave in sdk_slaves:
                try:
                    self.installed_slaves[ssubpkg].remove(sslave)
                    tu.passed_or_failed(self, True, "")
                except ValueError:
                    tu.passed_or_failed(self, False, sslave + " export slave missing in " + ssubpkg)
                except KeyError:
                    tu.passed_or_failed(self, False, "No slaves in " + ssubpkg + "subpkg.")
        return

    def check_subdirectory_slaves(self, args=None):
        jre_slave = "java"
        sdk_slave = "javac"
        self._document(jre_slave + " and " + sdk_slave + " are slaves that point at directories in /usr/lib/jvm.")
        jre_subpackages = self._get_jre_subpackage()
        sdk_subpackages = self._get_sdk_subpackage()
        for jsubpkg in jre_subpackages:
            try:
                self.installed_slaves[jsubpkg].remove(jre_slave)
                tu.passed_or_failed(self, True, "")
            except (ValueError, KeyError) as e:
                tu.passed_or_failed(self, False, jre_slave + " slave missing in " + jsubpkg)
                self.binaries_test.log(str(e))
        for ssubpkg in sdk_subpackages:
            try:
                self.installed_slaves[ssubpkg].remove(sdk_slave)
                tu.passed_or_failed(self, True, "")
            except (ValueError, KeyError) as e:
                tu.passed_or_failed(self, False, sdk_slave + " slave missing in " + ssubpkg)
                self.binaries_test.log(str(e))
        return

    def get_slaves(self, _subpkg):
        checked_masters = self._get_checked_masters()
        self._document("Checking slaves for masters:"
                       " {}".format(" and ".join(tu.replace_archs_with_general_arch(checked_masters, self._get_arch()))))

        masters = mexe.DefaultMock().get_masters()
        clean_slaves = []
        for m in checked_masters:
            if m not in masters:
                continue
            try:
                slaves = mexe.DefaultMock().get_slaves(m)
            except mexc.MockExecutionException:
                self.binaries_test.log("No relevant slaves were present for " + _subpkg + ".", vc.Verbosity.TEST)
                continue
            self.binaries_test.log("Found slaves for {}: {}".format(_subpkg, str(slaves)), vc.Verbosity.TEST)

            if m in [tc.JAVA, tc.JAVAC]:
                clean_slaves.append(m)

            # skipping manpage slaves
            for slave in slaves:
                if not slave.endswith("1.gz"):
                    clean_slaves.append(slave)

        return clean_slaves

    def _get_all_binaries_and_slaves(self, pkgs):

        for pkg in pkgs:
            name = os.path.basename(pkg)
            _subpkg = tu.rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            if _subpkg in tc.subpackages_without_alternatives() + tc.get_javadoc_dirs():
                self.binaries_test.log("Skipping binaries extraction for " + _subpkg)
                self.skipped.append(_subpkg)
                continue
            if not mexe.DefaultMock().run_all_scriptlets_for_install(pkg):
                self.binaries_test.log("Failed to execute postinstall. Slaves will not be found for " + _subpkg)
            binary_directory_path = self._get_binary_directory_path(name)
            binaries = mexe.DefaultMock().execute_ls(binary_directory_path)

            if binaries[1] != 0:
                self.binaries_test.log("Location {} does not exist, binaries test skipped "
                                       "for ".format(binary_directory_path) + name, vc.Verbosity.TEST)

                continue
            else:
                self.binaries_test.log("Binaries found at {}: {}".format(binary_directory_path,
                                                                         ", ".join(binaries[0].split("\n"))), vc.Verbosity.TEST)

            slaves = self.get_slaves(_subpkg)

            self.installed_slaves[_subpkg] = slaves
            self.installed_binaries[_subpkg] = binaries[0].split("\n")

        return self.installed_binaries, self.installed_slaves


class BinarySlaveTestMethods(GetAllBinariesAndSlaves):
    # checks if all jre binaries are in sdk and deletes them from there
    def all_jre_in_sdk_check(self, args=None):
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
                    la.LoggingAccess().log("Subpkg " + current_subpkg + " not containing binaries and is probably "
                                                                        "missing. This is being reported in subpkg test.")
                for j in jre:
                    try:
                        sdk.remove(j)
                        tu.passed_or_failed(self, True, "")
                    except ValueError:
                        tu.passed_or_failed(self, False, "Binary " + j + " is present in JRE, but is missing in SDK.")
        return

    def _extract_suffix_from_subpkg(self, subpkg):
        for suffix in tc.get_debug_suffixes():
            if suffix in subpkg:
                return suffix
        return ""

    def _perform_all_checks(self):
        tu.passed_or_failed(self, sorted(self.installed_slaves.keys()) == sorted(self.installed_binaries.keys()),
                                "Subpackages that contain binaries and slaves do not match. Subpackages with"
                                "binaries: {}, Subpackages with slaves: {}".format(
                                                                sorted(self.installed_binaries.keys()),
                                                                sorted(self.installed_slaves.keys())))
        try:
            for subpackage in self._get_subpackages_with_binaries():
                if subpackage in self.installed_binaries or subpackage in self.installed_slaves:
                    slaves = self.installed_slaves[subpackage]
                    binaries = self.installed_binaries[subpackage]
                    if(sorted(binaries) != sorted(slaves) and subpackage == "devel" and self.rpms.getMajorVersionSimplified() == 8):
                        diff = tu.two_lists_diff(binaries, slaves)
                        diff = tu.two_lists_diff(diff, self.installed_slaves["headless"])
                    else:
                        diff = []
                    tu.passed_or_failed(self, diff == [],
                                            "Binaries do not match slaves in {}. Missing binaries: {}"
                                            " Missing slaves: {}".format(subpackage, tu.two_lists_diff(slaves, binaries),
                                                                         tu.two_lists_diff(binaries, slaves)))
                    self._check_binaries_against_hardcoded_list(binaries, subpackage)
                else:
                    tu.passed_or_failed(self, False, "No binaries or missing subpkg: " + subpackage)
        except KeyError as err:
            tu.passed_or_failed(self, False, err.__str__())
        return

    # main check, that includes all small checks and at the end compares the binaries with slaves
    def check_binaries_with_slaves(self, pkgs):
        self._document("Every binary must have a slave in alternatives.")
        self._get_all_binaries_and_slaves(pkgs)
        self._remove_excludes()
        self.check_java_cgi()
        self.handle_policytool()
        self.remove_binaries_without_slaves()
        self.handle_plugin_binaries()
        self.all_jre_in_sdk_check()
        self.check_exports_slaves()
        self.check_subdirectory_slaves()
        self._perform_all_checks()
        self.path_test()

        for subpkg in self.installed_binaries.keys():
                    self.binaries_test.log("Presented binaries for {}: ".format(subpkg) +
                                           str(sorted(self.installed_binaries[subpkg])), vc.Verbosity.TEST)
                    self.binaries_test.log("Presented slaves for {}: ".format(subpkg) +
                                           str(sorted(self.installed_slaves[subpkg])), vc.Verbosity.TEST)

        self.binaries_test.log("Failed tests: " + "\n ".join(self.list_of_failed_tests), vc.Verbosity.ERROR)
        return self.passed, self.failed
