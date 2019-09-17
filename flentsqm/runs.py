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

import re
import subprocess
import time

from flentsqm.router import Router
from flentsqm.stats import mean, stddev, coefvar


class FlentRun:

    def __init__(self, flent_output_string, target=None):
        self._flent_output_string = flent_output_string

        self._test = None
        self._title = None
        self._data_file = None
        self._ping = None
        self._avg_download = None
        self._avg_upload = None
        self._sum_download = None
        self._sum_upload = None
        self._totals = None
        self._download_data = []
        self._upload_data = []

        self.target = target
        self.marked_good = None
        self.marked_bad = None
        self.marked_selected = None

        self._re_data_file = re.compile("Data file written to (.+)\.")
        self._re_title = re.compile("  Title: '(.*)'")
        self._re_test = re.compile("Summary of (.*) test")

        self._re_ping = re.compile(" Ping \(ms\) ICMP[ :]+[0-9]+\.[0-9]+ +([0-9]+\.[0-9]+)")

        self._re_avg_download = re.compile(" TCP download avg[ :]+([0-9]+\.[0-9]+)")
        self._re_sum_download = re.compile(" TCP download sum[ :]+([0-9]+\.[0-9]+)")

        self._re_data_download = re.compile(" TCP download.* : +([0-9]+\.[0-9]+)")

        self._re_avg_upload = re.compile(" TCP upload avg[ :]+([0-9]+\.[0-9]+)")
        self._re_sum_upload = re.compile(" TCP upload sum[ :]+([0-9]+\.[0-9]+)")

        self._re_data_upload = re.compile(" TCP upload.* : +([0-9]+\.[0-9]+)")

        self._re_totals = re.compile(" TCP totals.* : +([0-9]+\.[0-9]+)")

        self.parse()

    def parse(self):

        for line in self._flent_output_string.splitlines():

            m = self._re_data_file.match(line)
            if m:
                self._data_file = m.group(1)
                continue

            m = self._re_title.match(line)
            if m:
                self._title = m.group(1)
                continue

            m = self._re_test.match(line)
            if m:
                self._test = m.group(1)
                continue

            m = self._re_ping.match(line)
            if m:
                self._ping = float(m.group(1))
                continue

            m = self._re_avg_download.match(line)
            if m:
                self._avg_download = float(m.group(1))
                continue

            m = self._re_sum_download.match(line)
            if m:
                self._sum_download = float(m.group(1))
                continue

            m = self._re_avg_upload.match(line)
            if m:
                self._avg_upload = float(m.group(1))
                continue

            m = self._re_sum_upload.match(line)
            if m:
                self._sum_upload = float(m.group(1))
                continue

            m = self._re_data_download.match(line)
            if m:
                self._download_data.append(float(m.group(1)))
                continue

            m = self._re_data_upload.match(line)
            if m:
                self._upload_data.append(float(m.group(1)))
                continue

            m = self._re_totals.match(line)
            if m:
                self._totals = float(m.group(1))
                continue

    @property
    def data_file(self):
        return self._data_file

    @property
    def test(self):
        return self._test

    @property
    def title(self):
        return self._title

    @property
    def ping(self):
        return self._ping

    @property
    def download(self):
        return self._sum_download

    @property
    def upload(self):
        return self._sum_upload

    @property
    def totals(self):
        if self._totals is not None:
            totals = self._totals
        else:
            totals = 0
            try:
                totals += self._sum_download
            except TypeError:
                pass
            try:
                totals += self._sum_upload
            except TypeError:
                pass
        return totals

    @property
    def mean_download(self):
        return mean(self._download_data)

    @property
    def mean_upload(self):
        return mean(self._upload_data)

    @property
    def mean_both(self):
        both = self._upload_data.copy()
        both.extend(self._download_data)
        return mean(both)

    @property
    def stddev_download(self):
        return stddev(self._download_data)

    @property
    def stddev_upload(self):
        return stddev(self._upload_data)

    @property
    def stddev_both(self):
        both = self._upload_data.copy()
        both.extend(self._download_data)
        x = stddev(both)
        if x is None:
            print(self.__dict__)
        return stddev(both)

    @property
    def coefvar_download(self):
        return coefvar(self._download_data)

    @property
    def coefvar_upload(self):
        return coefvar(self._upload_data)

    @property
    def coefvar_both(self):
        both = self._upload_data.copy()
        both.extend(self._download_data)
        return coefvar(both)

    @property
    def flent_output_string(self):
        return self._flent_output_string


