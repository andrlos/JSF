import re
from collections import namedtuple
import config.global_config as gc
import ntpath
from collections import OrderedDict

RpmNameParts = namedtuple('RpmNameParts',
                          ['java', 'java_ver', 'vendor', 'pkg',
                           'version', 'release', 'dist', 'arch'])


def _rpmname_split_mapper(name):
    parts1 = _hyphen_split(name)
    parts2 = _dot_split(name)

    if gc.TEMURIN in name:
        return RpmNameParts(gc.TEMURIN, parts1[1], gc.ADOPTIUM, parts1[2], parts1[4], parts2[1], parts2[0], parts2[2])

    return RpmNameParts(parts1[0], parts1[1], parts1[2], parts1[3], parts1[4], parts2[0], parts2[1], parts2[2])


def _hyphen_split(name):
    """Split the rpm name according to hyphens, the subpackage string
    can be also empty or contain hyphens - as in devel-debug etc."""
    name = name.strip()
    hyphen_parts = name.split('-')
    num_h = len(hyphen_parts)
    if name.startswith(gc.ITW):
        icedtea, web,  *pkg, version, whole_end = hyphen_parts
        pkg = '-'.join(pkg)
        return [gc.ITW, gc.ITW, gc.ITW, pkg, version, whole_end]
    # rolling release is breaking everything, needs more checks, because it can break everything
    elif name.startswith("java-openjdk"):
        java, vendor, *pkg, version, whole_end = hyphen_parts
        pkg = '-'.join(pkg)
        java_ver = version.split(".")[0]
        return [java, java_ver, vendor, pkg, version, whole_end]
    else:
        java, java_ver, vendor, *pkg, version, whole_end = hyphen_parts
        pkg = '-'.join(pkg)
        return [java, java_ver, vendor, pkg, version, whole_end]


def _get_ith_part(i, name):
    name = ntpath.basename(name)
    parts = _hyphen_split(name)
    return parts[i]


def _get_ith_dotpart(i, name):
    name = ntpath.basename(name)
    parts = _dot_split(name)
    return parts[i]


def get_dottedsuffix(name):
    return _get_ith_part(5, name)


def _dot_split(name):
    name = name.strip()
    whole_end = get_dottedsuffix(name)
    period_parts = whole_end.split('.')
    if "rpm" in period_parts:
        without_rpm = period_parts[:-1]
    else:
        without_rpm = period_parts
    num_p = len(without_rpm)
    release = '.'.join(without_rpm[: num_p - 2])
    dist, arch = without_rpm[num_p - 2:]
    return [release, dist, arch]


def get_javaprefix(name):
    """Should be always java or temurin"""
    return _rpmname_split_mapper(name).java


def get_major_ver(name):
    """eg 1.7.0 or 9"""
    return _rpmname_split_mapper(name).java_ver


def get_vendor(name):
    """eg openjdk"""
    return _rpmname_split_mapper(name).vendor


def get_major_package_name(name):
    """or java-1.8.0-openjdk"""
    parts = _hyphen_split(name)
    if get_vendor(name) == gc.ADOPTIUM:
        return "-".join(list(_rpmname_split_mapper(name)[0:2]))
    return "-".join(list(_rpmname_split_mapper(name)[0:3]))


def get_package_name(name):
    """ eg java-1.8.0-openjdk-devel
        or java-1.8.0-openjdk
    """
    package = get_major_package_name(name)
    subpackage = get_subpackage_only(name)
    if subpackage == "":
        return package
    else:
        return package + "-" + subpackage


def get_subpackage_only(name):
    """ eg devel-debug"""
    return _rpmname_split_mapper(name).pkg


def get_minor_ver(name):
    """ eg 1.8.0.77"""
    return _rpmname_split_mapper(name).version


def get_release(name):
    """ eg 2.b03"""
    return _rpmname_split_mapper(name).release


def get_dist(name):
    """ eg fc25 or el6_7"""
    return _rpmname_split_mapper(name).dist


def get_arch(name):
    """ eg i686 """
    return _rpmname_split_mapper(name).arch


def get_arch_install(name):
    arch = get_arch(name)
    if arch == "x86_64":
        return "amd64"
    if arch == "i686":
        return "i386"
    if arch == "armv7hl":
        return "arm"
    return arch


def get_nvra(name):
    """ eg java-1.8.0-openjdk-1.8.0.101-4.b13.el7.i686"""
    n = name
    if n.endswith(".rpm"):
        sub = get_subpackage_only(name)
        if sub != "":
            n = n.replace("-" + sub, "")
        n = n.replace(".rpm", "")
    # this hook is necessary because of the rolling release, everything but the package name contains
    # the version (manpages, subdirs, links etc.)
    if n.startswith("java-latest-openjdk"):
        n = n.replace("java-latest-openjdk", "java-" + simplify_full_version(get_minor_ver(name)) + "-openjdk")
    return n


def get_name_version_release(name):
    return get_nvra(name).replace("." + get_arch(name), "")


def simplify_version(vers):
    old_naming_regex = re.compile("^[0-9].[0-9].[0-9]$")
    if old_naming_regex.match(vers):
        return vers.split(".")[1]
    return vers


def get_version_full(name):
    return get_version(name) + "." + get_dist(name)


def get_version(name):
    return "1:" + get_minor_ver(name) + "-" + get_release(name)


def simplify_full_version(vers, keepLegacy = False):
    if int(vers.split(".")[0]) > 1:
        return vers.split(".")[0]
    if keepLegacy:
        return ".".join(vers.split(".")[:3])
    return simplify_version(".".join(vers.split(".")[:3]))


def simplify_new_version(vers):
    return simplify_full_version(vers, True)


#recent changes in koji API started to append signature to the build path, this was screwing our download script
def drop_signature(rpm):
    if "\tSignatures" in rpm:
        return rpm.split("\t")[0]
    return rpm

