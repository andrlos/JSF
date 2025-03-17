import outputControl.logging_access as la
import utils.rpmbuild_utils as rpmbuild_utils
import config.verbosity_config as vc
# The get_methods nor find_on_disc are order-granting. However they seems to be sorted...
# Sometimes. So this switch will ensure it.


leSort = True


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DynamicArches(metaclass=Singleton):
    """
    Some architectures have more than one variant (e.g. arm or ppc). Rpmbuild is aware, so --eval method is used for
    currently known troublemakers (power64, arm, ix86).
    """

    def __init__(self):
        self.arm32 = None
        self.ix86 = None
        self.power64 = None

    def getDynamicArches(self, arch):
        la.LoggingAccess().log("Getting dynamic arches for: " + arch, vc.Verbosity.MOCK)
        output= rpmbuild_utils.rpmbuildEval(arch)
        li = output.split(" ")
        for i in range(len(li)):
            li[i] = li[i].strip()
        return li

    def getArm32Achs(self):
        if (self.arm32 == None):
            self.arm32 = self.getDynamicArches("arm")
        return self.arm32

    def getIx86Archs(self):
        if (self.ix86 == None):
            self.ix86 = self.getDynamicArches("ix86")
        return self.ix86

    def getPower64Achs(self):
        if (self.power64 == None):
            self.power64 = self.getDynamicArches("power64")
        return self.power64

    def getPower64BeAchs(self):
        achs = []
        for arch in self.getPower64Achs():
            if not 'le' in arch:
                achs.append(arch)
        return achs

    def getPower64LeAchs(self):
        achs = []
        for arch in self.getPower64Achs():
            if 'le' in arch:
                achs.append(arch)
                return achs

def getArm32Achs():
    # return ["armv7hl"]
    return DynamicArches().getArm32Achs()


def getPower64LeAchs():
    # return ["ppc64le"]
    return DynamicArches().getPower64LeAchs()


def getPower64BeAchs():
    # return ["ppc64","ppc64p7"]
    return DynamicArches().getPower64BeAchs()


def getPower64Achs():
    # return ["ppc64","ppc64p7","ppc64le"]
    return DynamicArches().getPower64Achs()


def getIx86archs():
    # return ["i386", "i686"]
    return DynamicArches().getIx86Archs()


def getHardcodedArchs():
    return getX86_64Arch() + getPpc32Arch() + getS390Arch() + getS390xArch() + getAarch64Arch()


def getGeneratedArchs():
    return getIx86archs() + getPower64Achs() + getArm32Achs() + getPower64LeAchs()


def getArchs():
    return getHardcodedArchs() + getGeneratedArchs()


def getAllArchs():
    return getArchs() + getNoarch() + getSrcrpmArch()


def getNoarch():
    return ["noarch"]


def getSrcrpmArch():
    return ["src"]


def getX86_64Arch():
    return ["x86_64"]


def getPpc32Arch():
    return ["ppc"]


def getS390Arch():
    return ["s390"]


def getS390xArch():
    return ["s390x"]


def getAarch64Arch():
    return ["aarch64"]


def get_32b_arch_identifiers_in_scriptlets(arch):
    if arch in getArm32Achs():
        return ARM_32_IDENTIFIER
    elif arch in getIx86archs():
        return INTEL_IDENTIFIER
    else:
        return arch


ARM_32_IDENTIFIER = "arm"
INTEL_IDENTIFIER= "i386"

JAVA_STRING = "java"
UNSPECIFIED = "unspecified"
FEDORA = "Fedora"
RHEL = "RHEL"

OPENJ9 = "openj9"
OPENJDK = "openjdk"
ITW = "icedtea-web"
IBM = "ibm"
ORACLE = "oracle"
SUN = "sun"
ADOPTIUM = "Adoptium"
TEMURIN = "temurin"

LIST_OF_PROPRIETARY_VENDORS = [IBM, ORACLE]
LIST_OF_OPEN_VENDORS_EXCEPT_ITW = [OPENJDK, ADOPTIUM]
LIST_OF_OPEN_VENDORS = LIST_OF_OPEN_VENDORS_EXCEPT_ITW + [ITW]
LIST_OF_POSSIBLE_VENDORS = LIST_OF_PROPRIETARY_VENDORS + LIST_OF_OPEN_VENDORS
LIST_OF_POSSIBLE_VENDORS_WITHOUT_ITW = LIST_OF_PROPRIETARY_VENDORS + LIST_OF_OPEN_VENDORS_EXCEPT_ITW
LIST_OF_LEGACY_VERSIONS = ["1.7.0", "1.8.0"]
LIST_OF_NEW_VERSIONS = ["11", "17", "21", "latest"]
LIST_OF_POSSIBLE_VERSIONS = [ITW] + LIST_OF_LEGACY_VERSIONS + LIST_OF_NEW_VERSIONS
LIST_OF_POSSIBLE_VERSIONS_WITHOUT_ITW = LIST_OF_LEGACY_VERSIONS + LIST_OF_NEW_VERSIONS
