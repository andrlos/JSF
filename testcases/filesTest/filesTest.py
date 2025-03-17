import sys
import utils.test_constants as tc
import outputControl.logging_access as la
import utils.core.configuration_specific as cs
import utils.test_utils as tu
import outputControl.dom_objects as do
import utils.core.base_xtest as bt
import config.runtime_config as rc
import utils.mock.mock_executor as me
import config.global_config as gc

OJDK11CHECKEDFILES = {tc.DEFAULT: ["/usr/lib/jvm/**NVRA**/lib/jspawnhelper"]}


# used to track existence of certain files in advancement of new java builds

class Default(cs.JdkConfiguration):
    def __init__(self, rpms):
        super().__init__()
        self.rpms = rpms
        self.file_list = []

    def _set_file_list(self):
        pass

    def test_file_list(self, current_arch):
        self._set_file_list()
        if self.documenting:
            self._document("Controlling existence of following files: " + str(self.file_list))
        return self.passed, self.failed

    def check_file_existence(self, file):
        out, res = me.DefaultMock().execute_ls(file)
        return res == 0


class Ojdk11AndAbove(Default):
    def _set_file_list(self):
        self.file_list = OJDK11CHECKEDFILES

    def test_file_list(self, current_arch):
        super().test_file_list(current_arch)
        for pkg in self.file_list.keys():
            for file in self.file_list[pkg]:
                pkg_name = self.rpms.getRpmWholeName(pkg, current_arch).replace(".rpm", "")
                tu.passed_or_failed(self, self.check_file_existence(file.replace("**NVRA**", pkg_name)),
                                    "requested file {} not found in specified pkg {}".format(file, ""))
        return self.passed, self.failed


class FileTest(bt.BaseTest):
    def setCSCH(self):
        rpms = rc.RuntimeConfig().getRpmList()
        rpms.getMajorPackage()
        if (rpms.getVendor() == gc.OPENJDK or rpms.getVendor() == gc.OPENJ9) and int(rpms.getMajorVersionSimplified()) >= 11:
            self.csch = Ojdk11AndAbove(rpms)
        else:
            self.csch = Default(rpms)

    def test_file_list(self):
        return self.csch.test_file_list(self.current_arch)


def testAll():
    return FileTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Files")
    return FileTest().execute_special_docs()


def main(argv):
    bt.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
