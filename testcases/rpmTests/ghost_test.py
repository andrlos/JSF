import sys
import utils.pkg_name_split as ns
import utils.test_utils as tu
import outputControl.logging_access as la
import utils.process_utils as pu
import utils.mock.mock_executor as mexe
import utils.core.base_xtest as bt
import utils.test_constants as tc
import utils.core.configuration_specific as cs
import config.runtime_config as rc


class GhostTest(bt.BaseTest):
    def __init__(self):
        super().__init__()
        self.list_of_failed_tests = []

    def test_ghosts(self):
        return self.csch.ghost_test(self)

    def setCSCH(self):
        arch = self.getCurrentArch()
        rpms = rc.RuntimeConfig().getRpmList()
        if int(rpms.getMajorVersionSimplified()) == 8:
            if tc.is_arch_jitarch(arch) and "ppc" not in arch:
                self.csch = Ojdk8JIT()
                return
        elif int(rpms.getMajorVersionSimplified()) == 11:
            if (arch in ["armv7hl", "s390x"] or tc.is_arch_jitarch(arch)) and "ppc" not in arch:
                self.csch = Ojdk11JIT()
                return
            elif int(rpms.getMajorVersionSimplified()) == 11:
                self.csch = Ojdk11JIT()
                return
        else:
            self.csch = OjdklatestJIT()
            return


class Default(cs.JdkConfiguration):
    def __init__(self):
        super().__init__()
        self.expected_ghosts = {}

    def _get_hardcoded_ghosts(self, file):
        return set()

    def ghost_test(self, this):
        documentation = "This tests checks if every master is ghosted. Ghosted files are listed via rpm command," \
                        " as a difference between \'rpm -q -l\' and \'rpm -q -l --no-ghost\'"
        files = rc.RuntimeConfig().getRpmList().files
        files = [x.replace("rpms/", "") for x in files]
        if not self.documenting:
            files = [x for x in files if tu.validate_arch_for_rpms(this.current_arch) == ns.get_arch(x)]
            for file in files:
                self._check_ghosts_per_file(file)
        self._document(documentation)
        return self.passed, self.failed

    def _check_ghosts_per_file(self, file):
        rpm_ghosts = self._get_actual_ghosts(file)
        default_masters = set(mexe.DefaultMock().get_default_masters())
        mexe.DefaultMock().run_all_scriptlets_for_install("rpms/" + file)
        resolved_rpm_ghosts = set()
        for ghost in rpm_ghosts:
            newghost = ghost.replace("\n", "")
            # skipping rpmmoved ghosts - those are only for removed/moved directories so that user doesnt loose data upon upgrade
            if not newghost.endswith(".rpmmoved"):
                resolved_rpm_ghosts.add(tu.resolve_link(newghost))
        if "debug" in file:
            tu.passed_or_failed(self, resolved_rpm_ghosts == self._get_hardcoded_ghosts(file),
                                "Debug packages are not expected to have any ghosts. Found ghosts: " + str(
                                    resolved_rpm_ghosts))
            return
        expected_master_ghosts = set()
        expected_follower_ghosts = set()
        if rc.RuntimeConfig().getRpmList().is_system_jdk():
            expected_master_ghosts = set(mexe.DefaultMock().get_masters()).difference(default_masters)
            for master in expected_master_ghosts.copy():
                expected_follower_ghosts = expected_follower_ghosts.union(set(mexe.DefaultMock().get_slaves_with_links(master).values()))
        resolved_actual_ghosts = {}
        for ghost in expected_master_ghosts:
            resolved_ghost = tu.resolve_link(mexe.DefaultMock().get_target(ghost))
            resolved_actual_ghosts[resolved_ghost] = ghost
        for ghost in expected_follower_ghosts:
            if ghost.startswith("/usr/lib/jvm/"):
                resolved_actual_ghosts[ghost] = "follower"
        for ghost in self._get_hardcoded_ghosts(file):
            resolved_actual_ghosts[ghost] = "hardcoded"
        if not tu.passed_or_failed(self, set(resolved_actual_ghosts.keys()) == resolved_rpm_ghosts, "Sets of ghost are not correct for " + file + ". Differences will follow."):
            missing_ghosts = set(resolved_actual_ghosts.keys()).difference(resolved_rpm_ghosts)
            extra_ghosts = resolved_rpm_ghosts.difference(set(resolved_actual_ghosts.keys()))
            missing_ghosts_masters = []
            for ghost in missing_ghosts:
                missing_ghosts_masters.append(ghost)
            if len(missing_ghosts) > 0:
                tu.passed_or_failed(self, False, "Masters not ghosted via %ghost declaration in specfile: " + str(missing_ghosts_masters))
            if len(extra_ghosts) >0:
                tu.passed_or_failed(self, False, "Ghosts that do not ghost any alternatives: " + str(extra_ghosts))

    def _get_actual_ghosts(self, filename):
        output, error, res = pu.executeShell("rpm -q -l rpms/" + filename)
        allfiles = set(output.split("\n"))
        output, error, res = pu.executeShell("rpm -q -l --noghost rpms/" + filename)
        withoutghosts = set(output.split("\n"))
        ghosts = allfiles.difference(withoutghosts)
        return ghosts


