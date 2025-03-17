# Intro

Generally speaking, the main purpose of JSF is staticaly analyse openjdk RPMS and check whether those match expected state. Majority of the rules is hardcoded in the relevant python scripts.
The framework is capable of testing multiple architectures during a single run by iterating every run the same number of times as the number of architectures provided in the rpm set.
# Initial setup

**Step 1.** - Get your favorite Python IDE, I personally develop in Pycharm community edition.

**Step 2.** - Fork this repository and clone it.

```
git clone https://github.com/your_username/JSF.git
```

**Step 3.** - Download rpms. The test looks for the rpms in the *JSF/rpms/* directory.
- rpms are usually downloaded directly from
            -  koji-like systems. Eg: https://koji.fedoraproject.org/koji/packageinfo?packageID=28488
            - bodhi like udpates. eg: https://bodhi.fedoraproject.org/updates/FEDORA-2021-8dab50bea8
            Those two examples always end in build, like eg: https://koji.fedoraproject.org/koji/buildinfo?buildID=1724813
          Also:
           rpm based systems allow to download-only through package manager like dnf or yum
           or eg Fedora have fedpkg, which can download the task or build by its number (see the BuildID above)

**Step 4.** - Run tests. Tests are runnable both via the main method as well as via running their own respective main as "standalone" python script. The framework will most probably need dependencies (namely koji and mock for starters) installed and will fail during the first run.

For arguments and additional wisdom, feel free to check the old [readme](https://github.com/andrlos/JSF/blob/master/readme-old).

# Getting started:

To get familiar with the framework try to run subpackages run on a complete set of rpms. You can download the complete set by running main function with parameter
```
-b java_version
```
where instead of `java_version` you put any name of package set available on [koji.fedoraproject.com](koji.fedoraproject.com).
Sadly the --download-only parameter has not been yet implemented, so you either have to kill it after the download is finished (you can track the progress in *verbose_log_file.log*)or let the whole suite finish (won't take longer that 2 hours if you don't have the mock package installed yet).

# Writing your own tests:
here is an example structure of a generic test:
```
import sys
import utils.core.base_xtest
from outputControl import logging_access as la
from utils.core.configuration_specific import JdkConfiguration

# classes inheriting from JdkConfiguration are for handling the special  cases of arch/vendor/version of jdk
# all except the main testing methods from the CSCH class should start with an underscore ("_"), to ensure that they are not called by the main document launcher 
class DocumentingTestKiller(JdkConfiguration):

    def intrudeTest(self, checker=None):
        self._document("if killTest is true,  then the test fail whatever you do.")
        assert checker == False

class DummyCsch(JdkConfiguration):

    def intrudeTest(self, checker=None):
        # do not forget to document your test properly, ideally without unnecessary calculations that are not gonna be documented.
        # resultant documentation basically tells what is expected from the current set of rpms
        self._document("If the killTest is false, then this test actually test whether  tested is True.")
        assert checker is not None

# test class should always inherit from the BaseTest or any of its childs. However methods from individual CSCHs may be used within testing.
class TestTest(testcases.utils.core.base_xtest.BaseTest):

    tested = True
    killTest = True

# individual checks may be written inside particular CSCHs, if the behaviour differs
    def test_checkTrue(self):
        self.csch.intrudeTest(TestTest.tested)
        assert TestTest.tested == True

# setCSCH method decides which of the CSCHs is gonna be used within testing
    def setCSCH(self):
        if TestTest.killTest == True:
            self.csch = DocumentingTestKiller()
        else:
            self.csch = DummyCsch()

    def getTestedArchs(self):
        return None



def testAll():
    return TestTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Crazy test")
    return TestTest().execute_special_docs()

# following two functions enable us to test this set of testcases separately from the others - great for debugging, 
# however user workspace MUST be set to the base folder of the suite
def main(argv):
    testcases.utils.core.base_xtest.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
```

# Documenting
This testsuite aims to dynamically document what is expected by the test from the tested rpm set. Therefore when handling quirks and differences of individual versions, one must document every exclude and special case in the test.
The resultant documentation is written into jsf.log upon launching the testsuite with "--docs" argument.
# Result logging in JSF
There are several different types of log files being produced by the framework. There is *jsf.log*, with basic info about passed and failed tests, there is *verbose_log_file.log*, logging detailed information about the run of the framework. Then there are jtreg logs.
Jtreg logs are xml files located in *jtregLogs*. These files are then processed by *JCK report publisher* plugin in Jenkins. The processed output of the plugin looks as follows:
[JCK example](readme-images/JCK-plugin-example.png). These reports are the easiest way of checking the test results of JSF for the java-qa team, that uses this framework to validate the newest openjdk packages.

The report is generated upon calling of the function `passed_or_failed()` from *test_utils* file. This function substitutes assert function that are usually used in test writing, as it checks boolean passed to 
it as argument and handles all the logging to both *jsf.log* and jtreg xml logfiles. All other classes and methods important for jtreg logging are located in the *outputControl* package. For reference on how to 
use the method see arbitrary test from *testcases*.

# Mock

**Purpose**

"In object-oriented programming, mock objects are simulated objects that mimic the behavior of real objects in controlled ways." - [Wikipedia](https://en.wikipedia.org/wiki/Mock_object) \
In our case, the mock object are used to simulate whole systems. Fedora in particular. Mocked system may be configured in *utils/mock/mock_executor.py*. \
So how does it work? Before the testcase a clean mock of the specified system is launched. The problem is, that we only simulate fedora systems, so in order to test RHEL rpms, we usually have to manually unpack the tested rpms and launch a postscript over them. This should in theory result in a similar behaviour as a regular installation would be. \
It often happens, that a new tester kills the test on local before finishing and interrupts the mock execution. This means that mock wont have time to clean the system of current mocks. The presence of the leftover mocks blocks other execution with the same mock version with error message *Build chroot is locked, please restart the testSuite*. \
The solvation of this problem is rather easy. You only need to execute command ```mock --orphanskill``` followed by ```mock --scrub=all```. This usually solves the problem. \
The last resort in the special cases is to delete the */var/lib/MOCK_OVERLAYFS* folder.

**Configuration**

Before running the JSF for the first time on the new system, we have to first configure mock plugins to work correctly. By default the mock uses *lvm* plugin for snapshotting, but as this proved to be very hard to configure and use eventually, we switched to using *overlayfs* plugin. 
To configure mock to use this plugin it is required to create a new directory somewhere accesible for all users using mock and edit the */etc/mock/site-defaults.cfg* file with adding following three lines into the config file:
```
config_opts['plugin_conf']['overlayfs_enable'] = True
config_opts['plugin_conf']['root_cache_enable'] = False
config_opts['plugin_conf']['overlayfs_opts']['base_dir'] = "/path/to/your/folder"
```
We can test its behaviour by running mock and trying to get a snapshot eg: 
```
$ mock --install maven-local
$ mock --snapshot mvn
```
if there are no problems getting the mvn snapshot, you have succesfully configured mock. Mock can be cleaned of all snapshots by running:
```
$ mock --scrub overlayfs
```
To learn more about mock and the overlayfs plugin read [documentation](https://rpm-software-management.github.io/mock/).
