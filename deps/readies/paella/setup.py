
import os
import sys
import tempfile
from .platform import OnPlatform, Platform

#----------------------------------------------------------------------------------------------

class Runner:
    def __init__(self, nop=False):
        self.nop = nop

    def run(self, cmd, output_on_error=False, _try=False):
        print(cmd)
        sys.stdout.flush()
        if self.nop:
            return
        if output_on_error:
            fd, temppath = tempfile.mkstemp()
            os.close(fd)
            cmd = "{{ {}; }} >{} 2>&1".format(cmd, temppath)
        rc = os.system(cmd)
        if rc > 0:
            if output_on_error:
                os.system("cat {}".format(temppath))
                os.remove(temppath)
            eprint("command failed: " + cmd)
            sys.stderr.flush()
            if not _try:
                sys.exit(1)
        return rc

    def has_command(self, cmd):
        return os.system("command -v " + cmd + " > /dev/null") == 0

#----------------------------------------------------------------------------------------------

class RepoRefresh(OnPlatform):
    def __init__(self, runner):
        OnPlatform.__init__(self)
        self.runner = runner

    def redhat_compat(self):
        pass

    def debian_compat(self):
        self.runner.run("apt-get -qq update -y")

    def macosx(self):
        self.runner.run("brew update || true")

#----------------------------------------------------------------------------------------------

