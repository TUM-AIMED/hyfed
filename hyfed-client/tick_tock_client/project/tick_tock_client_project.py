"""
    Client-side TickTock project to compute local parameters

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

from hyfed_client.project.hyfed_client_project import HyFedClientProject
from hyfed_client.util.hyfed_steps import HyFedProjectStep
from tick_tock_client.util.tick_tock_steps import TickTockProjectStep
from tick_tock_client.util.tick_tock_parameters import TickTockGlobalParameter, TickTockLocalParameter

import hashlib


class TickTockClientProject(HyFedClientProject):
    """
        A class that provides the computation functions to compute local parameters of Tiki-Taka algorithm in TicKTock
    """

    def __init__(self, username, token, project_id, server_url,
                 algorithm, name, description, coordinator, result_dir, log_dir,
                 tick_tock_dataset_file_path  # this argument is specific to TickTock project
                 ):

        super().__init__(username=username, token=token, project_id=project_id, server_url=server_url,
                         algorithm=algorithm, name=name, description=description, coordinator=coordinator,
                         result_dir=result_dir, log_dir=log_dir)

        self.tick_tock_dataset_file_path = tick_tock_dataset_file_path
        self.tick_tock_dataset_content = ''  # will be initialized in init_step function

    # ########## TickTock step functions
    def init_step(self):
        """ Open TickTock dataset file and read the content """

        try:
            text_file = open(self.tick_tock_dataset_file_path)

            self.tick_tock_dataset_content = text_file.read()

            text_file.close()
        except Exception as io_exception:
            self.log(io_exception)
            self.set_operation_status_failed()

    def tic_toc_step(self):
        """
            Compute the local toc parameter based on the global tic parameter from the server
            and the TickTock dataset content
        """

        try:
            # extract global parameter value from the server
            global_tic = self.global_parameters[TickTockGlobalParameter.TIC]

            # concatenate file content and global tic first, and then, compute the hash
            message = self.tick_tock_dataset_content + global_tic
            local_toc_digest = hashlib.sha256(message.encode('utf-8')).hexdigest()

            # local_toc is integer value of local_toc_digest value
            local_toc = int(local_toc_digest, 16)

            # put the computed parameter (i.e. local toc) in self.local_parameters
            self.local_parameters[TickTockLocalParameter.TOC] = local_toc
        except Exception as tic_toc_exception:
            self.log(tic_toc_exception)
            self.set_operation_status_failed()

    def compute_local_parameters(self):
        """ OVERRIDDEN: Compute the local parameters in each step of the Tiki-Taka algorithm """

        try:

            super().pre_compute_local_parameters()  # MUST be called BEFORE step functions

            # ############## TickTock specific local parameter computation steps
            if self.project_step == HyFedProjectStep.INIT:
                self.init_step()
            elif self.project_step == TickTockProjectStep.TIC_TOC:
                self.tic_toc_step()
            elif self.project_step == HyFedProjectStep.RESULT:
                super().result_step()  # the result step downloads the result file as zip (it is algorithm-agnostic)
            elif self.project_step == HyFedProjectStep.FINISHED:
                super().finished_step()  # The operations in the last step of the project is algorithm-agnostic

            super().post_compute_local_parameters()  # # MUST be called AFTER step functions
        except Exception as compute_exception:
            self.log(compute_exception)
            super().post_compute_local_parameters()
            self.set_operation_status_failed()
