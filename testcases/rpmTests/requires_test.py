import utils.pkg_name_split as ns
import utils.core.base_xtest as bt
import config.runtime_config as rc
import outputControl.logging_access as la
import utils.process_utils as pu
import utils.test_utils as tu
import utils.core.configuration_specific as cs
import config.global_config as gc

import sys


class Default(cs.JdkConfiguration):
    def __init__(self, this):
        super().__init__()
        self.rpms = rc.RuntimeConfig().getRpmList()
        self.this = this

    def _get_artificial_requires(self, filename):
        output, error, res = pu.executeShell(f"rpm -qp rpms/{filename} --requires")
        lines = output.split("\n")
        return lines

    def check_artificial_requires(self, this):
        files = self.rpms.files
        documentation = ""
        files = [x.replace("rpms/", "") for x in files]
        if not self.documenting:
            files = [x for x in files if tu.validate_arch_for_rpms(this.current_arch) == ns.get_arch(x)]
        for filename in files:
            filename = filename.split("/")[-1]
            expected_requires = self._get_expected_articial_requires(filename)
            documentation += make_rpm_readable(filename) + " should have these artificial requires: " + ", ".join(expected_requires) + "\n"
            if self.documenting:
                continue
            given_requires = self._get_artificial_requires(filename)
            missing_requires = []
            for require in expected_requires:
                if not tu.passed_or_failed(self, self._is_in_requires(require, given_requires), make_rpm_readable(filename) + " is missing require: " + require):
                    missing_requires.append(require)

        self._document(documentation)
        return self.passed, self.failed

    def _is_in_requires(self, r, set):
        for req in set:
            if r in req:
                return True
        return False

    def _get_expected_articial_requires(self, filename):
        name, java_ver, vendor, pkg, version, end = ns._hyphen_split(filename)
        arch = ns.get_arch(filename)
        requires = Empty(filename)
        if "slowdebug" == pkg or "fastdebug" == pkg or "" == pkg:
            requires = Basic(filename)
        elif "debuginfo" in pkg:
            requires = Empty(filename)
        elif "headless" in pkg:
            requires = Headless(filename)
        elif "openjfx-devel" in pkg:
            requires = OpenjfxDevel(filename)
        elif "openjfx" in pkg:
            requires = Openjfx(filename)
        elif "devel" in pkg:
            requires = Devel(filename)
        elif "static" in pkg:
            requires = StaticLibs(filename)
        elif "jmods" in pkg:
            requires = Jmods(filename)
        elif "demo" in pkg:
            requires = Demo(filename)
        elif "src" in pkg:
            requires = Src(filename)
        elif "javadoc" in pkg:
            requires = Javadoc(filename)
        return requires.expected_req


class Temurin(Default):
    def _get_expected_articial_requires(self, filename):
        return TemurinRequires(filename).expected_req


class RequiresTest(bt.BaseTest):
    instance = None

    def __init__(self):
        super().__init__()

    def setCSCH(self):
        rpms = rc.RuntimeConfig().getRpmList()
        if rpms.getVendor() == gc.ADOPTIUM:
            self.csch = Temurin(self)
            return
        self.csch = Default(self)

    def test_artificial_requires(self):
        self.csch.check_artificial_requires(self)
        return self.csch.check_artificial_requires(self)


class Empty:
    def __init__(self, filename):
        self.expected_req = []
        self.fill_description(filename)

    def get_proper_pkg_name(self):
        names = ["debuginfo", "slowdebug", "fastdebug", ""]
        for n in names:
            if n in self.desc['pkg']:
                return n

    def fill_description(self, filename):
        name, java_ver, vendor, pkg, version, end = ns._hyphen_split(filename)
        arch = ns.get_arch(filename)
        special_names = {
            "i686": "x86-32",
            "ppc64le": "ppc-64",
            "armv7hl": "armv7hl-32",
            "aarch64": "aarch-64",
            "x86_64": "x86-64",
            "s390x": "s390-64"
        }
        self.desc = {
            "name": name,
            "java_ver": java_ver,
            "vendor": vendor,
            "pkg": pkg,
            "version": version,
            "end": end,
            "arch": special_names[arch] if arch in special_names.keys() else arch,
            "start": name + '-' + java_ver + '-' + vendor
        }


class TemurinRequires(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        self.expected_req.extend([
            "/bin/sh",
            "/usr/sbin/alternatives",
            f"alsa-lib({self.desc['arch']})",
            "ca-certificates",
            "dejavu-sans-fonts",
            f"fontconfig({self.desc['arch']})",
            f"glibc({self.desc['arch']})",
            f"libX11({self.desc['arch']})",
            f"libXi({self.desc['arch']})",
            f"libXrender({self.desc['arch']})",
            f"libXtst({self.desc['arch']})",
            f"zlib({self.desc['arch']})",
            "rpmlib(CompressedFileNames)",
            "rpmlib(FileDigests)",
            "rpmlib(PayloadFilesHavePrefix)",
            "rpmlib(PayloadIsXz)"
        ])


class Basic(Empty):
    # Slowdebug, Fastdebug and the default one without any special name
    def __init__(self, filename):
        super().__init__(filename)
        self.expected_req.extend([
            f"fontconfig({self.desc['arch']})",
            "xorg-x11-fonts-Type1",
            f"{self.desc['start']}-headless{'-' + self.desc['pkg'] if self.desc['pkg'] else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}",
            f"libXcomposite({self.desc['arch']})"
        ])


class Headless(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        self.expected_req.extend([
            "ca-certificates",
            "javapackages-filesystem",
            "cups-libs",
            f"lksctp-tools({self.desc['arch']})",
            "copy-jdk-configs",
            "tzdata-java"
        ])


class Devel(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"{self.desc['start']}{'-' + pkg if pkg else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}"
        ])


class StaticLibs(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"{self.desc['start']}-devel{'-' + pkg if pkg else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}"
        ])


class Jmods(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"{self.desc['start']}-devel{'-' + pkg if pkg else ''} = "
            f"{ns.get_version_full(filename)}"
        ])


class Demo(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"{self.desc['start']}{'-' + pkg if pkg else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}"
        ])


class Src(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"{self.desc['start']}-headless{'-' + pkg if pkg else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}"
        ])


class Javadoc(Empty):
    # And JavadocZip
    def __init__(self, filename):
        super().__init__(filename)
        self.expected_req.extend([
            "javapackages-filesystem"
        ])


class Openjfx(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"openjfx({self.desc['arch']})", # openjfx8?
            f"{self.desc['start']}{'-' + pkg if pkg else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}"
        ])


class OpenjfxDevel(Empty):
    def __init__(self, filename):
        super().__init__(filename)
        pkg = self.get_proper_pkg_name()
        self.expected_req.extend([
            f"openjfx-devel({self.desc['arch']})",
            f"{self.desc['start']}{'-' + pkg if pkg else ''}({self.desc['arch']}) = {ns.get_version_full(filename)}"
        ])


def make_rpm_readable(name):
    return ns.get_package_name(name) + "." + ns.get_arch(name)


def testAll():
    return RequiresTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Requires")
    return RequiresTest().execute_special_docs()


def main(argv):
    bt.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])
