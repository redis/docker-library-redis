#!/usr/bin/env python2

import sys
import os
import popen2
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "deps/readies"))
import paella

#----------------------------------------------------------------------------------------------

class RedisSetup(paella.Setup):
    def __init__(self, nop=False):
        paella.Setup.__init__(self, nop)

    def common_first(self):
        self.install_downloaders()

    def debian_compat(self):
        self.install("build-essential")

    def redhat_compat(self):
        self.group_install("'Development Tools'")
        self.install("libatomic")

    def fedora(self):
        self.group_install("'Development Tools'")
        self.install("libatomic")

    def macosx(self):
        r, w, e = popen2.popen3('xcode-select -p')
        if r.readlines() == []:
            fatal("Xcode tools are not installed. Please run xcode-select --install.")

    def common_last(self):
        self.install("dirmngr gnupg patch")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for RedisGears build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

RedisSetup(nop = args.nop).setup()
