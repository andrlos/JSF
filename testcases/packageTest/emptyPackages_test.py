import sys

import utils.pkg_name_split as split

import config.global_config
import config.runtime_config
import utils.core.base_xtest
import outputControl.logging_access as la
import utils.test_utils as tu
import utils.rpmbuild_utils as rpmbu


class EmptyPackageTest(utils.core.base_xtest.BaseTest):
    def __init__(self):
        super().__init__()

    def test_checkNoPacakgeEmpty(self):
        pkgs= config.runtime_config.RuntimeConfig().getRpmList().getAllFiles()
        for pkg in pkgs:
            self.log("checking: " + pkg)
            files = rpmbu.listFilesInPackage(pkg)
            self.log("got: " + str(len(files)) + " files")
            if split.get_arch(pkg) in config.global_config.getSrcrpmArch():
                tu.passed_or_failed(self, len(files) > 1, "Wrong number of files in package " + pkg +
                                 " should be more than 1.")
            # IBM8EL8 src and jdbc pkgs both contain single file
            elif split.get_vendor(pkg) == "ibm" and split.simplify_full_version(split.get_major_ver(pkg)) == "8" and ("src" in pkg or "jdbc" in pkg):
                tu.passed_or_failed(self, len(files) == 1, "Wrong number of files in package " + pkg + " should be 1.")
            else:
                tu.passed_or_failed(self, len(files) > 2, "Wrong number of files in package "
                                 + pkg + " should be more than 2.")
        return self.passed, self.failed

    def getTestedArchs(self):
        return None


def testAll():
    return EmptyPackageTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Currently all java packages must have at least three files (except srpm which is "
                              "enough with 2 and more)")
    return EmptyPackageTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])