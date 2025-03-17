import abc

import utils.test_utils as tu
import outputControl.logging_access as la

import config.general_parser
import config.global_config
import config.runtime_config
import utils.core.base_test_runner as btr
import config.verbosity_config as vc


def defaultMain(argv, runDocs, runTests):
    args = config.general_parser.GeneralParser().parser.parse_args(argv)
    canContinue = config.runtime_config.RuntimeConfig().setFromParser(args)
    if canContinue:
        if config.runtime_config.RuntimeConfig().getDocs():
            passed, ignored, failed = runDocs()
            tu.closeDocSuite(passed, ignored, failed)
        else:
            passed, failed, perMethod = runTests()
            tu.closeTestSuite(passed, failed, perMethod)


class BaseTest(btr.BaseTestRunner):
    def __init__(self):
        super().__init__()
        self.failed = 0
        self.passed = 0

    def getBuild(self):
        return config.runtime_config.RuntimeConfig().getRpmList().getBuildWithoutSrpm(self.current_arch)

    def getCurrentArch(self):
        return self.current_arch

    @abc.abstractmethod
    def setCSCH(self):
        """Set csch as overwriting test wishes"""
        self.log("Nothing to set.", vc.Verbosity.TEST)

    @abc.abstractmethod
    def getTestedArchs(self):
        """returns array of architectures to run tests/docs on
        Usually native arches as most of the tests are run on
        getBuildWithoutSrpm or getCompleteBuild
        overwrite and return empty array or None if the test is arch-independent"""
        self.log("run on all known arches", vc.Verbosity.TEST)
        return config.runtime_config.RuntimeConfig().getRpmList().getNativeArches()
