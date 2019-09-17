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

import math
import sys

from flentsqm.runs import RunCollector, FlentRun, execute_one_test
from flentsqm.router import Router
from flentsqm.naming import protect_for_filename

###
### TODO: Handle failed flent run (more than logging error?)
###
### TODO: Up pass not morking selected on first run?
# Data file written to EA8300_no_irqbalance_None_2019-09-13_0643/tcp_8down-2019-09-13T065656.371916.EA8300_no_irqbalance_None_SQM_1933_1933.flent.gz.
#
# Summary of tcp_8down test run from 2019-09-13 13:56:56.371916
#   Title: 'EA8300_no_irqbalance_None_SQM_1933_1933'
#
#                              avg       median          # data pts
#  Ping (ms) ICMP   :         3.07         3.04 ms              349
#  TCP download avg :        27.13        27.19 Mbits/s         301
#  TCP download sum :       217.00       217.50 Mbits/s         301
#  TCP download::1  :        27.11        27.16 Mbits/s         299
#  TCP download::2  :        27.17        27.16 Mbits/s         299
#  TCP download::3  :        27.12        27.17 Mbits/s         299
#  TCP download::4  :        27.11        27.16 Mbits/s         299
#  TCP download::5  :        27.12        27.16 Mbits/s         299
#  TCP download::6  :        27.11        27.17 Mbits/s         299
#  TCP download::7  :        27.11        27.16 Mbits/s         299
#  TCP download::8  :        27.11        27.16 Mbits/s         299
#
# EA8300 no irqbalance None tcp_8down
#     Total          Ping       CoV        down     up        Target     sigma
#    216.49 Mbps    3.09 ms    0.06 %     0.06 %           1841 Mbps    0.0151
# => 216.64 Mbps    3.09 ms    0.00 %     0.00 %           1841 Mbps    0.0000
#    216.14 Mbps    3.16 ms    0.01 %     0.01 %           2117 Mbps    0.0035
#    215.87 Mbps    3.13 ms    0.07 %     0.07 %           2117 Mbps    0.0200
#    217.75 Mbps    3.02 ms    0.02 %     0.02 %           1933 Mbps    0.0053
#    217.00 Mbps    3.04 ms    0.08 %     0.08 %           1933 Mbps    0.0207
#
# SQM: Stopping SQM on eth1

###


