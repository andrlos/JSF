import sys

import utils.pkg_name_split as split
import utils.rpmbuild_utils as rpmuts
import utils.core.configuration_specific as cs
import config.runtime_config
import utils.core.base_xtest
import outputControl.logging_access as la
import utils.test_utils as tu


class Base(cs.JdkConfiguration):
    def __init__(self):
        super().__init__()


class ITW(Base):
    def _checkJreObsolete(self, obsoletes=None):
        self._document("Itw obsolete should be aligned to jres' plugins/javawss")
        # todo - do when doing other plugins
        return self.passed, self.failed


class Openjdk8Fedora(Base):

    jreRequiredObsolete=[
        "java-1.7.0-openjdk",
        "java-1.5.0-gcj",
        "sinjdoc"
    ]

    def _checkJreObsolete(self, obsoletes=None):
        self._document("jre OpenJdk8 in Fedora must obsolate: " +",".join(Openjdk8Fedora.jreRequiredObsolete))
        obsoleteJdk7Set = set(Openjdk8Fedora.jreRequiredObsolete).intersection(set(obsoletes))
        tu.passed_or_failed(self, len(obsoleteJdk7Set) == len(Openjdk8Fedora.jreRequiredObsolete),
                         "Number of obsoletes and obsoleteExceptions is not same.",
                         "this test is checking only count of obsoletes vs count of exceptions, needs rework")
        return self.passed, self.failed


class JdkRhel(Base):
    jreExceptionsObsolete = [
        "java-1.8.0-openjdk-accessibility",
        "java-1.8.0-openjdk-accessibility-fastdebug",
        "java-1.8.0-openjdk-accessibility-slowdebug"
    ]

    def _checkJreObsolete(self, obsoletes=None):
        self._document("Jdks in rhel must NOT obsolete anything. Possible exceptions: " +
                       ",".join(JdkRhel.jreExceptionsObsolete))
        tu.passed_or_failed(self, len(set(obsoletes)-set(JdkRhel.jreExceptionsObsolete)) == 0,
                         "Number of obsoletes and obsoleteExceptions is not same.",
                         "this test is checking only count of obsoletes vs count of exceptions, needs rework")
        return self.passed, self.failed


class ObsolateTest(utils.core.base_xtest.BaseTest):

    def test_jreobsolete(self):
        rpms = self.getBuild()
        for pkg in rpms:
            if split.get_subpackage_only(pkg) == '':
                return self.csch._checkJreObsolete(rpmuts.listOfVersionlessObsoletes(pkg))
        return 0, 0

    def setCSCH(self):
        if config.runtime_config.RuntimeConfig().getRpmList().isItw() :
            self.csch = ITW()
            return
        else:
            self.csch = JdkRhel()


def testAll():
    return ObsolateTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Jdk obsolates are rhel/fedora techpreview/released depndent.")
    return ObsolateTest().execute_special_docs()


def main(argv):
    utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