class Ojdk8JIT(Default):
    def _get_hardcoded_ghosts(self, file):
        ghosts = super(Ojdk8JIT, self)._get_hardcoded_ghosts(file)
        arch = ns.get_arch(file)
        if "headless" in file and not "info" in file:
            nvra = ns.get_nvra(file)
            archinstall = ns.get_arch_install(file)
            debugsuffix = ""
            for suffix in tc.get_debug_suffixes():
                if suffix in file:
                    debugsuffix = suffix
                    break
            if arch == "i686":
                nvra = nvra.replace(arch, archinstall)
            ghosts.add("/usr/lib/jvm/" + nvra + debugsuffix + "/jre/lib/" + archinstall + "/client/classes.jsa")
            ghosts.add("/usr/lib/jvm/" + nvra + debugsuffix + "/jre/lib/" + archinstall + "/server/classes.jsa")
        return ghosts


class Ojdk11JIT(Default):
    def _get_hardcoded_ghosts(self, file):
        ghosts = super(Ojdk11JIT, self)._get_hardcoded_ghosts(file)
        arch = ns.get_arch(file)
        if "headless" in file and not "info" in file:
            nvra = ns.get_nvra(file)
            archinstall = ns.get_arch_install(file)
            debugsuffix = ""
            for suffix in tc.get_debug_suffixes():
                if suffix in file:
                    debugsuffix = suffix
                    break
            if arch == "i686" or arch == "armv7hl":
                nvra = nvra.replace(arch, archinstall)
            ghosts.add("/usr/lib/jvm/" + nvra + debugsuffix + "/lib/server/classes.jsa")
        return ghosts


class OjdklatestJIT(Default):
    def _get_hardcoded_ghosts(self, file):
        ghosts = super(OjdklatestJIT, self)._get_hardcoded_ghosts(file)
        arch = ns.get_arch(file)
        if "headless" in file and not "info" in file:
            nvra = ns.get_nvra(file)
            archinstall = ns.get_arch_install(file)
            debugsuffix = ""
            for suffix in tc.get_debug_suffixes():
                if suffix in file:
                    debugsuffix = suffix
                    break
            if arch == "i686" or arch == "armv7hl":
                nvra = nvra.replace(arch, archinstall)
            ghosts.add("/usr/lib/jvm/" + nvra + debugsuffix + "/lib/server/classes.jsa")
        return ghosts


def testAll():
    return GhostTest().execute_tests()


def documentAll():
    la.LoggingAccess().stdout("Ghosts")
    return GhostTest().execute_special_docs()

def main(argv):
    bt.defaultMain(argv, documentAll, testAll)


if __name__ == "__main__":
    main(sys.argv[1:])


