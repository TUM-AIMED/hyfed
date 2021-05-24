"""
    A widget to add MyTool specific project info

    Copyright 2021 'My Name'. All Rights Reserved.

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
from my_tool_client.util.my_tool_parameters import MyToolProjectParameter
from hyfed_client.util.hyfed_parameters import HyFedProjectParameter
from my_tool_client.util.my_tool_algorithms import MyToolAlgorithm


class MyToolProjectInfoWidget(HyFedProjectInfoWidget):
    def __init__(self, title, connection_parameters, authentication_parameters):

        super().__init__(title=title, connection_parameters=connection_parameters,
                         authentication_parameters=authentication_parameters)

    # MyTool project specific info
    def add_my_tool_project_info(self):
        pass
