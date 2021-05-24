"""
    A class to monitor/measure the computation, network send/receive, and idle time in the clients as well as
    the aggregation time in the server and compensation time in the compensator

    Copyright 2021 Reza NasiriGerdeh. All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

import time


class Timer:
    """
        A class to measure the different constituents of the runtime
        (i.e. computation, network send, network receive, idle, aggregation, and compensation). Timer is additive, i.e. it keep tracks
        the sum of the statistics up to the PREVIOUS communication round. This is because network send time up to
        the current round cannot be computed in the current round. new_round function is called at the beginning of
        each round to update the total duration of the timer up to the previous round.
    """

    def __init__(self, name):
        self.name = name
        self.start_time = 0.0

        self.total_duration = 0.0  # total duration up to the previous round
        self.this_round_duration = 0.0  # duration in the current round

        # ensure timers are not used improperly
        self.in_progress = False

    def reset(self):
        """ Reset timer values """

        self.total_duration = 0.0
        self.this_round_duration = 0.0
        self.in_progress = False

    def start(self):
        """ Start timer """

        if self.in_progress:
            print(f"{self.name} timer already started! It must be stopped first! Check the code to find the bug!")
            return

        self.in_progress = True
        self.start_time = time.time()

    def stop(self):
        """ Stop timer """

        if not self.in_progress:
            print(f"{self.name} timer already stopped! It must be started first! Check the code to find the bug!")
            return

        self.this_round_duration += (time.time() - self.start_time)
        self.in_progress = False

    def ignore(self):
        if not self.in_progress:
            print(f"{self.name} timer already stopped! It must be started first! Check the code to find the bug!")
            return

        self.in_progress = False

    def new_round(self):
        """ Update total statistics in the new round """

        self.total_duration += self.this_round_duration
        self.this_round_duration = 0.0

    def get_total_duration(self):
        """ Get total duration of the timer up to the previous communication round """

        return self.total_duration
