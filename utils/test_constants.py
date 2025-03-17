PLUGIN = "plugin"
JAVA = "java"
JAVAC = "javac"
HEADLESS = "headless"
DEVEL = "devel"
DEFAULT = "default"
CONTROL_PANEL = "ControlPanel"
LIBJAVAPLUGIN = "libjavaplugin.so"
LIBNSSCKBI_SO = "libnssckbi.so"
JAVAFXPACKAGER = "javafxpackager"
POLICYTOOL = "policytool"
JAVAFX = "javafx"
JAVADOC = "javadoc"
JAVADOCZIP = "javadoc-zip"
MAN_DIR = "/usr/share/man/man1"
WAS_NOT_FOUND = "was not found"
JAVA_RMI_CGI = "java-rmi.cgi"
ICED_TEA_PLUGIN_SO = "IcedTeaPlugin.so"
JMC_INI = "jmc.ini"
JVM_DIR = "/usr/lib/jvm"
SDK_DIRECTORY = "/bin"
JRE_DIRECTORY = "/jre/bin"
JCONTROL = "jcontrol"
JAVAWS = "javaws"
ITWEB_SETTINGS = "itweb-settings"
USR_BIN = "/usr/bin"
JRE = "jre"
JDK= "jdk"
SDK = "java_sdk"
OJDK8 = "ojdk8"
OJDK8JFX = "ojdk8JFX"
OJDK8DEBUG = "ojdk8debug"
IGNOREDNAMEPARTS = ["playground."]
JITARCHES = ["aarch64", "i686", "ppc64le", "x86_64"]
KNOWN_DEBUG_SUFFIXES = ["-slowdebug-", "-fastdebug-", "-debug-"]


#unable to import singleton from global_config
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

def is_arch_jitarch(arch):
    return arch in JITARCHES

# exports jre binaries
def get_exports_slaves_jre():
    return ["jre_exports"]


# exports sdk binaries
def get_exports_slaves_sdk():
    return ["java_sdk_exports"]

def get_ibm_k_bins():
    return ["klist", "kinit", "ktab"]


def get_ibm_ikey_bins():
    return ["ikeycmd", "ikeyman"]


def get_ibm_folders():
    return ["classic", "j9vm", "java-rmi.cgi"]


def oracle_exclude_list():
    return [JMC_INI]


def get_ibm_exclude_list():
    return get_ibm_k_bins() + get_ibm_folders() + get_ibm_ikey_bins()


def get_plugin_binaries():
        return [JCONTROL, CONTROL_PANEL, JAVAWS]


def get_openjfx_binaries():
    return ["javapackager", "javafxpackager"]


def subpackages_without_alternatives():
    subpackages = ["debuginfo", "debug-debuginfo", "debugsource", "jdbc"]
    suffixes = get_debug_suffixes()
    debug_subpackages = ["accessibility", "src", "demo", "devel-debuginfo", "headless-debuginfo", "demo-debuginfo"]
    subpackages.extend(debug_subpackages)
    for suffix in suffixes:
        for subpkg in debug_subpackages:
            splitted = subpkg.split("-", 1)
            subpackages.append(splitted[0] + suffix + ("" if len(splitted) == 1 else "-" + splitted[1]))
    return subpackages


def get_javadoc_dirs():
    suffixes = get_debug_suffixes()
    dirs = [JAVADOC, JAVADOCZIP]
    for suffix in suffixes:
        for dir in dirs.copy():
            dirs.append(dir + suffix)
    return dirs


# following methods should serve as debug suffix identifier per architecture, just call get_debug_suffixes
# in order to get all suffixes for the current arch
def identify_debug_suffixes():
    import config.runtime_config as conf
    rpms = conf.RuntimeConfig().getRpmList()
    return rpms.getDebugSuffixes()


def get_debug_suffixes():
    import config.runtime_config as conf
    if not DebugSuffixHolder().debug_suffixes:
        DebugSuffixHolder().debug_suffixes = identify_debug_suffixes()
    return DebugSuffixHolder().debug_suffixes[conf.RuntimeConfig().current_arch]


class DebugSuffixHolder(metaclass=Singleton):
    def __init__(self):
        self.debug_suffixes = dict()


