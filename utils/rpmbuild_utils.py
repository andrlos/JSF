import outputControl.logging_access as la
import utils.process_utils
import utils.test_utils
import os
import config.verbosity_config as vc

def rpmbuildEval(macro):
    return utils.process_utils.processToString(['rpmbuild', '--eval', '%{' + macro + '}'])


def listFilesInPackage(rpmFile):
    return utils.process_utils.processAsStrings(['rpm', '-qlp', rpmFile])


def listDocsInPackage(rpmFile):
    return utils.process_utils.processAsStrings(['rpm', '-qldp', rpmFile])


def listConfigFilesInPackage(rpmFile):
    return utils.process_utils.processAsStrings(['rpm', '-qlcp', rpmFile])


def listOfRequires(rpmFile):
    return utils.process_utils.processAsStrings(['rpm', '--requires', '-qp', rpmFile])


def listOfProvides(rpmFile):
    return utils.process_utils.processAsStrings(['rpm', '--provides', '-qp', rpmFile])


def listOfObsoletes(rpmFile):
    return utils.process_utils.processAsStrings(['rpm', '--obsoletes', '-qp', rpmFile])


def listOfVersionlessRequires(rpmFile):
    return _filterVersions(listOfRequires(rpmFile))


def listOfVersionlessProvides(rpmFile):
    return _filterVersions(listOfProvides(rpmFile))


def listOfVersionlessObsoletes(rpmFile):
    return _filterVersions(listOfObsoletes(rpmFile))


def _filterVersions(listOfStrings):
    filtered = []
    for orig in listOfStrings:
        filtered.append(orig.split()[0])
    return filtered


def _isScripletLine(scriplet, line):
    return line.startswith(scriplet + " " + ScripletStarterFinisher.scriptlet)


PRETRANS = 'pretrans'
PREINSTALL = 'preinstall'
POSTINSTALL = 'postinstall'
TGINSTALL = 'triggerinstall'
TGUNINSTALL = 'triggeuninstall'
PREUNINSTALL = 'preuninstall'
POSTUNINSTALL = 'postuninstall'
TGPOSTUNINSTALL = 'triggerpostuninstall'
POSTTRANS = 'posttrans'


def isScripletNameValid(name):
    return name in ScripletStarterFinisher.allScriplets


class ScripletStarterFinisher:
    # hard to say when rpm uses uninstall or just un or install or just "nothing"
    allScriplets = [
        PRETRANS,
        PREINSTALL,
        POSTINSTALL,
        TGINSTALL,
        TGUNINSTALL,
        PREUNINSTALL,
        POSTUNINSTALL,
        TGPOSTUNINSTALL,
        POSTTRANS
    ]

    installScriptlets = [
        PRETRANS,
        PREINSTALL,
        POSTINSTALL,
        TGINSTALL,
        POSTTRANS
    ]

    uninstallScriptlets = [
        TGUNINSTALL,
        PREUNINSTALL,
        POSTUNINSTALL,
        TGPOSTUNINSTALL
    ]

    postScripts = allScriplets[2:]

    scriptlet = "scriptlet"

    def __init__(self, iid):
        self.id = iid

    def start(self, line):
        return _isScripletLine(self.id, line)

    def stop(self, line):
        for scriptlet in ScripletStarterFinisher.allScriplets:
            if _isScripletLine(scriptlet, line):
                return False  # stop
        return True  # continue


scriptlets = dict()

# returns tuple of executor of the string (eg. lua, shell) and the script itself
def getSrciplet(rpmFile, scripletId):
    if not isScripletNameValid(scripletId):
        la.LoggingAccess().log("warning! Scriplet name " + scripletId
                                                         + " is not known. It should be one of: "
                                                         + ",".join(ScripletStarterFinisher.allScriplets),
                               vc.Verbosity.TEST)
    key = rpmFile+"-"+scripletId
    if key in scriptlets:
        la.LoggingAccess().log(key + " already cached, returning", vc.Verbosity.MOCK)
        return scriptlets[key]
    la.LoggingAccess().log(key + " not yet cached, reading", vc.Verbosity.MOCK)
    sf = ScripletStarterFinisher(scripletId)
    script = utils.process_utils.processAsStrings(['rpm', '-qp', '--scripts', rpmFile], sf.start, sf.stop,
                                                False)
    if len(script) == 0:
        scriptlet = ("/bin/sh", [])
    else:
        #two argumentless strips to accommodate for whitespace before the "<lua>"
        executor = script[0].split("using")[1].strip().strip("):<>").strip()
        scriptlet = (executor, script[1:])
    scriptlets[key] = scriptlet
    return scriptlet


def unpackFilesFromRpm(rpmFile, destination):
    absFile = os.path.abspath(rpmFile)
    utils.test_utils.mkdir_p(destination)
    sout, serr, res = utils.process_utils.executeShell("cd "+destination+" && rpm2cpio "+absFile+" | cpio -idmv")
    return sout, serr, res
