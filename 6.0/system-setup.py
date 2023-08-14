#!/usr/bin/env python3

import sys
import os
import argparse

HERE=os.path.dirname(__file__)
READIES = os.path.join(HERE, "deps/readies")
if not os.path.exists(READIES):
    # not in docker
    READIES = os.path.join(HERE, "../deps/readies")
sys.path.insert(0, READIES)
import paella

#----------------------------------------------------------------------------------------------

class RedisSetup(paella.Setup):
    def __init__(self, nop=False):
        paella.Setup.__init__(self, nop)

    def common_first(self):
        self.install_downloaders()

    def debian_compat(self):
        if self.osnick == 'trusty':
            self.run(f"{READIES}/bin/getgcc --modern")
        else:
            self.run(f"{READIES}/bin/getgcc")
        self.install("libssl-dev")

    def redhat_compat(self):
        self.run(f"{READIES}/bin/getgcc --modern")
        self.install("libatomic openssl-devel")

    def fedora(self):
        self.run(f"{READIES}/bin/getgcc")
        self.install("libatomic openssl-devel jemalloc-devel")

    def macos(self):
        self.install("openssl")

    def alpine(self):
        self.install("gcc make openssl openssl-dev libatomic dev86 musl-dev")

    def common_last(self):
        if self.dist != "alpine":
            self.install("dirmngr gnupg patch pkg-config")
        else:
            self.install("patch pkgconfig gnupg linux-headers")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for RedisGears build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

RedisSetup(nop = args.nop).setup()
