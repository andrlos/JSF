import outputControl.logging_access as la
import sys
import re
import utils.core.base_xtest as bt
import config.global_config as gc
import config.runtime_config as rc
import utils
import config.verbosity_config as vc
from utils.mock.mock_executor import DefaultMock
from utils.test_utils import rename_default_subpkg, get_arch, two_lists_diff, get_32bit_id_in_nvra,\
    passed_or_failed
from utils.test_constants import *
import os
from utils import pkg_name_split as pkgsplit
from utils.core.configuration_specific import JdkConfiguration
from utils.core.unknown_java_exception import UnknownJavaVersionException
from outputControl import dom_objects as do

# TODO: is broken for ojdk10 rolling releases


class BaseTest(JdkConfiguration):
    """
    This test is supposed to check all the files in /usr/lib/jvm/nvra and their permissions. If the checked file is
    a link, we check it's target, if it is still in /usr/lib/jvm/nvra dir. We also check man pages located in MAN_DIR.
    """

    def __init__(self):
        super().__init__()
        self.list_of_failed_tests = []
        self.invalid_file_candidates = []

    def _get_target_java_directory(self, name):
        """Returns a directory where jdk is installed (mostly name-version-release-arch)."""
        directory =  get_32bit_id_in_nvra(pkgsplit.get_nvra(name))
        for suffix in get_debug_suffixes():
            if suffix in name:
                directory = directory + suffix
                break
        return directory

    def _skipped_subpackages(self):
        """We might want to skip the subpackages that have post install, but do not add any files into jvm directory."""
        return []

    def doc_test_java_files_permissions(self, pkgs):
        """Main test method body."""
        self._document("On all files extracted from RPMs to {}/nvra and {} apply "
                       "following rules:".format(JVM_DIR, MAN_DIR))
        # get default manpages, since we check these too
        DefaultMock().provideCleanUsefullRoot()
        default_manpages, res = DefaultMock().execute_ls(MAN_DIR)
        default_manpages = default_manpages.split("\n")
        passed_or_failed(self, res == 0, "Default manpages extraction has failed. Manpage tests will be invalid: " + str(res) +
                            str(default_manpages))
        for pkg in pkgs:
            name = os.path.basename(pkg)
            subpackage = rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            PermissionTest.instance.log("Checking {} subpackage...".format(subpackage), vc.Verbosity.TEST)
            if subpackage in subpackages_without_alternatives() + self._skipped_subpackages():
                PermissionTest.instance.log("Skipping " + pkg, vc.Verbosity.TEST)
                continue

            if not DefaultMock().run_all_scriptlets_for_install(pkg):
                continue

            # get content of jvm directory
            jvm_dir = self._get_target_java_directory(name)
            out, result = DefaultMock().executeCommand(["ls -LR " + JVM_DIR + "/" + jvm_dir])
            out = out.split("\n")
            fails = []
            clearedout = []
            for line in out:
                if line.startswith("ls: cannot access"):
                    fails.append(line)
                else:
                    clearedout.append(line)
            if len(fails) > 0:
                la.LoggingAccess().log("Following warning produced while listing files for " + pkg + ":", vc.Verbosity.TEST)
                for line in fails:
                    la.LoggingAccess().log("    " + line)
            if len(clearedout) > 0:
                result = 0
            if not passed_or_failed(self, result == 0, "Java directory not found for " + subpackage +
                                                       ", for desired directory " + jvm_dir):
                continue
            valid_targets = self._parse_output(clearedout, subpackage)
            self.sort_and_test(valid_targets, subpackage, name)

            manpages = two_lists_diff(DefaultMock().execute_ls(MAN_DIR)[0].split("\n"), default_manpages)
            for manpage in manpages:
                self.sort_and_test([MAN_DIR + "/" + manpage], subpackage, name)

        PermissionTest.instance.log("Failed permissions tests: " + "\n    ".join(self.list_of_failed_tests), vc.Verbosity.ERROR)
        PermissionTest.instance.log("Unexpected files, filetypes or errors occured, requires sanity check, these are "
                                    "treated as fails: " + "\n    ".join(self.invalid_file_candidates))
        return self.passed, self.failed

    def _parse_output(self, out, subpackage):
        """Output of the file listing must be parsed into something more readable and easier to process."""
        return_targets = []
        header = re.compile("/[^:]*:")
        current_header = ""
        for line in out:
            if line == "":
                continue
            elif "cannot access" in line:
                if passed_or_failed(self, subpackage == DEVEL and "/bin/" in line,
                                    "In subpackage {} following was found: ".format(subpackage) + line,
                                    "In subpackage {} following was found: ".format(subpackage) + line +
                                    "This might be expected behaviour and should be only sanity checked."):
                    self.invalid_file_candidates.append(line)
                    continue
                else:
                    self.invalid_file_candidates.append(line)
                    PermissionTest.instance.log("Unexpected filetype. Needs manual inspection.")
                continue
            elif header.search(line):
                current_header = header.match(line)
                current_header = current_header.group(0).strip(":")
                continue
            else:
                return_targets.append(current_header + "/" + line)
        return return_targets

    def sort_and_test(self, valid_targets, subpackage=None, name=None):
        """
        Sorts the files and checks whether permissions are as expected. If ever adding any exclude case, it must be
        documented in the _document method.
        """
        self._document("\n - ".join(["Directories should have 755 permissions.",
                                     "Content of bin directory should have 755 permissions",
                                     "All of the files ending with '.so' should have 755 permissions",
                                     "Regular files should have 644 permissions",
                                     "Symbolic links should have 777 permissions.",
                                     "Permissions of a file classes.jsa must be 444."
                                     "Binary jexec and jspawnhelper are exceptions and must be in lib directory and have"
                                     " 755 permissions.",
                                     "Other types of files with different permissions should not be present."]))
        for target in valid_targets:
            out, res = DefaultMock().executeCommand(['stat -c "%F" ' + target])
            if JVM_DIR not in target and MAN_DIR not in target and res == 0:
                passed_or_failed(self, True, "", "This target: " + target + " is located out of the jvm directory. "
                                                                            "These files are not checked.")
                continue
            # this is not easy to reproduce - there is an error in lib directory permissions, but since there is
            # jre subpackage present along with devel (default or headless), this keeps being hidden
            # for now we cover it with this hook, but once reproducible, we will ask for official fix
            # since it behaves correctly so far, this is a PASS
            # TODO: reproduce and fix
            if (target == JVM_DIR + "/" + self._get_target_java_directory(name) + "/lib" and "devel" in subpackage):
                passed_or_failed(self, True, "", target + " in subpackage " + subpackage + ". This is an unknown bug in the"
                                            " framework / jre, that is not reproducible "
                                            "so far. Howewer, in installed JDK, the permissions are correct.")
                continue
            if out == "directory":
                self._test_fill_in(target, out, "755")
            elif out == "regular file" or out == "regular empty file":
                if "/bin/" in target:
                    self._test_fill_in(target, "binary", "755")
                elif ".so" in target:
                    self._test_fill_in(target, "file ending with .so", "755")
                elif "/lib/server/classes.jsa" in target:
                    self._test_fill_in(target, "file classes.jsa", "444")
                elif "/lib/jexec" in target:
                    self._test_fill_in(target, "binary jexec", "755")
                elif "/lib/jspawnhelper" in target:
                    self._test_fill_in(target, "binary jspawnhelper", "755")
                elif target.endswith(".pf") or target.endswith(".data"):
                    self._test_fill_in(target, out, "444")
                elif target.endswith(".template") and "/conf/" not in target:
                    self._test_fill_in(target, out, "444")
                else:
                    self._test_fill_in(target, out, "644")
            elif out == "symbolic link":
                self._test_fill_in(target, out, "777")
                out, res = DefaultMock().executeCommand(["readlink " + target])
                if not passed_or_failed(self, res == 0,
                                        "Target of symbolic link {} does not exist.".format(target) + " Error " + out):
                    continue
                out = self._get_link_full_path(target, out)
                self.sort_and_test([out], subpackage, name)
            else:
                if res != 0:
                    PermissionTest.instance.log("Command stat -c '%F' {} finished with {} exit"
                                                " code".format(target, res))
                    # JRE binaries in SDK packages have broken links that result in failed command.
                    if subpackage == DEVEL and (self._get_target_java_directory(name) + "/jre/bin/") in target:
                        PermissionTest.instance.log("This is expected behaviour in devel subpackage, since this is "
                                                    "consciously broken "
                                                    "symlink to default subpackage binaries. Not treated as fail.")
                        self.passed += 1
                        continue
                    else:
                        passed_or_failed(self, False,
                                         "In subpackage {} following was found: Command stat -c '%F' {} finished"
                                         " with message: {}. ".format(subpackage, target, res, out))
                        self.invalid_file_candidates.append(
                            "Target: " + target + " with result: " + res.__str__() + " and output: " + out)
                        continue


                else:
                    PermissionTest.instance.log("Unexpected filetype. Needs manual inspection.", vc.Verbosity.TEST)
                    passed_or_failed(self, False,
                                     "In subpackage {} following was found: Command stat -c '%F' {} finished"
                                    " with message: {}. ".format(subpackage, target, res, out))

                self.invalid_file_candidates.append(target)

    def _get_link_full_path(self, target, link):
        if link.startswith("/"):
            return link
        parts = target.split("/")
        parts = parts[:-1]
        linkparts = link.split("/")
        suffix = ""
        for part in linkparts:
            if part == "..":
                parts = parts[:-1]
            else:
                suffix += "/" + part
        prefix = "/" + "/".join(parts)
        return prefix + suffix


    def _test_fill_in(self, file, filetype, expected_permission):
        """
        This method takes as an argument path to a file, type of the file for logs, expected permission and checks,
        if it matches results from chroot. It also documents any fails or successful checks.
        """
        out, res = DefaultMock().executeCommand(['stat -c "%a" ' + file])
        if out == "775" and "ibm" in file:
            PermissionTest.instance.log("Skipping " + file + ". Some unzipped Ibm packages are acting wierdly in mock. "
                                                             "Howewer, in installed JDK, the permissions are correct.",
                                        vc.Verbosity.TEST)
            return
        if res != 0:
            passed_or_failed(self, False, filetype + " link is broken, could not find " + file)
            return
        else:
            PermissionTest.instance.log(filetype + " {} exists. Checking permissions... ".format(file),
                                        vc.Verbosity.MOCK)
        for p in range(3):
            if not (int(out[p]) == int(expected_permission[p])):
                passed_or_failed(self, False, "Permissions of {} not as expected, should be {} but is "
                                      "{}.".format(file, expected_permission, out))
                return
        PermissionTest.instance.log(filetype + " {} with permissions {}. Check "
                                    "successful.".format(file, out), vc.Verbosity.MOCK)
        passed_or_failed(self, True, "")
        return


