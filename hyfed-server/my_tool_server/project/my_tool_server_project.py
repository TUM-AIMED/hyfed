"""
    server-side MyTool project to aggregate the local parameters from the clients

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

from hyfed_server.project.hyfed_server_project import HyFedServerProject
from hyfed_server.util.hyfed_steps import HyFedProjectStep
from hyfed_server.util.status import ProjectStatus
from hyfed_server.util.utils import client_parameters_to_list

from my_tool_server.util.my_tool_steps import MyToolProjectStep
from my_tool_server.util.my_tool_parameters import MyToolGlobalParameter, MyToolLocalParameter,\
    MyToolProjectParameter


import logging
logger = logging.getLogger(__name__)


class MyToolServerProject(HyFedServerProject):
    """ Server side of MyTool project """

    def __init__(self, creation_request, project_model):
        """ Initialize MyTool project attributes based on the values set by the coordinator """

        # initialize base project
        super().__init__(creation_request, project_model)

        try:
            pass

        except Exception as model_exp:
            logger.error(model_exp)
            self.project_failed()

    # ############### Project step functions ####################
    def init_step(self):
        """ initialize MyTool server project """

        try:
            self.prepare_results()

            self.set_step(HyFedProjectStep.RESULT)

        except Exception as init_exception:
            logger.error(f'Project {self.project_id}: {init_exception}')
            self.project_failed()

    def prepare_results(self):
        """ Prepare result files for MyTool project """

        try:
            self.create_result_dir()

        except Exception as io_error:
            logger.error(f"Result file write error: {io_error}")
            self.project_failed()

    # ##############  MyTool specific aggregation code
    def aggregate(self):
        """ OVERRIDDEN: perform MyTool project specific aggregations """

        # The following four lines MUST always be called before the aggregation starts
        super().pre_aggregate()
        if self.status != ProjectStatus.AGGREGATING:  # if project failed or aborted, skip aggregation
            super().post_aggregate()
            return

        logger.info(f'Project {self.project_id}: ############## aggregate ####### ')
        logger.info(f'Project {self.project_id}: #### step {self.step}')

        if self.step == HyFedProjectStep.INIT:  # The first step name MUST always be HyFedProjectStep.INIT
            self.init_step()

        elif self.step == HyFedProjectStep.RESULT:
            super().result_step()

        # The following line MUST be the last function call in the aggregate function
        super().post_aggregate()
