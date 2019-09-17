"""
Copyright 2019 Jeff Klesky

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import sys
import time

from flentsqm.controller import DownPassController
from flentsqm.naming import protect_for_filename
from flentsqm.runs import RunCollector
from flentsqm.router import Router

try:
    device = sys.argv[1]
except IndexError:
    print(f"Usage: {sys.argv[0]} 'Device Name'")
    exit(1)

tunnels = ["WireGuard"]
tests = ["tcp_8down"]

router = Router()

nowstr = time.strftime("%Y-%m-%d_%H%M")
basedir = protect_for_filename(f"{device}_{nowstr}")

try:
    os.mkdir(basedir)
except FileExistsError as e:
    print(f"Output directory '{basedir}' already exists. Wait a minute and try again.")
    exit(1)


class DownScan(DownPassController):
    def always_fail(self, run):
        return self.current_target < 10

    def __init__(self, run_collector: RunCollector, router: Router, device, test, tunnel, destdir, logname,
                 factor=0.7, start_at=380):
        super().__init__(run_collector, router, device, test, tunnel, destdir, logname, factor, start_at)
        self.run_successful_test = self.always_fail
        self.target_failure_requires = 1
        self.target_success_requires = 1


for tunnel in tunnels:

    destdir = os.path.join(basedir,
                           protect_for_filename(tunnel or "None"))

    try:
        os.mkdir(destdir)
    except FileExistsError as e:
        pass

    for test in tests:

        rc_sqm = RunCollector(device=device, tunnel=tunnel, test=test)
        down_pass = DownScan(run_collector=rc_sqm,
                             router=router, device=device, test=test, tunnel=tunnel,
                             destdir=destdir, logname=f"{destdir}/{test}_sqm.log")

        down_pass.start()

