import ntpath
import os
import re
from traceback import extract_tb

import utils.podman.rpm_uncpio_cache
import utils.process_utils as exxec
import utils.rpmbuild_utils as rpmuts
import utils.test_utils as tu
import utils.podman.podman_execution_exception
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


class Podman:
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
        This is a base constructor for DefaultPodman. Arguments should never be changed when initiating new instance,
        unless you need it for some valid reasons (so far, there are NONE).
        Version of podman must be currently < 27 (26 is obsoleted though). This is necessary due to rich dependencies in
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
        self.scriptletTmpDir = "scriptletsLocalTMP"
        la.LoggingAccess().log("Providing new instance of " + self.getPodmanName(),
                                                         vc.Verbosity.PODMAN)
        self.init()
        # comment this, set inited and alternatives to true if debug of some test needs to be done in hurry, it is
        # sometimes acting strange though, so I do not recommend it (overlayfs plugin is quite fast so take the time
        # self._scrubLvmCommand()
        # self.init()

    def getPodmanName(self):
        return self.os + ":" + self.version

    def mainCommand(self):
        return [self.command, "build", "-t"]

    #method to clean up after previous execution..
    def init(self):
        exxec.executeShell("podman rmi --all")
        exxec.executeShell("podman image prune -f")
        exxec.executeShell("rm " + self.scriptletTmpDir + "/tmp*")

    def listSnapshots(self):
        o = exxec.processAsStrings([self.command, "images"])
        items = []
        for item in o[1:len(o)]:
            #sis = item.split("\s")
            i = item.split()[2]
            items.append(i)
        return self.current_snapshot, items

    def importRpm(self, rpmPath, resetBuildRoot=True):
        containerName = utils.pkg_name_split.get_package_name(ntpath.basename(rpmPath))
        if resetBuildRoot:
            self.provideCleanUsefullRoot()
        o, e, r = exxec.processToStringsWithResult(self.mainCommand() + [containerName,"-f","utils/podman/dockerfiles/Copyin", ".", "--build-arg", "BASE_IMAGE=" + self.current_snapshot, "--build-arg", "FILE=" + rpmPath, "--build-arg", "DEST=" + self.containerRpmsLocation])
        if r != 0:
            la.LoggingAccess().log("Importing rpmfile " + rpmPath + " to the container name " + self.current_snapshot + " failed with exit code " + str(r) + ".")
            la.LoggingAccess().log("Error message given was: " + e)
        self.current_snapshot=containerName
    def importAllRpms(self, rpmsDirectory, resetBuildRoot=True, snapshotName=None):
        """
        Import all RPM files from a directory into the current snapshot image.
        Creates a single Docker layer containing all extracted RPMs for efficiency.
        
        Args:
            rpmsDirectory (str): Path to directory containing RPM files (relative or absolute).
                                Example: "rpms17el8" or "/home/user/rpms"
            resetBuildRoot (bool): If True, resets to clean build root before importing.
                                  If False, imports on top of current snapshot. Default: True
            snapshotName (str): Optional custom name for the resulting snapshot.
                               If None, auto-generates: "all_rpms_<directory_name>"
        
        Returns:
            str: Name of the created snapshot image
        
        Raises:
            ValueError: If directory doesn't exist or contains no RPM files
            Exception: If podman build fails
        
        Example:
            >>> podman = DefaultPodman()
            >>> podman.importAllRpms("rpms17el8")
            'all_rpms_rpms17el8'
            >>> podman.executeCommand(["java", "-version"])
        """
        # Validate directory exists
        if not os.path.exists(rpmsDirectory):
            raise ValueError(f"Directory not found: {rpmsDirectory}")
        
        # Scan for RPM files
        rpm_files = [f for f in os.listdir(rpmsDirectory) if f.endswith('.rpm')]
        if not rpm_files:
            raise ValueError(f"No RPM files found in {rpmsDirectory}")
        
        la.LoggingAccess().log(f"Found {len(rpm_files)} RPM files in {rpmsDirectory}", 
                              vc.Verbosity.PODMAN)
        
        # Reset to clean build root if requested
        if resetBuildRoot:
            self.provideCleanUsefullRoot()
        
        # Generate snapshot name if not provided
        if snapshotName is None:
            dir_basename = os.path.basename(rpmsDirectory.rstrip('/'))
            snapshotName = f"all_rpms_{dir_basename}"
        
        # Build container with all RPMs using the ImportAllRpms dockerfile
        la.LoggingAccess().log(f"Building snapshot '{snapshotName}' with {len(rpm_files)} RPMs from {rpmsDirectory}", 
                              vc.Verbosity.PODMAN)
        
        o, e, r = exxec.processToStringsWithResult(
            self.mainCommand() + 
            [snapshotName, "-f", "utils/podman/dockerfiles/ImportAllRpms", ".", 
             "--build-arg", f"BASE_IMAGE={self.current_snapshot}",
             "--build-arg", f"RPMS_DIR={rpmsDirectory}"]
        )
        
        # Error handling
        if r != 0:
            la.LoggingAccess().log(
                f"Importing all RPMs from {rpmsDirectory} to snapshot '{snapshotName}' failed with exit code {r}",
                vc.Verbosity.ERROR
            )
            la.LoggingAccess().log(f"Error message: {e}", vc.Verbosity.ERROR)
            raise Exception(f"Failed to import RPMs from {rpmsDirectory}: {e}")
        
        # Update current snapshot
        self.current_snapshot = snapshotName
        la.LoggingAccess().log(
            f"Successfully imported {len(rpm_files)} RPMs into snapshot '{snapshotName}'",
            vc.Verbosity.PODMAN
        )
        
        return snapshotName
    # Containerized RPM utility methods - platform independent
    # These methods execute rpm commands inside the container instead of on the host
    
    def containerized_listFilesInPackage(self, rpmFile):
        """
        List files in an RPM package using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
        
        Returns:
            list: List of file paths in the package
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        output, returncode = self.executeCommand(["rpm", "-qlp", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to list files in {rpmFile}", vc.Verbosity.ERROR)
            return []
        return output.strip().split('\n') if output.strip() else []
    
    def containerized_listDocsInPackage(self, rpmFile):
        """
        List documentation files in an RPM package using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
        
        Returns:
            list: List of documentation file paths
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        output, returncode = self.executeCommand(["rpm", "-qldp", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to list docs in {rpmFile}", vc.Verbosity.ERROR)
            return []
        return output.strip().split('\n') if output.strip() else []
    
    def containerized_listConfigFilesInPackage(self, rpmFile):
        """
        List config files in an RPM package using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
        
        Returns:
            list: List of config file paths
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        output, returncode = self.executeCommand(["rpm", "-qlcp", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to list config files in {rpmFile}", vc.Verbosity.ERROR)
            return []
        return output.strip().split('\n') if output.strip() else []
    
    def containerized_listOfRequires(self, rpmFile):
        """
        List package requirements using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
        
        Returns:
            list: List of required packages
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        output, returncode = self.executeCommand(["rpm", "--requires", "-qp", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to list requires for {rpmFile}", vc.Verbosity.ERROR)
            return []
        return output.strip().split('\n') if output.strip() else []
    
    def containerized_listOfProvides(self, rpmFile):
        """
        List package provides using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
        
        Returns:
            list: List of provided packages/capabilities
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        output, returncode = self.executeCommand(["rpm", "--provides", "-qp", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to list provides for {rpmFile}", vc.Verbosity.ERROR)
            return []
        return output.strip().split('\n') if output.strip() else []
    
    def containerized_listOfObsoletes(self, rpmFile):
        """
        List package obsoletes using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
        
        Returns:
            list: List of obsoleted packages
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        output, returncode = self.executeCommand(["rpm", "--obsoletes", "-qp", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to list obsoletes for {rpmFile}", vc.Verbosity.ERROR)
            return []
        return output.strip().split('\n') if output.strip() else []
    
    def containerized_getSrciplet(self, rpmFile, scripletId):
        """
        Extract scriptlet from RPM using the container's rpm command.
        
        Args:
            rpmFile (str): Path to RPM file (should be in containerRpmsLocation)
            scripletId (str): Scriptlet identifier (e.g., 'postinstall', 'preinstall')
        
        Returns:
            tuple: (executor, script_lines) where executor is the interpreter (e.g., '/bin/sh', 'lua')
                   and script_lines is a list of script content lines
        """
        rpm_basename = ntpath.basename(rpmFile)
        rpm_path = f"{self.containerRpmsLocation}/{rpm_basename}"
        
        # Get all scripts from the RPM
        output, returncode = self.executeCommand(["rpm", "-qp", "--scripts", rpm_path])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to get scripts from {rpmFile}", vc.Verbosity.ERROR)
            return ("/bin/sh", [])
        
        # Parse the output to find the specific scriptlet
        lines = output.split('\n')
        script_lines = []
        in_scriptlet = False
        executor = "/bin/sh"
        
        for line in lines:
            # Check if this is the start of our scriptlet
            if scripletId + " scriptlet" in line:
                in_scriptlet = True
                # Extract executor if specified
                if "using" in line:
                    executor = line.split("using")[1].strip().strip("):<>").strip()
                continue
            
            # Check if we've hit another scriptlet (stop condition)
            if in_scriptlet and " scriptlet" in line:
                break
            
            # Collect script lines
            if in_scriptlet:
                script_lines.append(line)
        
        if not script_lines:
            la.LoggingAccess().log(f"Scriptlet {scripletId} not found in {rpmFile}", vc.Verbosity.PODMAN)
            return (executor, [])
        
        return (executor, script_lines)
    
    def containerized_rpmbuildEval(self, macro):
        """
        Evaluate an RPM macro using the container's rpmbuild command.
        
        Args:
            macro (str): Macro name to evaluate (without %{})
        
        Returns:
            str: Evaluated macro value
        """
        output, returncode = self.executeCommand(["rpmbuild", "--eval", f"%{{{macro}}}"])
        if returncode != 0:
            la.LoggingAccess().log(f"Failed to evaluate macro {macro}", vc.Verbosity.ERROR)
            return ""
        return output.strip()




    def executeCommand(self, cmds):
        o, e, r = exxec.executeShell(" ".join([self.command, "run", "--rm", "-it", self.current_snapshot, "/bin/sh", "-c", "\'"] + cmds + ["\'"]))
        la.LoggingAccess().log(e, vc.Verbosity.PODMAN)
        return o, r

    #def executeScriptlet(self, executor, file, params, suffix):
    #    pass

    def provideCleanUsefullRoot(self):
        initName = "init"
        if self.inited:
            self.current_snapshot=initName
        else:
            o, e, r = exxec.processToStringsWithResult(self.mainCommand() + [initName, "-f","utils/podman/dockerfiles/Init", "."])
            if r != 0:
                la.LoggingAccess().log("Container creation failed with exit code: " + str(r) + " and error message: " + e + ".")
            self.inited = True
            self.current_snapshot = initName

    def executeScriptlet(self, rpmFile, scriptletName, extraFlag="", script_arg=None):
        executor, scriptletFile = self.saveScriptlet(rpmFile, scriptletName)
        scriptletFileName = scriptletFile.split("/")[-1]
        containerName = self.current_snapshot.split("_")[0] + "_" + scriptletName + (("_" + extraFlag) if extraFlag != "" else "")
        script_arg_addition = [] if script_arg is None else ["--build-arg", "SCRIPTARG=" + script_arg]
        o, e, r = exxec.processToStringsWithResult(
            self.mainCommand() + [containerName, "-f", "utils/podman/dockerfiles/RunScriptlet", ".", "--build-arg", "BASE_IMAGE=" + self.current_snapshot, "--build-arg", "EXECUTOR=" + executor, "--build-arg", "FILE=" + self.scriptletTmpDir + "/" + scriptletFileName] + script_arg_addition)
        if scriptletFileName + " failed!!" in o:
            r = 1
        if r != 0:
            la.LoggingAccess().log("Container creation failed with exit code: " + str(r) + " and error message: " + e + ".")
        self.current_snapshot = containerName
        return o, r

    def saveScriptlet(self, rpmFile, scriptletName, params=""):
        executor, lines = rpmuts.getSrciplet(rpmFile, scriptletName)
        scriptletSuffix = "_" + scriptletName + "_" + utils.pkg_name_split.get_subpackage_only(ntpath.basename(rpmFile))
        scritletFile = tu.saveStringsAsTmpFile(lines, scriptletSuffix, self.scriptletTmpDir)
        return executor, scritletFile

    def getSnapshot(self, name):
        self.current_snapshot=name

    def run_all_scriptlets_for_install(self, pkg):
        key = utils.pkg_name_split.get_subpackage_only((ntpath.basename(pkg))) + "_" + utils.rpmbuild_utils.ScripletStarterFinisher.installScriptlets[-1] + "_" + "a"
        if key in self.snapshots:
            la.LoggingAccess().log(pkg + " already installed in snapshot. Rolling to " + key,
                                   vc.Verbosity.PODMAN)
            self.getSnapshot(key)
            return
        self.importRpm(pkg)
        for script in utils.rpmbuild_utils.ScripletStarterFinisher.installScriptlets:
            la.LoggingAccess().log("        " + "running " + script + " from " +
                                   os.path.basename(pkg),
                                   vc.Verbosity.TEST)
            try:
                self.executeScriptlet(pkg, script, "a", "1")
            except utils.podman.podman_execution_exception.PodmanExecutionException:
                la.LoggingAccess().log("        " + script + " script not found in " +
                                       os.path.basename(pkg),
                                       vc.Verbosity.TEST)
        return True

    def execute_ls(self, dir):
        return self.executeCommand(["ls", dir])

    def get_masters(self):
        otp, r = self.execute_ls(ALTERNATIVES_DIR)
        masters = otp.split()
        return masters


    def parse_alternatives_display(self, master):
        """
        Alternatives --display master provide us with a lot of information, that are parsed here. Use the getters
        below every time you need something.
        """
        output, r = self.executeCommand(["alternatives --display " + master])
        #output = self.display_alternatives(master)
        if len(output.strip()) == 0:
            la.LoggingAccess().log("alternatives --display master output is empty",
                                   vc.Verbosity.PODMAN)
            raise utils.podman.podman_execution_exception.PodmanExecutionException("alternatives --display master "
                                                                             "output is empty ")
        data = {}
        otp = output.splitlines()
        try:
            data[PRIORITY] = otp[2].split(" ")[-1]
        except Exception:
            raise utils.podman.podman_execution_exception.PodmanExecutionException("alternatives output reading encountered "
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


# Try to avoid making unnecessary instances of Podman()
# if possible, try to work with the DefaultPodman and its snapshots
class DefaultPodman(Podman, metaclass=Singleton):
    pass
