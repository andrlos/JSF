import ntpath
import os
import re

import utils.mock.rpm_uncpio_cache
import utils.process_utils as exxec
import utils.rpmbuild_utils as rpmuts
import utils.test_utils as tu
import utils.mock.mock_execution_exception
import utils.pkg_name_split
import config.runtime_config as rc
import config.global_config as gc
import outputControl.logging_access as la
import config.verbosity_config as vc

PRIORITY = "priority"
STATUS = "status"
FAMILY = "family"
TARGET = "target_link"
SLAVES = "slaves"
ALTERNATIVES_DIR = "/var/lib/alternatives"


class Mock:
    caredTopDirs = [
        "/bin",
        "/boot",
        "/builddir",
        "/dev",
        "/etc",
        "/home",
        "/lib",
        "/lib64",
        "/media",
        "/opt",
        "/root",
        "/run",
        "/sbin",
        "/tmp",
        "/usr"
        #            ,"/var"
    ]

    def __init__(self, os="fedora", version="37", arch="x86_64", command="mock"):
        """
        This is a base constructor for DefaultMock. Arguments should never be changed when initiating new instance,
        unless you need it for some valid reasons (so far, there are NONE).
        Version of mock must be currently < 27 (26 is obsoleted though). This is necessary due to rich dependencies in
        fedora 28 packages, that do not work on RHEL 7 VM's. As soon as we got good RHEL 8 images, we must switch back
        to rawhide and run this framework there, so we do not have to switch chroot every year or so.
        """
        self.os = os
        self.version = version
        self.arch = arch
        self.command = command
        self.inited = False
        self.alternatives = False
        self.snapshots = dict()
        la.LoggingAccess().log("Providing new instance of " + self.getMockName(),
                                                         vc.Verbosity.MOCK)
        # comment this, set inited and alternatives to true if debug of some test needs to be done in hurry, it is
        # sometimes acting strange though, so I do not recommend it (overlayfs plugin is quite fast so take the time
        self._scrubLvmCommand()
        # self.init()

    def getMockName(self):
        return self.os + "-" + self.version + "-" + self.arch

    def getConfigFile(self):
        return "/etc/mock/" + self.getMockName() + ".cfg"

    def getDir(self):
        return "/var/lib/mock/" + self.getMockName()

    def getRootDir(self):
        return self.getDir() + "/root"

    def getResultDir(self):
        return self.getDir() + "/result"

    def mainCommand(self):
        return [self.command, "--isolation=simple", "-r", self.getMockName()]

    def mainCommandAsString(self):
        s = ""
        for x in self.mainCommand():
            s=s+" " + x
        return s

    def init(self):
        if self.inited:
            self.reinit()
        else:
            self._init()

    def _init(self):
        o, e = exxec.processToStrings(self.mainCommand() + ["--init"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        self.inited = True

    def reinit(self):
        self._rollbackCommand("postinit")
        current, items = self.listSnapshots()
        for i in items:
            self.snapshots[i] = ""
        self.snapshots[current] = ""


    def listSnapshots(self):
        o = exxec.processAsStrings(self.mainCommand() + ["--list-snapshots"])
        current = None
        items = []
        for item in o[1:len(o)]:
            i = re.sub("^.\s+","", item)
            if item.startswith("*"):
                current = i
            items.append(i)
        return current, items

    def _snapsotCommand(self, name):
        o, e = exxec.processToStrings(self.mainCommand() + ["--snapshot", name])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        la.LoggingAccess().log(o, vc.Verbosity.MOCK)
        la.LoggingAccess().log(str(self.listSnapshots()), vc.Verbosity.MOCK)

    def _rollbackCommand(self, name):
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + ["--rollback-to", name])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        la.LoggingAccess().log(o, vc.Verbosity.MOCK)
        la.LoggingAccess().log(str(self.listSnapshots()), vc.Verbosity.MOCK)
        return e, o, r

    def _scrubLvmCommand(self):
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + ["--scrub", "all"])
        if r != 0:
            failed = "Build chroot is locked, please restart the testsuite."
            tu.passed_or_failed(self, False, failed)
            raise utils.mock.mock_execution_exception.MockExecutionException(failed)
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        la.LoggingAccess().log(o, vc.Verbosity.MOCK)
        la.LoggingAccess().log(str(self.listSnapshots()), vc.Verbosity.MOCK)

    def installAlternatives(self):
        if self.alternatives:
            self.getSnapshot("alternatives")
        else:
            self._installAlternatives()

    def _installAlternatives(self):
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "lua"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "lua-posix"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "copy-jdk-configs"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "chkconfig"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "man"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "symlinks"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        o, e = exxec.processToStrings(self.mainCommand() + ["--install", "tzdata-java"])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        self.createSnapshot("alternatives")
        self.alternatives = True

    def mktemp(self, suffix="me"):
        o, e = exxec.processToStrings(self.mainCommand() + ["--chroot", "mktemp --suffix " + suffix])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        return o

    def importFileContnet(self, suffix, content):
        src = tu.saveStringsAsTmpFile(content, suffix)
        dest = self.mktemp(suffix)
        self.copyIn([src], dest)
        return dest

    def copyIn(self, src, dest):
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + ["--copyin"] + src + [dest])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        return o, e, r

    def copyIns(self, cwd, srcs, dest):
        # unlike copyIn, this copy list of files TO destination. Because of necessary relativity of srcs,
        # CWD is included
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + ["--copyin"] + srcs + [dest], True, cwd)
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        return o, e, r

    def importRpm(self, rpmPath, resetBuildRoot=True):
        # there is restriciton to chars and length in/of vg name
        key= re.sub('[^0-9a-zA-Z]+', '_', ntpath.basename(rpmPath))
        if key in self.snapshots:
            la.LoggingAccess().log(rpmPath + " already extracted in snapshot. "
                                                                       "Rolling to " + key, vc.Verbosity.MOCK)
            return self.getSnapshot(key)
        else:
            la.LoggingAccess().log(rpmPath + " not extracted in snapshot. Creating " + key,
                                                             vc.Verbosity.MOCK)
            out, serr, res = self.importRpmCommand(rpmPath, resetBuildRoot)
            self.createSnapshot(key)
            self.snapshots[key] = rpmPath
            return out, serr, res

    def importRpmCommand(self, rpmPath, resetBuildRoot=True):
        """ Using various copy-in  variants have perofroamnce or existence issues at all """
        if resetBuildRoot:
            DefaultMock().provideCleanUsefullRoot()
        out, serr, res = utils.process_utils.executeShell("rpm2cpio " + rpmPath + " | " + self.mainCommandAsString() +
                                                          " --shell \"cd / && cpio -idmv\"")
        return out, serr, res

    def mkdirP(self, dirName):
        return self.executeCommand(["mkdir -p " + dirName])

    def mkdirsP(self, dirNames):
        all=""
        for  dir in dirNames:
            all=all+" "+dir
        return self.executeCommand(["mkdir -p " + all])

    def executeCommand(self, cmds):
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + ["--chroot"] + cmds)
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        return o, r

    def executeShell(self, scriptFilePath, params=""):
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + ["--chroot", "sh", scriptFilePath, params])
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        return o, r

    def listFiles(self):
        o = exxec.processAsStrings(self.mainCommand() + ["--chroot", "find"] + Mock.caredTopDirs, log=False)
        return o

    def createAndExecuteScriptlet(self, executor, scriptSuffix, lines, params=""):
        script = self.importFileContnet(scriptSuffix, lines)
        o, r = self.executeCommand([executor, script, params])
        return o, r

    def provideCleanUsefullRoot(self):
        if self.alternatives:
            self.installAlternatives()
        else:
            self.init()
            self.installAlternatives()
            if rc.RuntimeConfig().getRpmList().getVendor() in (gc.ORACLE + gc.SUN + gc.IBM + gc.ITW):
                # ibm/itw/oracle plugin packages expect mozilla installed in the filesystem, this gives us
                # directories neccessary
                self.mkdirP("/usr/lib64/mozilla")
                self.mkdirP("/usr/lib64/mozilla/plugins")
                self.mkdirP("/usr/lib/mozilla")
                self.mkdirP("/usr/lib/mozilla/plugins")
                if rc.RuntimeConfig().getRpmList().getVendor() == gc.ORACLE:
                    # oracle plugin packages in addition expect also these directories
                    self.mkdirP("/usr/lib/jvm/jce-1.7.0-oracle")
                    self.mkdirP("/usr/lib/jvm/jce-1.8.0-oracle")

    def executeScriptlet(self, rpmFile, scripletName, params=""):
        executor, scriplet = rpmuts.getSrciplet(rpmFile, scripletName)
        if scriplet is None or len(scriplet) == 0:
            raise Exception("Scriptlet " + scripletName + " is not in " + rpmFile)
        return self.createAndExecuteScriptlet(executor, "_" + scripletName + "_" + ntpath.basename(rpmFile), scriplet, params)

    def _getAbsFiles(self, files):
        absDirs = []
        for f in files:
            absDirs.append(self.getRootDir() + "/" + f)
        return absDirs

    def createSnapshot(self, name):
        self._snapsotCommand(name)

    def getSnapshot(self, name):
        return self._rollbackCommand(name)

    def run_all_scriptlets_for_install(self, pkg):
        key = re.sub('[^0-9a-zA-Z]+', '_', ntpath.basename(pkg) + "_" + "all_installed")
        if key in self.snapshots:
            la.LoggingAccess().log(pkg + " already installed in snapshot. Rolling to " + key,
                                                             vc.Verbosity.MOCK)
            self.getSnapshot(key)
            return
        self.importRpm(pkg)
        for script in utils.rpmbuild_utils.ScripletStarterFinisher.installScriptlets:
            la.LoggingAccess().log("        " + "running " +  script + " from " +
                                   os.path.basename(pkg),
                                   vc.Verbosity.TEST)
            try:
                self._only_run_scriptlet(pkg, script, "1")
            except utils.mock.mock_execution_exception.MockExecutionException:
                la.LoggingAccess().log("        " + script + " script not found in " +
                                       os.path.basename(pkg),
                                       vc.Verbosity.TEST)
        self.createSnapshot(key)
        return True

    def install_postscript(self, pkg):
        return self._effective_install_scriptlet(pkg, utils.rpmbuild_utils.POSTINSTALL)

    def _effective_install_scriptlet(self, pkg, scriptlet):
        key = re.sub('[^0-9a-zA-Z]+', '_', ntpath.basename(pkg) + "_" + scriptlet)
        if key in self.snapshots:
            la.LoggingAccess().log(pkg + " already extracted in snapshot. Rolling to " + key,
                                                             vc.Verbosity.MOCK)
            self.getSnapshot(key)
            return
        else:
            self.importRpm(pkg, False)
            try:
                self._only_run_scriptlet(pkg, scriptlet)
                self.createSnapshot(key)
            except utils.mock.mock_execution_exception.MockExecutionException:
                la.LoggingAccess().log("        " + scriptlet + " script not found in " +
                                       os.path.basename(pkg),
                                       vc.Verbosity.TEST)

    def _only_run_scriptlet(self, pkg, scriptlet, params):
        executor, content = utils.rpmbuild_utils.getSrciplet(pkg, scriptlet)
        if len(content) == 0:
            raise utils.mock.mock_execution_exception.MockExecutionException(scriptlet + " scriptlet not found in given"
                                                                                         " package.")
        else:
            o, r = self.executeScriptlet(pkg, scriptlet, params)
            la.LoggingAccess().log(scriptlet + "returned " +
                                   str(r) + " of " + os.path.basename(pkg), vc.Verbosity.MOCK)

    def execute_ls(self, dir):
        return self.executeCommand(["ls " + dir])

    def execute_ls_for_alternatives(self):
        return self.execute_ls(ALTERNATIVES_DIR)

    def get_masters(self):
        otp, r = self.execute_ls_for_alternatives()
        masters = otp.split("\n")
        return masters

    def display_alternatives(self, master):
        output, r = self.executeCommand(["alternatives --display " + master])
        return output

    def parse_alternatives_display(self, master):
        """
        Alternatives --display master provide us with a lot of information, that are parsed here. Use the getters
        below every time you need something.
        """

        output = self.display_alternatives(master)
        if len(output.strip()) == 0:
            la.LoggingAccess().log("alternatives --display master output is empty",
                                                             vc.Verbosity.MOCK)
            raise utils.mock.mock_execution_exception.MockExecutionException("alternatives --display master "
                                                                             "output is empty ")
        data = {}
        otp = output.splitlines()
        try:
            data[PRIORITY]= otp[2].split(" ")[-1]
        except Exception:
            raise utils.mock.mock_execution_exception.MockExecutionException("alternatives output reading encountered "
                                                                             "an error: " + output)
        if not data[PRIORITY].isdigit():
            raise ValueError("Priority must be digit-only.")
        data[STATUS] = otp[0].split(" ")[-1].strip(".")
        if FAMILY in otp[2]:
            data[FAMILY]= otp[2].split(" ")[3]
        else:
            data[FAMILY] = None
        data[TARGET] = otp[2].split(" ")[0]
        slaves = {}
        for o in otp:
            if "follower" in o:
                slaves[o.split(" ")[2].strip(":")] = o.split(" ")[3]
        data[SLAVES] = slaves
        return data

    def get_priority(self, master):
        return self.parse_alternatives_display(master)[PRIORITY]

    def get_status(self, master):
        return self.parse_alternatives_display(master)[STATUS]

    def get_family(self, master):
        return self.parse_alternatives_display(master)[FAMILY]

    def get_target(self, master):
        return self.parse_alternatives_display(master)[TARGET]

    def get_slaves(self, master):
        return self.parse_alternatives_display(master)[SLAVES].keys()

    def get_slaves_with_links(self, master):
        return self.parse_alternatives_display(master)[SLAVES]

    def get_default_masters(self):
        self.provideCleanUsefullRoot()
        return self.get_masters()


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# Try to avoid making unnecessary instances of Mock()
# if possible, try to work with the DefaultMock and its snapshots
class DefaultMock(Mock, metaclass=Singleton):
    pass