class PassController:

    def _default_test_run_successful(self, run: FlentRun):
        var_ok = (run.coefvar_both < 0.01) or (run.stddev_both < 0.02)
        ###
        ### TODO: Handle misbehaving SQM better?
        ###
        sqm_fudge_factor = 0.7
        if self.current_target:
            if run.download and run.download < self.current_target * sqm_fudge_factor:
                return False
            if run.upload and run.upload < self.current_target * sqm_fudge_factor:
                return False
        if self.ping_limit:
            return var_ok and run.ping < self.ping_limit
        else:
            return var_ok

    def _default_test_run_no_progress(self, run: FlentRun):
        return False

    def _default_create_sqm_string(self, sqm):
        if sqm and sqm >= self.sqm_fractional_threshold:
            sqmf = f"{sqm}"
        elif sqm:
            sqmf = f"{sqm:0.1f}"
        else:
            sqmf = "None"
        return sqmf

    def _default_create_title(self):
        sqmf = self.create_sqm_string(self.current_target)
        return protect_for_filename(f"{self.device}_{self.tunnel}_SQM_{sqmf}_{sqmf}")

    def _default_create_note(self):
        sqmf = self.create_sqm_string(self.current_target)
        return f"{self.device} {self.tunnel} {self.test} {sqmf}/{sqmf}"

    def _default_prepare_sqm(self):
        self.router.sqm_set_params(interface=self.iface, overhead=self.overhead)
        self.router.sqm_enable(yes=(self.current_target is not None), print_output=True)

    def _default_after_run(self, run):
        print(run.flent_output_string)

    def _default_dump(self):
        print(self.collected.dump(with_output_filename=False))
        if self.logname:
            with open(self.logname, mode='w') as logfile:
                print(self.collected.dump(), file=logfile)

    def _default_before_continue(self):
        self._default_dump()

    def __init__(self, run_collector: RunCollector, router: Router, device, test, tunnel, destdir, logname):
        self.collected = run_collector
        self.router = router
        self.device = device
        self.test = test
        self.tunnel = tunnel
        self.destdir = destdir
        self.logname = logname

        self.host = None
        self.iface = None
        self.overhead = None

        self.ping_limit = None

        self.run_successful_test = self._default_test_run_successful
        self.no_progress_test = self._default_test_run_no_progress

        self.create_sqm_string = self._default_create_sqm_string
        self.create_title = self._default_create_title
        self.create_note = self._default_create_note

        self.prepare_sqm = self._default_prepare_sqm
        self.after_run = self._default_after_run
        self.before_continue = self._default_before_continue

        self.pass_started = False
        self.pass_complete = False

        self.sqm_fractional_threshold = 20
        self.sqm_fractional_increment = 0.1

        self.highest_successful_run = None
        self.current_target = None


        if self.tunnel is None or self.tunnel.lower() == "none":
            self.tunnel = None
            self.host = '10.0.0.2'
            self.iface = router.run_cmd("uci get network.wan.ifname").stdout.decode('utf-8').strip()
            if not self.iface:
                print("No interface for wan returned. Exiting")
                exit(1)
            self.overhead = 22

        elif self.tunnel.lower() == "wireguard":
            self.tunnel = "WireGuard"
            self.host = "172.16.0.2"
            self.iface = "wg0"
            self.overhead = 82

        elif self.tunnel.lower() == "openvpn":
            self.tunnel = "OpenVPN"
            self.host = "172.16.1.2"
            self.iface = "tun0"
            self.overhead = 95

        else:
            print(f"Unrecognized tunnel: '{tunnel}'. Exiting")
            exit(2)

    def start(self):
        raise NotImplementedError


class DownPassController(PassController):

    def __init__(self, run_collector: RunCollector, router: Router, device, test, tunnel, destdir, logname,
                 factor=0.7, start_at=1024):
        super().__init__(run_collector, router, device, test, tunnel, destdir, logname)
        self.factor = factor
        self.start_at = start_at

        self.target_success_requires = 2
        self.target_failure_requires = 1

        self.sqm_lower_limit = 1

    def start(self):
        self.current_target = self.start_at
        self.prepare_sqm()

        done = False
        found_success = False

        count_failures = 0
        count_successes = 0

        while not done:

            this_run = execute_one_test(router=self.router,
                                        sqm=self.current_target,
                                        dest_dir = self.destdir,
                                        host = self.host,
                                        test = self.test,
                                        title = self.create_title(),
                                        note = self.create_note(),
                                        )

            self.after_run(this_run)

            run_successful = self.run_successful_test(this_run)
            no_progress = self.no_progress_test(this_run)

            cr = self.collected.add(this_run)

            if run_successful:
                count_successes += 1
                cr.marked_good = True
            else:
                count_failures += 1
                cr.marked_bad = True

            # Typical condition where additional runs are required
            if count_successes < self.target_success_requires and count_failures < self.target_failure_requires:
                self.before_continue()
                continue

            # Success at this SQM target
            if count_successes >= self.target_success_requires:
                if not found_success:
                    found_success = True
                    cr.marked_selected = True
                    self.highest_successful_run = self.collected.runs[-1]

            # Failure at this SQM target
            if count_failures >= self.target_failure_requires:
                pass  # Well, not really, more below

            if found_success:
                done = True
                self.before_continue()
                continue

            # Set up next target

            if self.current_target > 20:
                next_target = self.current_target * self.factor
            else:    # "Slow" devices failed to find a suitable target for RRUL
                next_target = self.current_target * math.sqrt(self.factor)
            if next_target < self.sqm_fractional_threshold:
                increment = self.sqm_fractional_increment
            else:
                increment = 1
            next_target = round(next_target/increment) * increment
            if next_target == self.current_target:
                next_target = self.current_target - increment
            if next_target < self.sqm_lower_limit:
                done = True
                self.before_continue()
                continue
            self.current_target = next_target
            count_failures = 0
            count_successes = 0
            self.before_continue()
            continue

        return self.highest_successful_run


