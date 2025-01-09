import ntpath
import os
import re
from traceback import extract_tb

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

    def __init__(self, os="fedora", version="rawhide", arch="x86_64", command="podman"):
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
        self.current_snapshot = None
        self.temp_name = "temp_name"
        self.containerRpmsLocation = "/rpms"
        la.LoggingAccess().log("Providing new instance of " + self.getMockName(),
                                                         vc.Verbosity.MOCK)
        # comment this, set inited and alternatives to true if debug of some test needs to be done in hurry, it is
        # sometimes acting strange though, so I do not recommend it (overlayfs plugin is quite fast so take the time
        # self._scrubLvmCommand()
        # self.init()

    def getMockName(self):
        return self.os + ":" + self.version

    def mainCommand(self):
        return [self.command, "build", "-t"]

    def init(self):
        pass

    def listSnapshots(self):
        o = exxec.processAsStrings([self.command, "images"])
        items = []
        for item in o[1:len(o)]:
            #sis = item.split("\s")
            i = item.split()[2]
            items.append(i)
        return self.current_snapshot, items

    def importRpm(self, rpmPath, resetBuildRoot=True):
        containerName = ntpath.basename(rpmPath)
        if resetBuildRoot:
            self.provideCleanUsefullRoot()
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + [containerName,"-f","utils/mock/dockerfiles/Copyin", ".", "-e", "BASE_IMAGE=" + self.current_snapshot, "FILE=" + rpmPath, "DEST=" + self.containerRpmsLocation])
        if r != 0:
            la.LoggingAccess().log("Importing rpmfile " + rpmPath + " to the container name " + self.current_snapshot + " failed with exit code " + str(r) + ".")
            la.LoggingAccess().log("Error message given was: " + e)
        self.current_snapshot=containerName


    def executeCommand(self, cmds):
        o, e, r = exxec.processToStringsWithResult([self.command, "run", "--rm", "-it", self.current_snapshot] + cmds)
        la.LoggingAccess().log(e, vc.Verbosity.MOCK)
        return o, r

    #def executeScriptlet(self, executor, file, params, suffix):
    #    pass

    def provideCleanUsefullRoot(self):
        initName = "init"
        if self.inited:
            self.current_snapshot=initName
        else:
            o, e, r = exxec.processToStringsWithResult(self.mainCommand() + [initName, "-f","utils/mock/dockerfiles/Init", "."])
            if r != 0:
                la.LoggingAccess().log("Container creation failed with exit code: " + str(r) + " and error message: " + e + ".")
            self.inited = True
            self.current_snapshot = initName

    def executeScriptlet(self, rpmFile, scriptletName, extraFlag=""):
        executor, scriptletFile = self.saveScriptlet(rpmFile, scriptletName)
        containerName = self.current_snapshot + "_" + scriptletName + (("_" + extraFlag) if extraFlag != "" else "")
        o, e, r = exxec.processToStringsWithResult(
            self.mainCommand() + [containerName, "--build-arg EXECUTOR=" + executor, "--build-arg FILE=" + scriptletFile, "."])
        if r != 0:
            la.LoggingAccess().log("Container creation failed with exit code: " + str(r) + " and error message: " + e + ".")

    def saveScriptlet(self, rpmFile, scriptletName, params=""):
        executor, lines = rpmuts.getSrciplet(rpmFile, scriptletName)
        scriptletSuffix = "_" + scriptletName + "_" + ntpath.basename(rpmFile)
        scritletFile = tu.saveStringsAsTmpFile(lines, scriptletSuffix)
        return executor, scritletFile

    def getSnapshot(self, name):
        self.current_snapshot=name

    def run_all_scriptlets_for_install(self, pkg):
        key = (ntpath.basename(pkg) + "_" + utils.rpmbuild_utils.ScripletStarterFinisher.installScriptlets[-1] + "_" + "a")
        if key in self.snapshots:
            la.LoggingAccess().log(pkg + " already installed in snapshot. Rolling to " + key,
                                   vc.Verbosity.MOCK)
            self.getSnapshot(key)
            return
        self.importRpm(pkg)
        for script in utils.rpmbuild_utils.ScripletStarterFinisher.installScriptlets:
            la.LoggingAccess().log("        " + "running " + script + " from " +
                                   os.path.basename(pkg),
                                   vc.Verbosity.TEST)
            try:
                self.executeScriptlet(pkg, script, "a")
            except utils.mock.mock_execution_exception.MockExecutionException:
                la.LoggingAccess().log("        " + script + " script not found in " +
                                       os.path.basename(pkg),
                                       vc.Verbosity.TEST)
        return True

    def execute_ls(self, dir):
        return self.executeCommand(["ls", dir])

    def get_masters(self):
        otp, r = self.execute_ls(ALTERNATIVES_DIR)
        masters = otp.split("\n")
        return masters


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
            data[PRIORITY] = otp[2].split(" ")[-1]
        except Exception:
            raise utils.mock.mock_execution_exception.MockExecutionException("alternatives output reading encountered "
                                                                             "an error: " + output)
        if not data[PRIORITY].isdigit():
            raise ValueError("Priority must be digit-only.")
        data[STATUS] = otp[0].split(" ")[-1].strip(".")
        if FAMILY in otp[2]:
            data[FAMILY] = otp[2].split(" ")[3]
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
