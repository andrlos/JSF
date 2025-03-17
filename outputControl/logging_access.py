import outputControl.file_log
import config.runtime_config as rc
import config.verbosity_config as vc


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class LoggingAccess(metaclass=Singleton):
    pass

    def stdout(self, arg2):
        print(arg2)
        self.log(arg2, vc.Verbosity.ERROR)

    def log(self, logmsg, verbosity=vc.Verbosity.TEST, jtregfilename=""):
        if verbosity.value <= rc.RuntimeConfig().get_verbosity().value:
            outputControl.file_log.FileLog().println(logmsg)
        if verbosity == verbosity.JTREG:
            if logmsg == "" and jtregfilename != "":
                outputControl.file_log.JtregLog().__init__(jtregfilename)
            else:
                outputControl.file_log.JtregLog(jtregfilename).println(logmsg)
        outputControl.file_log.DefaultLog().println(logmsg)