###
### TODO: What about the non-improvement case?
###         tcp_8down, None, EA8300


class UpPassController(PassController):

    def __init__(self, run_collector: RunCollector, router: Router, device, test, tunnel, destdir, logname,
                 factor, start_at):
        super().__init__(run_collector, router, device, test, tunnel, destdir, logname)
        self.factor = factor
        self.start_at = start_at

        self.target_success_requires = 2
        self.target_failure_requires = 2

        self.sqm_upper_limit = 2000

    def start(self):
        self.current_target = self.start_at
        self.prepare_sqm()

        done = False
        found_success = False

        count_failures = 0
        count_successes = 0

        while not done:

            this_run = execute_one_test(router=self.router,
                                        sqm=self.current_target,
                                        dest_dir = self.destdir,
                                        host = self.host,
                                        test = self.test,
                                        title = self.create_title(),
                                        note = self.create_note(),
                                        )

            self.after_run(this_run)

            run_successful = self.run_successful_test(this_run)
            no_progress = self.no_progress_test(this_run)

            cr = self.collected.add(this_run)

            if run_successful:
                count_successes += 1
                cr.marked_good = True
            else:
                count_failures += 1
                cr.marked_bad = True

            # Typical condition where additional runs are required
            if count_successes < self.target_success_requires and count_failures < self.target_failure_requires:
                self.before_continue()
                continue

            # Success at this SQM target
            if count_successes >= self.target_success_requires:
                self.highest_successful_run = self.collected.runs[-1]


            # Failure at this SQM target
            if count_failures >= self.target_failure_requires:
                if self.highest_successful_run:
                    self.highest_successful_run.marked_selected = True
                    done = True
                    self.before_continue()
                    continue
                else:
                    # Need to back off and try again
                    self.current_target = self.current_target / (self.factor**5)  # **4 would be 3 steps back

            # Set up next target

            next_target = self.current_target * self.factor
            if next_target < self.sqm_fractional_threshold:
                increment = self.sqm_fractional_increment
            else:
                increment = 1
            next_target = round(next_target/increment) * increment
            if next_target == self.current_target:
                next_target = self.current_target + increment
            if next_target > self.sqm_upper_limit:
                done = True
                self.before_continue()
                continue
            self.current_target = next_target
            count_failures = 0
            count_successes = 0
            self.before_continue()
            continue

        return self.highest_successful_run


class MultiRunController(PassController):

    def __init__(self, run_collector: RunCollector, router: Router, device, test, tunnel, destdir, logname,
                 runs=5, sqm=None):
        super().__init__(run_collector, router, device, test, tunnel, destdir, logname)
        self.runs = runs
        self.sqm = sqm
        if (int(runs) != runs) or (runs % 2 != 1):
            new_runs = int(runs)
            if (runs % 2 != 1):
                runs += 1
            print(f"runs={runs} not an odd integer. Changed to {new_runs}.", file=sys.stderr)

    def start(self):
        self.current_target = self.sqm
        self.prepare_sqm()

        for run in range(self.runs):
            this_run = execute_one_test(router=self.router,
                                        sqm=self.current_target,
                                        dest_dir = self.destdir,
                                        host = self.host,
                                        test = self.test,
                                        title = self.create_title(),
                                        note = self.create_note(),
                                        )

            self.after_run(this_run)
            cr = self.collected.add(this_run)

        median_index = int(self.runs / 2)
        by_totals = lambda run: run.totals
        sorted_runs = sorted(self.collected.runs, key=by_totals)
        sorted_runs[median_index].marked_selected = True
        print(self.collected.dump(sort=by_totals, with_output_filename=False))
        if self.logname:
            with open(self.logname, mode='w') as logfile:
                print(self.collected.dump(sort=by_totals), file=logfile)

        return sorted_runs[median_index]