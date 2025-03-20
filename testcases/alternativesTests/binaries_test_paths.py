from utils.core.configuration_specific import JdkConfiguration
from utils.mock.mock_executor import DefaultMock
import utils.pkg_name_split as pkgsplit
from utils.mock.mock_execution_exception import MockExecutionException
from utils.test_utils import rename_default_subpkg, log_failed_test
from config.global_config import get_32b_arch_identifiers_in_scriptlets as get_id
import os
from utils.test_constants import *
from utils.test_utils import get_32bit_id_in_nvra, passed_or_failed
import outputControl.logging_access as la
from outputControl import dom_objects as do
import config.verbosity_config as vc


# TODO binary jexec in /usr/lib/jvm/nvra/lib in headless package is not checked on path, or in the directory.
class BaseTest(JdkConfiguration):
    def __init__(self, binariesTest):
        super(BaseTest, self).__init__()
        self.binaries_test = binariesTest
        self.skipped = []
        self.list_of_failed_tests = []
        self.installed_binaries = {}
        self.installed_slaves = {}

    def remove_binaries_without_slaves(self, args=None):
        return

    def _remove_excludes(self):
        return

    def check_exports_slaves(self, args=None):
        return

    def handle_policytool(self, args=None):
        return

    def _check_binaries_against_hardcoded_list(self, binaries, subpackage):
        return

    def handle_plugin_binaries(self, args=None):
        return

    def _get_binary_directory(self, name):
        return get_32bit_id_in_nvra(pkgsplit.get_nvra(name))

    def _get_sdk_subpackage(self):
        return [DEVEL]

    def _get_sdk_debug_subpackage(self):
        return [DEVEL + suffix for suffix in get_debug_suffixes()]

    def _get_binary_directory_path(self, name):
        d = JVM_DIR + "/" + self._get_binary_directory(name)
        for suffix in get_debug_suffixes():
            if suffix + "-" in name:
                d += suffix
        if DEVEL in name or JAVAFX in name:
            return d + SDK_DIRECTORY
        else:
            return d + JRE_DIRECTORY

    def _check_binaries_against_harcoded_list(self, binaries, subpackage):
        return

    def _get_exports_slaves_jre(self):
        return get_exports_slaves_jre()

    def _get_exports_slaves_sdk(self):
        return get_exports_slaves_sdk()

    def _get_jre_subpackage(self):
        return [DEFAULT]

    def _get_checked_masters(self):
        return [JAVA, JAVAC]

    # returns architecture in 32bit identifier
    def _get_arch(self):
        return get_id(self.binaries_test.getCurrentArch())

    def _get_subpackages_with_binaries(self):
        return [DEFAULT, DEVEL]

    # This is a script that executes the Java interpreter, it has no slave, so it must be documented and also does not
    # appear in IBM7 64 bit power archs and in x86_64 arch
    def check_java_cgi(self, args=None):
        self._document(
            "{} must be present in {} binaries. It has no slave in alternatives.".format(JAVA_RMI_CGI, DEVEL))
        # java-rmi.cgi binary check
        for subpackage in self._get_sdk_subpackage():
            try:
                self.installed_binaries[subpackage].remove(JAVA_RMI_CGI)
                passed_or_failed(self, True, "")
            except (ValueError, KeyError):
                passed_or_failed(self, False, "Missing {} in {}.".format(JAVA_RMI_CGI, DEVEL))
        return self.installed_binaries

    def _get_32bit_id_in_nvra(self, nvra):
        parts = nvra.split(".")
        parts[-1] = get_id(parts[-1])
        nvra = ".".join(parts)
        return nvra


class PathTest(BaseTest):
    def path_test(self, args=None):
        self._document("All binaries must be on $PATH. If present on multiple paths, the alternatives "
                       "links must be equal.")
        path_contents = {}
        pkgs = self.binaries_test.getBuild()
        for pkg in pkgs:
            name = os.path.basename(pkg)
            _subpkg = rename_default_subpkg(pkgsplit.get_subpackage_only(name))
            if _subpkg in subpackages_without_alternatives() + get_javadoc_dirs():
                self.binaries_test.log("Skipping path test for " + _subpkg)
                continue
            if not DefaultMock().run_all_scriptlets_for_install(pkg):
                self.binaries_test.log("Skipping path test because of missing post install scriptlet.")
                continue
            if (_subpkg == DEFAULT or _subpkg in [DEFAULT + suffix for suffix in get_debug_suffixes()])\
                    and int(pkgsplit.simplify_full_version(pkgsplit.get_minor_ver(name))) >= 10:
                self.binaries_test.log("Skipping default package, it has no binaries.")
                continue
            if _subpkg == PLUGIN and pkgsplit.get_vendor(name) == "ibm" and \
                     int(pkgsplit.simplify_version(pkgsplit.get_major_ver(name))) == 8 and pkgsplit.get_dist(name) == "el8":
                self.binaries_test.log("Skipping plugin package, it has no binaries.")
                continue

            paths = self._get_paths()
            self.binaries_test.log("Given paths: " + ", ".join(paths), vc.Verbosity.TEST)

            for path in paths:
                content = self._get_path_contents(path)
                if content[1] != 0:
                    content = []
                else:
                    content = content[0].split()
                path_contents[path] = content

            self.binaries_test.log("Validating binaries paths for {} subpackage: ".format(_subpkg), vc.Verbosity.TEST)
            if _subpkg in self.installed_binaries:
                for binary in self.installed_binaries[_subpkg]:
                    found_paths = self._binary_in_path_contents(path_contents, binary)
                    if passed_or_failed(self, found_paths is not None, binary + " not found in any path given for " + _subpkg):
                        self.binaries_test.log("Binary {} found in {} for "
                                               "{}".format(binary, ", ".join(found_paths), _subpkg), vc.Verbosity.TEST)

        self.binaries_test.log("Path test finished.", vc.Verbosity.TEST)
        return

    def _get_paths(self):
        paths = DefaultMock().executeCommand(['printenv PATH'])
        if paths[1] != 0:
            raise MockExecutionException("Command echo $PATH failed.")
        paths = paths[0].split(os.pathsep)
        return paths

    def _get_path_contents(self, path):
        content = DefaultMock().execute_ls(path)
        return content

    def _binary_in_path_contents(self, path_contents, binary):
        paths = set()
        for path in path_contents.keys():
            if binary in path_contents[path]:
                paths.add(path)
        if len(paths) == 0:
            return None
        result = set()
        for p in paths:
            tg = "readlink " + p + "/" + binary
            res = DefaultMock().executeCommand([tg])
            if passed_or_failed(self, res[1] == 0, "Command readlink " + p + "/" + binary + " failed."):
                result.add(res)
        if len(result) != 1:
            if len(result) > 1:
                passed_or_failed(self, False, "Links of one binary do not point on same target: " + ",".join(result))
            else:
                passed_or_failed(self, False, "Links do not point on any target.")
        return paths

