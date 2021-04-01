"""
    server-side TickTock project to aggregate the local parameters from the clients

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

from hyfed_server.project.hyfed_server_project import HyFedServerProject
from hyfed_server.util.hyfed_steps import HyFedProjectStep
from hyfed_server.util.status import ProjectStatus
from hyfed_server.models import UserModel
from hyfed_server.model.hyfed_models import TimerModel, TrafficModel
from tick_tock_server.util.tick_tock_steps import TickTockProjectStep
from tick_tock_server.model.tick_tock_model import TickTockProjectModel
from hyfed_server.util.hyfed_parameters import HyFedProjectParameter
from tick_tock_server.util.tick_tock_parameters import TickTockGlobalParameter, TickTockLocalParameter,\
    TickTockProjectParameter
from hyfed_server.util.utils import client_parameters_to_list


import hashlib
import numpy as np

import logging
logger = logging.getLogger(__name__)


class TickTockServerProject(HyFedServerProject):
    """ A toy project to show the capabilities of the HyFed framework """

    def __init__(self, creation_request, project_model):
        """ Initialize TickTock project attributes based on the values set by the coordinator """

        # initialize base project
        super().__init__(creation_request, project_model)

        try:

            # extract/initialize TickTock specific project parameters (i.e. initial tic)
            initial_tic = creation_request.data[TickTockProjectParameter.INITIAL_TIC]
            result_dir = "tick_tock_server/result"

            tick_tock_model_instance = project_model.objects.get(id=self.project_id)
            tick_tock_model_instance.initial_tic = initial_tic
            tick_tock_model_instance.result_dir = result_dir
            tick_tock_model_instance.save()

            # initialize TickTock project specific attributes
            self.initial_tic = initial_tic
            self.result_dir = result_dir

            logger.debug(f"Project {self.project_id}: TickTock specific attributes initialized!")

            self.global_tics = []  # final results

        except Exception as model_exp:
            logger.error(model_exp)
            self.project_failed()

    # ############### Project step functions ####################
    def init_step(self):
        """ Compute hex digest of the initial tic and set it as the value of the global parameter """

        try:
            # initialize global model parameter (i.e. global tic) for the next step
            initialized_global_tic = hashlib.sha256(self.initial_tic.encode('utf-8')).hexdigest()
            self.global_parameters[TickTockGlobalParameter.TIC] = initialized_global_tic

            # tell clients to go to the TicToc step
            self.set_step(TickTockProjectStep.TIC_TOC)

            # put computed tic in the result variable
            self.global_tics.append(initialized_global_tic)

        except Exception as init_exception:
            logger.error(f'Project {self.project_id}: {init_exception}')
            self.project_failed()

    def tic_toc_step(self):
        """ aggregate the local parameter (i.e. local tocs) from the clients """

        try:
            # convert local tocs from dictionary to a list
            local_tocs = client_parameters_to_list(self.local_parameters, TickTockLocalParameter.TOC)

            # compute the sum of the local tocs
            sum_local_tocs = np.sum(local_tocs)

            # global tic is the hex digest of the sum of the local tocs
            global_tic = hashlib.sha256(str(sum_local_tocs).encode('utf-8')).hexdigest()

            # set the value of the global parameter to computed global_tick
            self.global_parameters[TickTockGlobalParameter.TIC] = global_tic

            # append the computed global tic to the result variable
            self.global_tics.append(global_tic)

            # TickTockProjectStep.TIC_TOC step is last COMPUTATIONAL step,
            # so prepare the final results first, and then, go to HyFedProjectStep.RESULT step
            self.prepare_results()

            # tell clients to go to the next step
            self.set_step(HyFedProjectStep.RESULT)

        except Exception as exp:
            logger.error(f'Project {self.project_id}: {exp}')
            self.project_failed()

    def prepare_results(self):
        """ Prepare result files for TickTock project """

        try:
            # create TickTock project result directory
            project_result_dir = self.create_result_dir()

            # Open TickTock result file
            tick_tock_result_file = open(f'{project_result_dir}/tick-tock-result.csv', 'w')

            # write TickTock results to the file
            tick_tock_result_file.write('communication_round,tic_value')
            for comm_round in range(0, len(self.global_tics)):
                tick_tock_result_file.write(f'\n{comm_round + 1},{self.global_tics[comm_round]}')

            # close result file
            tick_tock_result_file.close()

        except Exception as io_error:
            logger.error(f"Result file write error: {io_error}")
            self.project_failed()

    # ##############  TickTock specific aggregation code
    def aggregate(self):
        """ OVERRIDDEN: perform TickTock project specific aggregations """

        # The following four lines MUST always be called before the aggregation starts
        super().pre_aggregate()
        if self.status != ProjectStatus.AGGREGATING:  # if project failed or aborted, skip aggregation
            super().post_aggregate()
            return

        logger.info(f'Project {self.project_id}: ############## aggregate ####### ')
        logger.info(f'Project {self.project_id}: #### step {self.step}')

        if self.step == HyFedProjectStep.INIT:  # The first step name MUST always be HyFedProjectStep.INIT
            self.init_step()

        elif self.step == TickTockProjectStep.TIC_TOC:
            self.tic_toc_step()

        #  HyFedProjectStep.RESULT is the last step that needs implementation
        # The last step is HyFedProjectStep.FINISHED but it has not corresponding step function;
        elif self.step == HyFedProjectStep.RESULT:
            super().result_step()

        # The following line MUST be the last function call in the aggregate function
        super().post_aggregate()
