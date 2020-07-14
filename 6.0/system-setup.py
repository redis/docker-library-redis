#!/usr/bin/env python2

import sys
import os
import popen2
import argparse

HERE=os.path.dirname(__file__)
if os.path.exists(os.path.join(HERE, "deps/readies")):
    # true within docker
    sys.path.insert(0, os.path.join(HERE, "deps/readies"))
else:
    sys.path.insert(0, os.path.join(HERE, "../deps/readies"))
import paella

#----------------------------------------------------------------------------------------------

class RedisSetup(paella.Setup):
    def __init__(self, nop=False):
        paella.Setup.__init__(self, nop)

    def common_first(self):
        self.install_downloaders()

    def debian_compat(self):
        self.install("build-essential libssl-dev")
        if self.osnick == 'trusty':
            self.add_repo("ppa:ubuntu-toolchain-r/test")
            self.install("gcc-7 g++-7")
            self.run("update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-7 60 --slave /usr/bin/g++ g++ /usr/bin/g++-7")

    def redhat_compat(self):
        self.group_install("'Development Tools'")
        self.install("centos-release-scl")
        self.install("devtoolset-8")
        self.run("cp /opt/rh/devtoolset-8/enable /etc/profile.d/scl-devtoolset-8.sh")
        # self.run("scl enable devtoolset-8 bash")
        self.install("libatomic openssl-devel")

    def fedora(self):
        self.group_install("'Development Tools'")
        self.install("libatomic openssl-devel")

    def macosx(self):
        r, w, e = popen2.popen3('xcode-select -p')
        if r.readlines() == []:
            fatal("Xcode tools are not installed. Please run xcode-select --install.")
        self.install("openssl")

    def common_last(self):
        self.install("dirmngr gnupg patch pkg-config")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for RedisGears build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

RedisSetup(nop = args.nop).setup()