class RunCollector:

    def __init__(self, device=None, tunnel=None, test=None):
        self._device = device
        self._tunnel = tunnel
        self._test = test
        self.runs = []

        self.sqm_fractional_threshold = 20

    def add(self, run):
        if not isinstance(run, FlentRun):
            raise TypeError(f"Can only add a FlentRun, not a {type(run)}")
        self.runs.append(run)
        return run

    @property
    def selected_runs(self):
        selected = []
        for run in self.runs:
            if run.marked_selected:
                selected.append(run)
        return selected

    def dump_one(self, run: FlentRun, with_output_filename=True):
        this_output = ''
        if run.marked_bad:
            this_output += " x"
        elif run.marked_selected:
            this_output += "=>"
        else:
            this_output += "  "
        this_output += f"{run.totals:7.2f} Mbps  {run.ping:6.2f} ms  "
        this_output += f"{run.coefvar_both * 100:6.2f} %   "
        for try_cov in (run.coefvar_download, run.coefvar_upload):
            if try_cov is not None:
                this_output += f"{try_cov * 100:6.2f} % "
            else:
                this_output += f"{'':6s}  "
        # TODO: Any option better than this hack?
        if run.target is None:
            this_output += "      None "
        elif run.target < self.sqm_fractional_threshold:
            this_output += f"{run.target:6.1f} Mbps"
        else:
            this_output += f"{run.target:6d} Mbps"
        this_output += f"    {run.stddev_both:.4f}"
        if with_output_filename:
            this_output += f"\t{run.data_file}"
        this_output += "\n"

        return this_output

    def dump_header(self):
        this_output = f"{self._device} {self._tunnel} {self._test}\n"
        this_output += "    Total          Ping       CoV        down     up        Target     sigma"
        this_output += "\n"

        return this_output

    def dump(self, sort=None, with_output_filename=True):
        this_output = self.dump_header()
        if sort:
            the_runs = sorted(self.runs, key=sort)
        else:
            the_runs = self.runs
        for run in the_runs:
            this_output += self.dump_one(run, with_output_filename=with_output_filename)

        return this_output


def execute_one_test(router: Router, sqm, dest_dir, host, test, title='', note=''):

    if sqm is not None:
        router.sqm_set_targets(int(sqm*1000), int(sqm*1000))
    else:
        router.sqm_enable(yes=False)
    router.sqm_restart(True)

    print(f"Starting test: {note}")

    sp = subprocess.run(["flent", "-D", dest_dir, "-t", title, "-n", f'"{note}"',
                         "-x", "-H", host, test],
                        capture_output=True)

    if sp.returncode or (sp.stderr and sp.stderr != b''):
        nowstr = time.strftime("%Y-%m-%d_%H%M%S")
        print(f"flent returned {sp.returncode}")
        print(f"args: {sp.args}")
        print(f"stderr:\n{sp.stderr.decode('utf-8')}")
        with open(f"{dest_dir}/{nowstr}.err", 'w') as errfile:
            print(f"flent returned {sp.returncode}", file=errfile)
            print(f"args: {sp.args}", file=errfile)
            print(f"stderr:\n{sp.stderr.decode('utf-8')}", file=errfile)
            print(f"stdout:\n{sp.stdout.decode('utf-8')}", file=errfile)

    run = FlentRun(sp.stdout.decode('utf-8'), target=sqm)

    return run