class Setup(OnPlatform):
    def __init__(self, nop=False):
        OnPlatform.__init__(self)
        self.runner = Runner(nop)
        self.stages = [0]
        self.platform = Platform()
        self.os = self.platform.os
        self.dist = self.platform.dist
        self.ver = self.platform.os_ver

        if self.has_command("python"):
            self.python = "python"
        elif self.has_command("python2"):
            self.python = "python2"
        elif self.has_command("python3"):
            self.python = "python3"

        if self.os == 'macosx':
            # this is required because osx pip installed are done with --user
            os.environ["PATH"] = os.environ["PATH"] + ':' + '$HOME/Library/Python/2.7/bin'
            # this prevents brew updating before each install
            os.environ["HOMEBREW_NO_AUTO_UPDATE"] = "1"

        if self.platform.is_debian_compat():
            # prevents apt-get from interactively prompting
            os.environ["DEBIAN_FRONTEND"] = 'noninteractive'

        os.environ["PYTHONWARNINGS"] = 'ignore:DEPRECATION::pip._internal.cli.base_command'

    def setup(self):
        RepoRefresh(self.runner).invoke()
        self.invoke()

    def run(self, cmd, output_on_error=False, _try=False):
        return self.runner.run(cmd, output_on_error=output_on_error, _try=_try)

    def has_command(self, cmd):
        return self.runner.has_command(cmd)

    #------------------------------------------------------------------------------------------

    def apt_install(self, packs, group=False, _try=False):
        self.run("apt-get -qq install -y " + packs, output_on_error=True, _try=_try)

    def yum_install(self, packs, group=False, _try=False):
        if not group:
            self.run("yum install -q -y " + packs, output_on_error=True, _try=_try)
        else:
            self.run("yum groupinstall -y " + packs, output_on_error=True, _try=_try)

    def dnf_install(self, packs, group=False, _try=False):
        if not group:
            self.run("dnf install -y " + packs, output_on_error=True, _try=_try)
        else:
            self.run("dnf groupinstall -y " + packs, output_on_error=True, _try=_try)

    def zypper_install(self, packs, group=False, _try=False):
        self.run("zipper --non-interactive install " + packs, output_on_error=True, _try=_try)

    def pacman_install(self, packs, group=False, _try=False):
        self.run("pacman --noconfirm -S " + packs, output_on_error=True, _try=_try)

    def brew_install(self, packs, group=False, _try=False):
        # brew will fail if package is already installed
        for pack in packs.split():
            self.run("brew list {} &>/dev/null || brew install {}".format(pack, pack), output_on_error=True, _try=_try)

    def install(self, packs, group=False, _try=False):
        if self.os == 'linux':
            if self.dist == 'fedora':
                self.dnf_install(packs, group=group, _try=_try)
            elif self.dist == 'ubuntu' or self.dist == 'debian':
                self.apt_install(packs, group=group, _try=_try)
            elif self.dist == 'centos' or self.dist == 'redhat':
                self.yum_install(packs, group=group, _try=_try)
            elif self.dist == 'suse':
                self.zypper_install(packs, group=group, _try=_try)
            elif self.dist == 'arch':
                self.pacman_install(packs, group=group, _try=_try)
            else:
                Assert(False), "Cannot determine installer"
        elif self.os == 'macosx':
            self.brew_install(packs, group=group, _try=_try)
        else:
            Assert(False), "Cannot determine installer"

    def group_install(self, packs, _try=False):
        self.install(packs, group=True, _try=_try)

    #------------------------------------------------------------------------------------------

    def yum_add_repo(self, repourl, repo="", _try=False):
        if not self.has_command("yum-config-manager"):
            self.install("yum-utils")
        self.run("yum-config-manager -y --add-repo {}".format(repourl), _try=_try)

    def apt_add_repo(self, repourl, repo="", _try=False):
        if not self.has_command("yum-config-manager"):
            self.install("software-properties-common")
        self.run("add-apt-repository -y {}".format(repourl), _try=_try)
        self.run("apt-get -qq update", _try=_try)

    def dnf_add_repo(self, repourl, repo="", _try=False):
        if self.run("dnf config-manager 2>/dev/null", _try=True):
            self.install("dnf-plugins-core", _try=_try)
        self.run("dnf config-manager -y --add-repo {}".format(repourl), _try=_try)

    def zypper_add_repo(self, repourl, repo="", _try=False):
        pass

    def pacman_add_repo(self, repourl, repo="", _try=False):
        pass

    def brew_add_repo(self, repourl, repo="", _try=False):
        pass

    def add_repo(self, repourl, repo="", _try=False):
        if self.os == 'linux':
            if self.dist == 'fedora':
                self.dnf_add_repo(repourl, repo=repo, _try=_try)
            elif self.dist == 'ubuntu' or self.dist == 'debian':
                self.apt_add_repo(repourl, repo=repo, _try=_try)
            elif self.dist == 'centos' or self.dist == 'redhat':
                self.yum_add_repo(repourl, repo=repo, _try=_try)
            elif self.dist == 'suse':
                self.zypper_add_repo(repourl, repo=repo, _try=_try)
            elif self.dist == 'arch':
                self.pacman_add_repo(repourl, repo=repo, _try=_try)
            else:
                Assert(False), "Cannot determine installer"
        elif self.os == 'macosx':
            self.brew_add_repo(packs, group=group, _try=_try)
        else:
            Assert(False), "Cannot determine installer"

    #------------------------------------------------------------------------------------------

    def pip_install(self, cmd, _try=False):
        pip_user = ''
        if self.os == 'macosx':
            pip_user = '--user '
        self.run("pip install --disable-pip-version-check " + pip_user + cmd, output_on_error=True, _try=_try)

    def pip3_install(self, cmd, _try=False):
        pip_user = ''
        if self.os == 'macosx':
            pip_user = '--user '
        self.run("pip3 install --disable-pip-version-check " + pip_user + cmd, output_on_error=True, _try=_try)

    def setup_pip(self, _try=False):
        get_pip = "set -e; wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py"
        if not self.has_command("pip"):
            # self.install("python3-distutils")
            self.install_downloaders()
            self.run(get_pip + "; " + self.python + " /tmp/get-pip.py", output_on_error=True, _try=_try)

    def install_downloaders(self, _try=False):
        if self.os == 'linux':
            self.install("ca-certificates", _try=_try)
        self.install("curl wget", _try=_try)

    def install_git_lfs_on_linux(self, _try=False):
        self.run("curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash", _try=_try)
        self.install("git-lfs", _try=_try)