class OpenJdk8(BaseTest):
    def _skipped_subpackages(self):
        subpkgs = [JAVADOCZIP, JAVADOC, DEFAULT]
        for suffix in get_debug_suffixes():
            subpkgs.extend([JAVADOC + suffix, DEFAULT + suffix, JAVADOCZIP + suffix])
        return super()._skipped_subpackages() + subpkgs

    def _get_target_java_directory(self, name):
        directory = super()._get_target_java_directory(name)
        return directory


class Oracle(BaseTest):
    pass


class PermissionTest(bt.BaseTest):
    instance = None

    def test_alternatives_binary_files(self):
        pkgs = self.getBuild()
        return self.csch.doc_test_java_files_permissions(pkgs)

    def setCSCH(self):
        PermissionTest.instance = self
        rpms = rc.RuntimeConfig().getRpmList()
        self.log("Checking files for " + rpms.getMajorPackage(), vc.Verbosity.TEST)
        if rpms.getVendor() == gc.OPENJDK or rpms.getVendor() == gc.OPENJ9:
            if rpms.getMajorVersionSimplified() == "8":
                self.csch = OpenJdk8()
                return
            elif int(rpms.getMajorVersionSimplified()) >= 9:
                self.csch = OpenJdk8()
                return
            else:
                raise UnknownJavaVersionException("Unknown version of OpenJDK.")
        if rpms.getVendor() == gc.ORACLE:
            self.csch = Oracle()
            return

        if rpms.getVendor() == gc.IBM:
            self.csch = BaseTest()
            return

        if rpms.getVendor() == gc.ITW:
            # TODO might be worth to check also other subdirectories
            self.csch = BaseTest()
            return
        if rpms.getVendor() == gc.ADOPTIUM:
            self.csch = BaseTest()
            return
        raise UnknownJavaVersionException("Unknown JDK version!!!")


def testAll():
    return PermissionTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("File permissions conventions")
    return PermissionTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)
    return PermissionTest().execute_special_docs()


if __name__ == "__main__":
    main(sys.argv[1:])
