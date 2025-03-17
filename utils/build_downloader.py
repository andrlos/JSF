"""In time of writing this library, the koji python library was not compatible with python3, so legacy approach
 was chosen"""

import ntpath
import os
import shutil

#import urllib3

import utils.pkg_name_split as split
import config.global_config
import config.runtime_config
import outputControl.logging_access as la
import utils.rpm_list
import utils.process_utils
import config.verbosity_config as vc

BREW = "brew"
KOJI = "koji"


def getBuild(nvr):
    "This method download build from brw. The filtering of arches depends on RuntimeConfig().getArchs();"
    target = _checkDest(config.runtime_config.RuntimeConfig().getPkgsDir())
    command = _getCommand(nvr)
    la.LoggingAccess().log("using " + command, vc.Verbosity.TEST)
    packages = _getBuildInfo(command, nvr)
    if len(packages) == 0:
        raise Exception("No pkgs to download. Verify build or archs")
    la.LoggingAccess().log("going to download " + str(len(packages)) + " rpms", vc.Verbosity.TEST)
    _downloadBrewKojiBuilds(packages, target)
    return True


def _downloadBrewKojiBuilds(pkgs, targetDir):
    for i, pkg_with_signature in enumerate(pkgs):
        pkg = split.drop_signature(pkg_with_signature)
        mainUrl = _getMainUrl(pkg)
        url = "unknonw_service"
        if KOJI in pkg:
            url = mainUrl + pkg.replace("/mnt/koji/", "/")
        if BREW in pkg:
            url = mainUrl + pkg.replace("/mnt/redhat/", "/")
        la.LoggingAccess().log("downloading " + str(i + 1) + "/" + str(len(pkgs)) + " - " + url, vc.Verbosity.TEST)
        targetFile = targetDir + "/" + ntpath.basename(pkg)
        http = "bullshit" #urllib3.PoolManager()
        with http.request('GET', url, preload_content=False) as r, open(targetFile, 'wb') as out_file:
            shutil.copyfileobj(r, out_file)


def _isRpm(line):
    return line == "RPMs:"


def _getBuildInfo(cmd, nvr):
    allPkgs = utils.process_utils.processAsStrings([cmd, 'buildinfo', nvr], _isRpm, None, False)
    rpms = []
    for pkg in allPkgs :
        if _isArchValid(pkg):
            rpms.append(pkg)
    return rpms


def _checkDest(dir):
    absOne = os.path.abspath(dir)
    if not os.path.exists(absOne):
        la.LoggingAccess().log("Creating: " + absOne, vc.Verbosity.TEST)
        os.mkdir(absOne)
    if not os.path.isdir(absOne):
        raise Exception(absOne + " Must be a directory, is not")
    if not os.listdir(absOne) == []:
        raise Exception(absOne + " Is not empty, please fix")
    la.LoggingAccess().log("Using as download target: " + absOne, vc.Verbosity.TEST)
    return absOne


def _isArchValid(rpmLine):
    arches= config.runtime_config.RuntimeConfig().getArchs()
    if arches is None or len(arches) == 0:
        arches = config.global_config.getAllArchs()
    for arch in arches:
        if "/" + arch + "/" in rpmLine or "." + arch + "." in rpmLine:
            return True
    return False


def _getCommand(nvr):
    os = _getOs(nvr + ".fakeArch")
    if utils.rpm_list.isRhel(os):
        return BREW
    if utils.rpm_list.isFedora(os):
        return KOJI
    raise Exception("Unknown os - " + os)


def _getMainUrl(path_rpm):
    rpm = ntpath.basename(path_rpm)
    os = _getOs(rpm)
    if utils.rpm_list.isRhel(os):
        return "http://download.devel.redhat.com/"
    if utils.rpm_list.isFedora(os):
        return "http://koji.fedoraproject.org"
    raise Exception("Unknown os - " + os)


def _getOs(rpm):
    os = split.get_dist(rpm)
    la.LoggingAccess().log("in " + rpm + " recognized " + os, vc.Verbosity.TEST)
    return os
