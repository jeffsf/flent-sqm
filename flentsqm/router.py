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

import subprocess


class Router:
    
    def __init__(self, ip="192.168.1.1", user="root"):
        self._ip = ip
        self._user = user
        
    def run_cmd(self, cmd, print_output=False):
        if isinstance(cmd, str):
            cmd = cmd.split()
        sp = subprocess.run(["ssh", f"{self._user}@{self._ip}"] + cmd, capture_output=True)
        if sp.stderr:
            print(sp.stderr.decode('utf-8'))
        if print_output:
            print(sp.stdout.decode('utf-8'))
        return sp
    
    def sqm_show(self, print_output=True):
        self.run_cmd("uci show sqm", print_output)

    def sqm_restart(self, print_output=False):
        self.run_cmd("/etc/init.d/sqm restart", print_output)

    def sqm_enable(self, yes=True, print_output=False):
        if yes:
            state = 1
        else:
            state = 0
        self.run_cmd(f"uci set sqm.test.enabled='{state}'")
        self.run_cmd("uci commit")
        self.sqm_restart(print_output)

    def sqm_set_params(self, interface, overhead):
        self.run_cmd(f"uci set sqm.test.interface='{interface}'")
        self.run_cmd(f"uci set sqm.test.overhead='{overhead}'")
        self.run_cmd("uci commit")

    def sqm_set_targets(self, download, upload):
        self.run_cmd(f"uci set sqm.test.download='{download}'")
        self.run_cmd(f"uci set sqm.test.upload='{upload}'")
        self.run_cmd("uci commit")
