import re

import config.global_config as gc
import outputControl.logging_access as la
from utils.core.configuration_specific import JdkConfiguration
import utils.test_utils as tu
import config.runtime_config as rc


class DefaultCheck(JdkConfiguration):
    def checkMajorVersionSimplified(self, version=None):
        pass

    def checkMajorVersion(self, version=None):
        pass

    def checkPrefix(self, version=None):
        pass

    def checkVendor(self, vendor=None):
        pass

    def checkOs(self, vendor=None):
        l = rc.RuntimeConfig().getRpmList()
        la.LoggingAccess().log("Os: " + l.getOs())
        la.LoggingAccess().log("Version: " + l.getOsVersion())
        la.LoggingAccess().log("Version major: " + str(l.getOsVersionMajor()))
        tu.passed_or_failed(self, l.isFedora() | l.isRhel(), "Pkgs are not rhel, neither fedora")
        tu.passed_or_failed(self, l.isFedora() != l.isRhel(), "Both Rhel and fedora pkgs are present")
        tu.passed_or_failed(self, l.getOs() is not None, "Os was equal to None")
        tu.passed_or_failed(self, l.getOsVersion() is not None, "OsVersion was equal to None")
        tu.passed_or_failed(self, l.getOsVersionMajor() is not None, "OsVersionMajor was equal to None")
        return self.passed, self.failed


class ItwVersionCheck(DefaultCheck):

    def checkMajorVersionSimplified(self, version=None):
        self._document("IcedTea-Web do not have any version contained in name.")
        la.LoggingAccess().log("ITW special call for checkMajorVersionSimplified")
        return version == gc.ITW

    def checkMajorVersion(self, version=None):
        self.checkMajorVersionSimplified(version)

    def checkPrefix(self, version=None):
        self._document("IcedTea-Web do not have any prefix-based name. It is just " + gc.ITW + ".")
        la.LoggingAccess().log("ITW special call for checkPrefix")
        return version == gc.ITW

    def checkVendor(self, vendor=None):
        self._document("IcedTea-Web do not have any vendor in name. It is just " + gc.ITW + ".")
        la.LoggingAccess().log("ITW special call for checkVendor")
        return vendor == gc.ITW


class OthersVersionCheck(DefaultCheck):

    def checkMajorVersionSimplified(self, version=None):
        self._document(
            "All jdsk (except icedtea-web) have major version in name. eg: java-1.8.0-openjdk or java-9-oracle."
            " For legacy JDK (like jdk 1.6.0 or 1.7.1) the major version is included as middle number."
            " For modern jdks (jdk 9+)  the major version is just plain number. Eg.: java-9-ibm."
            " The extracted middle number *is* number")
        la.LoggingAccess().log("non itw call for checkMajorVersionSimplified")
        return re.compile("[0-9]+").match(version) and int(version) > 0

    def checkMajorVersion(self, version=None):
        self._document("The version string in middle of package name is one of: " + ",".join(
            gc.LIST_OF_POSSIBLE_VERSIONS_WITHOUT_ITW))
        return version in gc.LIST_OF_POSSIBLE_VERSIONS_WITHOUT_ITW

    def checkPrefix(self, version=None):
        self._document("prefix of each java package is " + gc.JAVA_STRING + ".")
        la.LoggingAccess().log("non itw call for checkPrefix")
        return version == gc.JAVA_STRING

    def checkVendor(self, vendor=None):
        self._document("The vendor string, suffix of package name is one of: " + ",".join(
            gc.LIST_OF_POSSIBLE_VENDORS_WITHOUT_ITW))
        la.LoggingAccess().log("non itw call for checkVendor")
        return vendor in gc.LIST_OF_POSSIBLE_VENDORS_WITHOUT_ITW

class TemurinCheck(OthersVersionCheck):
    def checkOs(self):
        la.LoggingAccess().log("Temurin is not os or osversion specific, this test is being skipped.")
        return self.passed, self.failed
