"""
    Timer class to monitor/measure the computation, network send/receive, and idle time in the clients and
    the aggregation time in the server as well as Counter class to monitor network send/receive traffic

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

import logging
logger = logging.getLogger(__name__)


class Timer:
    """
        A class to measure the different constituents of the runtime
        (i.e. computation, network send, network receive, idle, and aggregation). Timer is additive, i.e. it keep tracks
        the sum of the statistics up to the PREVIOUS communication round because network send time up to
        the current round cannot be computed in the current round. new_round() function is called at the beginning of
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
        """ reset timer values """
        self.total_duration = 0.0
        self.this_round_duration = 0.0
        self.in_progress = False

    def start(self):
        """ Start timer """

        if self.in_progress:
            logger.error(f"{self.name} timer already started! It must be stopped first! Check the code to find the bug!")
            return

        self.in_progress = True
        self.start_time = time.time()

    def stop(self):
        """ Stop timer """

        if not self.in_progress:
            logger.error(f"{self.name} timer already stopped! It must be started first! Check the code to find the bug!")
            return

        self.this_round_duration += (time.time() - self.start_time)
        self.in_progress = False

    def new_round(self):
        """
            Update total statistics in the new round
        """
        self.total_duration += self.this_round_duration
        self.this_round_duration = 0.0

    def get_total_duration(self):
        """ Get total duration of the timer up to the previous communication round """
        return self.total_duration


class Counter:
    """ A class to count the traffic (in terms of bytes) sent/received to/from the clients """

    def __init__(self, name):
        self.name = name

        self.total_count = 0

    def increment(self, value):
        """ Increase total_count by value """
        self.total_count += value

    def get_total_count(self):
        """ Return total count (in string) in human readable format """

        kilo = 1024
        mega = kilo * kilo
        giga = mega * kilo
        tera = giga * kilo

        if self.total_count < 999:
            return f'{self.total_count} Bytes'

        if self.total_count < kilo * 999:
            return f'{self.total_count / kilo:.2f} KB'

        if self.total_count < mega * 999:
            return f'{self.total_count / mega:.2f} MB'

        if self.total_count < giga * 999:
            return f'{self.total_count / giga:.2f} GB'

        if self.total_count < tera * 999:
            return f'{self.total_count / tera:.2f} TB'

        return -1


