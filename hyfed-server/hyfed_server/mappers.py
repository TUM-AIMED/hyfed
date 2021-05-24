"""
    Mapper to map an algorithm name to the corresponding server project, model, and serializer

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

# HyFed project
from hyfed_server.project.hyfed_server_project import HyFedServerProject
from hyfed_server.model.hyfed_models import HyFedProjectModel
from hyfed_server.serializer.hyfed_serializers import HyFedProjectSerializer

# MyTool project
from my_tool_server.project.my_tool_server_project import MyToolServerProject
from my_tool_server.model.my_tool_model import MyToolProjectModel
from my_tool_server.serializer.my_tool_serializers import MyToolProjectSerializer

# Stats project
from stats_server.project.stats_server_project import StatsServerProject
from stats_server.model.stats_model import StatsProjectModel
from stats_server.serializer.stats_serializers import StatsProjectSerializer

# server_project, project_model, and project_serializer are mappers used in webapp_view
server_project = dict()
project_model = dict()
project_serializer = dict()

# Stats tool mapper classes
stats_tool_name = 'Stats'
server_project[stats_tool_name] = StatsServerProject
project_model[stats_tool_name] = StatsProjectModel
project_serializer[stats_tool_name] = StatsProjectSerializer

# HyFed project mapper values
hyfed_tool = 'HyFed'
server_project[hyfed_tool] = HyFedServerProject
project_model[hyfed_tool] = HyFedProjectModel
project_serializer[hyfed_tool] = HyFedProjectSerializer

# MyTool project mapper values
my_tool_name = 'MyTool'
server_project[my_tool_name] = MyToolServerProject
project_model[my_tool_name] = MyToolProjectModel
project_serializer[my_tool_name] = MyToolProjectSerializer


