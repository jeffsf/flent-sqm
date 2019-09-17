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
import re
import sys

try:
    basedir = sys.argv[1]
except IndexError:
    basedir = None


tunnels = ["None", "WireGuard", "OpenVPN"]
lognames = [
    "tcp_8down.log",
    "tcp_8up.log",
    "rrul.log",
    "tcp_8down_sqm.log",
    "tcp_8up_sqm.log",
    "rrul_sqm.log",
             ]

re_get_throughput = re.compile("^.*?([0-9.]+) Mbps.*?([0-9.]+) Mbps")

for tunnel in tunnels:
    for logname in lognames:
        filename = os.path.join(tunnel, logname)
        if basedir:
            filename = os.path.join(basedir, filename)
        try:
            with open(filename, 'r') as log:
                print(f"{filename}\n")
                runs = []
                for line in log:
                    match = re_get_throughput.match(line)
                    if not match:
                        if line.find("\t") >= 0:
                            print(line.split("\t")[0])
                        else:
                            print(line, end='')
                    else:
                        runs.append({"throughput": match.group(1),
                                     "target": match.group(2),
                                     "line": line})

            runs.sort(key=lambda r: float(r["target"]))
            for run in runs:
                print(run["line"].split("\t")[0])

            print("\n")
        except FileNotFoundError:
            print(f"=====> Missing: {filename}")
