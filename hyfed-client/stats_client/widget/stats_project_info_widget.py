"""
    A widget to add Stats specific project info

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

from hyfed_client.widget.hyfed_project_info_widget import HyFedProjectInfoWidget
from hyfed_client.util.gui import add_label_and_textbox
from hyfed_client.util.hyfed_parameters import HyFedProjectParameter
from stats_client.util.stats_parameters import StatsProjectParameter
from stats_client.util.stats_algorithms import StatsAlgorithm


class StatsProjectInfoWidget(HyFedProjectInfoWidget):
    def __init__(self, title, connection_parameters, authentication_parameters):

        super().__init__(title=title, connection_parameters=connection_parameters,
                         authentication_parameters=authentication_parameters)

    # Stats project specific info
    def add_stats_project_info(self):
        add_label_and_textbox(self, label_text="Features",
                              value=self.project_parameters[StatsProjectParameter.FEATURES], status='disabled')

        if self.project_parameters[HyFedProjectParameter.ALGORITHM] == StatsAlgorithm.LOGISTIC_REGRESSION:
            add_label_and_textbox(self, label_text="Learning rate",
                                  value=self.project_parameters[StatsProjectParameter.LEARNING_RATE], status='disabled')

            add_label_and_textbox(self, label_text="Max iterations",
                                  value=self.project_parameters[StatsProjectParameter.MAX_ITERATIONS], status='disabled')
