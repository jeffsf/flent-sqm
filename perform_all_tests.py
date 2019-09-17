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

from flentsqm.controller import DownPassController, UpPassController, MultiRunController
from flentsqm.naming import protect_for_filename
from flentsqm.runs import RunCollector
from flentsqm.router import Router

try:
    device = sys.argv[1]
except IndexError:
    print(f"Usage: {sys.argv[0]} 'Device Name'")
    exit(1)

tunnels = [None, "WireGuard", "OpenVPN"]
tests = ["tcp_8down", "tcp_8up", "rrul"]

start_at = 2000
router = Router()

nowstr = time.strftime("%Y-%m-%d_%H%M")
basedir = protect_for_filename(f"{device}_{nowstr}")

try:
    os.mkdir(basedir)
except FileExistsError as e:
    print(f"Output directory '{basedir}' already exists. Wait a minute and try again.")
    exit(1)

for tunnel in tunnels:

    destdir = os.path.join(basedir,
                           protect_for_filename(tunnel or "None"))

    try:
        os.mkdir(destdir)
    except FileExistsError as e:
        pass

    for test in tests:

        rc = RunCollector(device=device, tunnel=tunnel, test=test)
        median_pass = MultiRunController(run_collector=rc,
                                         router=router, device=device, test=test, tunnel=tunnel,
                                         destdir=destdir, logname=f"{destdir}/{test}.log", sqm=None)
        median_pass.start()

        start_next = int(rc.selected_runs[-1].totals * 2)

        rc_sqm = RunCollector(device=device, tunnel=tunnel, test=test)
        down_pass = DownPassController(run_collector=rc_sqm,
                                       router=router, device=device, test=test, tunnel=tunnel,
                                       destdir=destdir, logname=f"{destdir}/{test}_sqm.log",
                                       start_at=start_next)
        down_pass.start()

        start_next = rc_sqm.selected_runs[-1].target

        up_pass1 = UpPassController(run_collector=rc_sqm,
                                    router=router, device=device, test=test, tunnel=tunnel,
                                    destdir=destdir, logname=f"{destdir}/{test}_sqm.log",
                                    factor=1.15, start_at=start_next)
        up_pass1.start()

        start_next = rc_sqm.selected_runs[-1].target

        up_pass2 = UpPassController(run_collector=rc_sqm,
                                    router=router, device=device, test=test, tunnel=tunnel,
                                    destdir=destdir, logname=f"{destdir}/{test}_sqm.log",
                                    factor=1.05, start_at=start_next)
        up_pass2.start()

        ping_limit = 10
        if rc_sqm.selected_runs[-1].ping > ping_limit:
            start_next = rc_sqm.selected_runs[-1].target

            ping_pass = DownPassController(run_collector=rc_sqm,
                                           router = router, device = device, test = test, tunnel = tunnel,
                                           destdir=destdir, logname=f"{destdir}/{test}_sqm.log",
                                           factor=0.95, start_at=start_next)
            ping_pass.ping_limit = ping_limit
            ping_pass.target_failure_requires = 2

            ping_pass.start()
