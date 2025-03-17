import config.global_config
import utils.build_downloader
import outputControl.logging_access as la
import utils.rpm_list as rpm_list
import config.verbosity_config as vc

VERSION_STRING = "jdks_specification_framework, version 0.1"


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class RuntimeConfig(metaclass=Singleton):
    """
    This class handles configuration prior the run of the test cases. It keeps information about the rpms,
    log files, default configuration of the tests and sets configuration from the parser.
    """

    def __init__(self):
        self.pkgsDir = "rpms"
        self.logsFile = "jsf.log"
        self.rpmList = None
        self.docs = False
        self.header = True
        self.archs = None
        self.verbosity = vc.Verbosity.TEST
        self.diewith = None
        self.current_arch = None

    def getRpmList(self):
        if self.rpmList is None:
            self.rpmList = rpm_list.RpmList(self.getPkgsDir())
        return self.rpmList

    def setLogsFile(self, nwFile):
        oldValue = self.logsFile
        self.logsFile = nwFile
        la.LoggingAccess().log("Logfile set to " + nwFile + " instead of " + oldValue, vc.Verbosity.TEST)

    def set_verbosity(self, verbosity):
        self.verbosity = verbosity

    def get_verbosity(self):
        return self.verbosity

    def getLogsFile(self):
        return self.logsFile

    def getDocs(self):
        return self.docs

    def isHeader(self):
        return self.header

    def setPkgsDir(self, nwDir):
        la.LoggingAccess().log("Rpms looked for in " + nwDir + " instead of " + self.pkgsDir, vc.Verbosity.TEST)
        self.pkgsDir = nwDir

    def getPkgsDir(self):
        return self.pkgsDir

    def setArchs(self, archString):
        if archString == "all":
            self.archs = config.global_config.getAllArchs()
        else:
            words = archString.split(",")
            self.archs = words
        la.LoggingAccess().log("archs limited/forced to " + str(self.archs), vc.Verbosity.TEST)

    def getArchs(self):
        return self.archs

    def setFromParser(self, args):
        # Order matters a lot!
        # logfile must go first
        if args.logfile:
            self.setLogsFile(args.logfile)
        if args.version:
            la.LoggingAccess().stdout(VERSION_STRING)
            return False
        # later it does not matter as logging is already going to log file
        la.LoggingAccess().log(VERSION_STRING, vc.Verbosity.TEST)
        # switches should go before commands, so commands can use them
        if args.dir:
            self.setPkgsDir(args.dir)
        if args.archs:
            self.setArchs(args.archs)
        if args.build:
            r = utils.build_downloader.getBuild(args.build)
            # failed? exit...
            if not r:
                return False
        if args.docs:
            # no setter - should not be set from outside
            self.docs = True
        if args.noheader:
            # no setter - should not be set from outside
            self.header = False
        if args.verbosity:
            try:
                verbosity = vc.Verbosity(int(args.verbosity))
            except Exception:
                raise AttributeError("Invalid verbosity argument, expected 1, 2 or 3, "
                                     "but got {}.".format(args.verbosity))
            self.set_verbosity(verbosity)
        if args.diewith:
            try:
                val = int(args.diewith)
            except Exception:
                raise AttributeError("diewith argument must be integer")
            self.diewith = val
        return True
