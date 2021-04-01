"""
    Client-side MyTool project to compute local parameters

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

from hyfed_client.project.hyfed_client_project import HyFedClientProject
from hyfed_client.util.hyfed_steps import HyFedProjectStep

from my_tool_client.util.my_tool_steps import MyToolProjectStep
from my_tool_client.util.my_tool_parameters import MyToolGlobalParameter, MyToolLocalParameter


class MyToolClientProject(HyFedClientProject):
    """
        A class that provides the computation functions to compute local parameters
    """

    def __init__(self, username, token, project_id, server_url,
                 algorithm, name, description, coordinator, result_dir, log_dir):

        super().__init__(username=username, token=token, project_id=project_id, server_url=server_url,
                         algorithm=algorithm, name=name, description=description, coordinator=coordinator,
                         result_dir=result_dir, log_dir=log_dir)

    # ########## MyTool step functions
    def init_step(self):
        # OPEN DATASET FILE(S) AND INITIALIZE THEIR CORRESPONDING DATASET ATTRIBUTES
        try:
            pass
        except Exception as io_exception:
            self.log(io_exception)
            self.set_operation_status_failed()

    def compute_local_parameters(self):
        """ OVERRIDDEN: Compute the local parameters in each step of the MyTool algorithms """

        try:

            super().pre_compute_local_parameters()  # MUST be called BEFORE step functions

            # ############## MyTool specific local parameter computation steps
            if self.project_step == HyFedProjectStep.INIT:
                self.init_step()
            elif self.project_step == HyFedProjectStep.RESULT:
                super().result_step()  # the result step downloads the result file as zip (it is algorithm-agnostic)
            elif self.project_step == HyFedProjectStep.FINISHED:
                super().finished_step()  # The operations in the last step of the project is algorithm-agnostic

            super().post_compute_local_parameters()  # # MUST be called AFTER step functions
        except Exception as computation_exception:
            self.log(computation_exception)
            super().post_compute_local_parameters()
            self.set_operation_status_failed()
