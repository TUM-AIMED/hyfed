"""
    Provides the base functionalities of the server including client synchronization and operation check,
    operations before and after aggregation, and etc.

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


from hyfed_server.util.status import ProjectStatus, OperationStatus
from hyfed_server.util.hyfed_parameters import Parameter, SyncParameter, MonitoringParameter
from hyfed_server.util.monitoring import Timer, Counter
from hyfed_server.model.hyfed_models import HyFedProjectModel, TimerModel, TrafficModel
from hyfed_server.util.utils import client_parameters_to_list
from hyfed_server.util.hyfed_steps import HyFedProjectStep
from hyfed_server.models import UserModel
from hyfed_server.util.hyfed_parameters import HyFedProjectParameter

from pathlib import Path
import copy
import os
import numpy as np
import time

import logging
logger = logging.getLogger(__name__)


class HyFedServerProject:
    """
        A base class that provides the essential functionalities of the server package
        including client sync check, pre/post-aggregation operation, result preparation, and etc.
        The local parameters of the clients in this and all derived classes are NEVER saved in a permanent storage.
        Only timer values, project info, and synchronization attributes are saved in the database after aggregation.
        The instances are in the memory (project pool) when the project is created and
        destroyed when the project is completed/failed/aborted.
    """

    def __init__(self, creation_request, project_model):
        """ Initialize the base project based on the project parameters from the creation request"""

        # extract basic project parameters (specified in HyFedProjectModel)
        coordinator = UserModel.objects.get(id=creation_request.user.id)
        tool = creation_request.data[HyFedProjectParameter.TOOL]
        algorithm = creation_request.data[HyFedProjectParameter.ALGORITHM]
        name = creation_request.data[HyFedProjectParameter.NAME]
        description = creation_request.data[HyFedProjectParameter.DESCRIPTION]
        result_dir = 'hyfed_server/result'

        # create Timer and Counter instances
        timer = TimerModel.objects.create()  # computation/network/idle/aggregation timers
        traffic = TrafficModel.objects.create()  # client <-> server network traffic

        # create and save the project model instance
        project_instance = project_model.objects.create(coordinator=coordinator, tool=tool,
                                                        algorithm=algorithm, name=name, description=description,
                                                        timer=timer, traffic=traffic, result_dir=result_dir)
        project_instance.save()

        logger.info(f"{tool} project {project_instance.id} created!")

        """  project coordination and sync parameters """
        self.project_id = str(project_instance.id)
        self.algorithm = algorithm
        self.status = project_instance.status
        self.step = project_instance.step
        self.comm_round = project_instance.comm_round
        logger.debug(f"Project {project_instance.id}: Project coordination and sync attributes initialized!")

        """ A counter to auto-generate a unique result file number """
        self.result_file_counter = 0

        """ Base dir to save the results of the project; re-initialized in the derived class """
        self.result_dir = result_dir

        """ 
            For authentication of the clients using the copy of the project in the memory (process pool);
            indexed by the client's username; initialized in ProjectPool.start_project function and NEVER re-initialized
        """
        self.client_tokens = dict()

        """ 
            Checking the operation status of the clients before aggregation; 
            indexed by the client's username;
            re-initialized in ModelAggregationView in each communication round.  
        """
        self.client_operation_stats = dict()

        """ 
            Checking whether the clients and server are synced; 
            indexed by the client's username;
            re-initialized in ModelAggregationView in each communication round.
        """
        self.client_steps = dict()
        self.client_comm_rounds = dict()

        """ 
            The value of the monitoring parameters of the clients 
            (i.e. computation time, network send/receive time, and idle time);
            indexed by the client username;
            re-initialized in ModelAggregationView in each communication round. 
        """
        self.client_monitoring_parameters = dict()

        """
            The value of the LOCAL model parameters from the clients; indexed by the client's username;
            re-initialized in ModelAggregationView in each communication round.
        """
        self.local_parameters = dict()

        """ 
            The value of the GLOBAL model parameters shared with the clients;
            computed in aggregate function of the DERIVED class in each communication round.
        """
        self.global_parameters = dict()

        """ Determine whether or not GLOBAL parameter values are the same for all clients """
        self.global_parameters_client_agnostic = True

        """ Timer to track the aggregation time of the server in each round """
        self.aggregation_timer = Timer(name='Aggregation')

        """ 
            The average (over clients) value of the clients' monitoring timers;
            Updated every communication round in post_aggregate function 
        """
        self.average_computation_time = 0.0
        self.average_network_send_time = 0.0
        self.average_network_receive_time = 0.0
        self.average_idle_time = 0.0

        """ Counters to track the traffic (in terms of bytes) """
        self.client_server_traffic = Counter("client->server")
        self.server_client_traffic = Counter("server->client")

        """ attributes to clean up the project  """
        self.time_before_clean_up = 300  # in seconds
        self.clean_up_flag = False  # will be set to True if project fails/aborted/completed

    # ########## client check functions
    def is_client_operation_ok(self):
        """
            Check the operation status of the clients to ensure all clients ended up with 'Done' operation status,
            indicating they correctly computed the local parameters or initialized the project.
        """

        logger.debug(f"Project {self.project_id}: checking operation status of the clients ...")

        operation_ok = True
        try:
            for username in self.client_operation_stats.keys():
                if self.client_operation_stats[username] != OperationStatus.DONE:
                    logger.error(f"Project {self.project_id}: Operation status is not Done at client {username}!")
                    operation_ok = False
        except Exception as exp:
            logger.error(f'Project {self.project_id}: {exp}')
            operation_ok = False

        return operation_ok

    def is_client_sync_ok(self):
        """
            Check the synchronization status of the clients;
            Before aggregation, the project step and communication round of all clients must be
            the same as the server's
        """

        logger.debug(f"Project {self.project_id}: checking synchronization status of the clients ...")

        sync_ok = True
        try:
            for username in self.client_operation_stats.keys():
                if self.client_steps[username] != self.step:
                    logger.error(f"Project {self.project_id}: "
                                 f"project step at client {username} is different from than that at the server "
                                 f"({self.client_steps[username]} vs. {self.step})!")
                    sync_ok = False

                if self.client_comm_rounds[username] != self.comm_round:
                    logger.error(f"Project {self.project_id}: "
                                 f"communication round at client {username} is different from than that at the server "
                                 f"({self.client_comm_rounds[username]} vs. {self.comm_round})!")
                    sync_ok = False

        except Exception as exp:
            logger.error(f'Project {self.project_id}: {exp}')
            sync_ok = False

        return sync_ok

    # ########## pre|post aggregation functions
    def pre_aggregate(self):
        """
            Performs pre-aggregation operations such as checking the client operation and synchronization status;
            MUST be called at the beginning of the aggregate function in all derived classes.
        """""

        logger.info(f'Project {self.project_id}: ############## pre-aggregate ####### ')
        # From server perspective, new round is the beginning of the aggregation process
        self.aggregation_timer.new_round()

        # start aggregation timer; it will be stopped in the post_aggregate function
        self.aggregation_timer.start()

        # check clients' operation status as well as ensure clients are synced with the server
        if not self.is_client_operation_ok() or not self.is_client_sync_ok():
            self.project_failed()
            return

        # if the project status is not FAILED, then go to AGGREGATING status
        if self.status == ProjectStatus.PARAMETERS_READY:
            self.set_status(ProjectStatus.AGGREGATING)

        # update project status in the database (to be visible in webapp)
        self.update_project_model()

    def aggregate(self):
        """ Will be OVERRIDDEN in the derived class  """

        self.pre_aggregate()
        if self.status != ProjectStatus.AGGREGATING:  # if project failed or aborted, skip aggregation
            self.post_aggregate()
            return

        logger.info(f'Project {self.project_id}: ############## aggregate ####### ')
        logger.info(f'Project {self.project_id}: #### step {self.step}')

        if self.step == HyFedProjectStep.INIT:  # The first step name MUST always be HyFedProjectStep.INIT
            self.create_result_dir()
            self.set_step(HyFedProjectStep.RESULT)

        elif self.step == HyFedProjectStep.RESULT:
            self.result_step()

        # The following line MUST be the last function call in the aggregate function
        self.post_aggregate()

    def post_aggregate(self):
        """
            Performs post-aggregation operations such as
            updating the project and timer values in the corresponding models;
            MUST be called at the END of the aggregate function in the derived classes.
        """

        logger.info(f'Project {self.project_id}: ############## post-aggregate ####### ')

        # clear the client-related dictionaries except monitoring parameters
        self.client_operation_stats = dict()
        self.client_steps = dict()
        self.client_comm_rounds = dict()
        self.local_parameters = dict()

        # if project failed/aborted, mark the project for clean-up
        if self.status != ProjectStatus.AGGREGATING:
            self.aggregation_timer.stop()
            self.update_project_model()  # update status and step to make them visible to the webapp
            self.clean_up_project()
            return

        # if aggregation was OK, compute average timer values of the clients
        self.average_computation_time = self.compute_client_average_time(MonitoringParameter.COMPUTATION_TIME)
        self.average_network_send_time = self.compute_client_average_time(MonitoringParameter.NETWORK_SEND_TIME)
        self.average_network_receive_time = self.compute_client_average_time(MonitoringParameter.NETWORK_RECEIVE_TIME)
        self.average_idle_time = self.compute_client_average_time(MonitoringParameter.IDLE_TIME)

        # clear client monitoring parameters
        self.client_monitoring_parameters = dict()

        # update average timer values and aggregation time in the database
        self.update_timer_model()

        # update network traffic stats in the traffic model
        self.update_traffic_model()

        # if updating timer and traffic values was NOT OK, mark the project for clean-up
        if self.status != ProjectStatus.AGGREGATING:
            self.aggregation_timer.stop()
            self.update_project_model()
            self.clean_up_project()
            return

        # if this is the last step (HyFedProjectStep.FINISHED) and project is not failed/aborted,
        # set status to Done and mark the project for clean-up
        if self.step == HyFedProjectStep.FINISHED:
            logger.info(f"Project {self.project_id}: completed!")
            self.set_status(ProjectStatus.DONE)
            self.aggregation_timer.stop()
            self.increment_comm_round()
            self.update_project_model()
            self.clean_up_project()
            return

        # if this is not the last step and aggregation was OK, go to the next round
        self.set_status(ProjectStatus.PARAMETERS_READY)
        self.increment_comm_round()
        self.update_project_model()

        # if project failed using model saving, mark project as clean-up
        if self.status != ProjectStatus.PARAMETERS_READY:
            self.clean_up_project()

        self.aggregation_timer.stop()

    def result_step(self):
        """
           FINISHED project status directs post_aggregate function to
           get the project done and mark the project for clean-up
        """

        self.set_step(HyFedProjectStep.FINISHED)

    # ########## clean-up|failure|abort function(s)
    def clean_up_project(self):
        """
            Mark project as clean-up so that it is removed from the project pool
        """
        # clear dictionaries
        self.global_parameters = {}
        self.client_operation_stats = dict()
        self.client_steps = dict()
        self.client_comm_rounds = dict()
        self.client_monitoring_parameters = dict()
        self.local_parameters = dict()

        # wait for time_before_clean_up seconds before marking the project as clean-up
        time.sleep(self.time_before_clean_up)

        # the project will be removed from the pool
        self.clean_up_flag = True

        logger.info(f'Project {self.project_id}: project marked for clean-up!')

    def project_failed(self):
        """ Perform necessary operations if the project failed """
        logger.error(f'Project {self.project_id}: project failed!')
        self.set_status(ProjectStatus.FAILED)

    def project_aborted(self):
        """ Do necessary operation if coordinator aborted the project """
        logger.error(f'Project {self.project_id}: project aborted!')
        self.set_status(ProjectStatus.ABORTED)

    # ########## model update functions
    def update_project_model(self):
        """
            Update status, step, and comm_round of the project model
        """

        try:
            project_instance = HyFedProjectModel.objects.get(id=self.project_id)
            project_instance.status = self.status
            project_instance.step = self.step
            project_instance.comm_round = self.comm_round
            project_instance.save()

            logger.debug(f'Project {self.project_id}: HyFedProject model updated!')

        except Exception as model_exception:
            logger.error(f'Project {self.project_id}: {model_exception}')
            self.project_failed()

    def update_timer_model(self):
        """ Update computation/network/idle/aggregation times in the database """

        try:

            project_instance = HyFedProjectModel.objects.get(id=self.project_id)
            project_instance.timer.computation = self.average_computation_time
            project_instance.timer.network_send = self.average_network_send_time
            project_instance.timer.network_receive = self.average_network_receive_time
            project_instance.timer.idle = self.average_idle_time
            project_instance.timer.aggregation = self.aggregation_timer.get_total_duration()

            project_instance.save()

            logger.debug(f'Project {self.project_id}: Timer model updated!')

        except Exception as model_exception:
            logger.error(f'Project {self.project_id}: {model_exception}')
            self.project_failed()

    def update_traffic_model(self):
        """ Update network traffic stats in the database """

        try:

            project_instance = HyFedProjectModel.objects.get(id=self.project_id)
            project_instance.traffic.client_server_megabytes = self.client_server_traffic.get_total_count()
            project_instance.traffic.server_client_megabytes = self.server_client_traffic.get_total_count()

            project_instance.save()

            logger.debug(f'Project {self.project_id}: Traffic model updated!')

        except Exception as model_exception:
            logger.error(f'Project {self.project_id}: {model_exception}')
            self.project_failed()

    # ########## result preparation function(s)
    def create_result_dir(self):
        """
           Create result directory for the project
        """

        result_base_dir = f'{self.result_dir}/{self.project_id}'
        try:
            # create result base directory with no permission to the other server users
            Path(result_base_dir).mkdir(parents=True, exist_ok=True)
            os.chmod(result_base_dir, 0o700)
        except Exception as create_dir_exp:
            logger.error(f'Project {self.project_id}: {create_dir_exp}')
            self.project_failed()

        logger.debug(f'Project {self.project_id}: result directory created!')

        return result_base_dir

    # ########## Helper functions
    def extract_client_parameters(self, username, request_body):
        """
            Extract the sync, monitoring, and local parameters of the clients from the request body;
            sync parameters are used in checking functions (e.g. is_client_operation_ok);
            monitoring parameters are used to compute average client timer values;
            local parameters are employed in the aggregation.
        """

        try:
            # sync parameters
            sync_parameters = request_body[Parameter.SYNCHRONIZATION]
            client_operation_status = sync_parameters[SyncParameter.OPERATION_STATUS]
            client_step = sync_parameters[SyncParameter.PROJECT_STEP]
            client_comm_round = sync_parameters[SyncParameter.COMM_ROUND]

            # monitoring parameters of the clients containing timer values
            monitoring_parameters = request_body[Parameter.MONITORING]

            # local parameters
            local_parameters = request_body[Parameter.LOCAL]

            logger.debug(f'Project {self.project_id}: client {username} parameters extracted from the request!')

        except Exception as parse_exception:
            logger.error(f'Project {self.project_id}: {parse_exception}')
            self.project_failed()
            return

        # add the client parameter values to the corresponding dictionaries
        self.add_client_operation_status(username, client_operation_status)
        self.add_client_step(username, client_step)
        self.add_client_comm_round(username, client_comm_round)
        self.add_client_monitoring_parameter(username, monitoring_parameters)
        self.add_local_parameter(username, local_parameters)

    def compute_client_average_time(self, timer_name):
        try:
            timer_values = client_parameters_to_list(self.client_monitoring_parameters, timer_name)
            average_time = np.mean(timer_values)

            logger.debug(f'Project {self.project_id}: average {timer_name} time of the clients computed!')

            return average_time
        except Exception as exp:
            logger.error(f'Project {self.project_id}: {exp}')
            self.project_failed()
            return -1

    def add_to_client_server_traffic(self, traffic_size):
        """ Add the content length of the client request to the client -> server traffic counter """

        self.client_server_traffic.increment(traffic_size)
        logger.debug(f'Project {self.project_id}: {traffic_size} bytes added to client -> server traffic!')

    def add_to_server_client_traffic(self, traffic_size):
        """ Add the size of the serialized response to  server -> client traffic counter """

        self.server_client_traffic.increment(traffic_size)
        logger.debug(f'Project {self.project_id}: {traffic_size} bytes added to server -> client traffic!')

    # ########## setter functions
    def set_status(self, status):
        self.status = status
        logger.debug(f'Project {self.project_id}: project status set to {status}')

    def set_step(self, step):
        self.step = step
        logger.debug(f'Project {self.project_id}: project step set to {step}')

    def increment_comm_round(self):
        self.comm_round += 1
        logger.debug(f'Project {self.project_id}: communication round incremented to {self.comm_round+1}!')

    def set_client_tokens(self, tokens):
        self.client_tokens = copy.deepcopy(tokens)
        logger.debug(f'Project {self.project_id}: setting client tokens ...')

    def add_client_operation_status(self, username, client_operation_status):
        logger.debug(f'Project {self.project_id}: adding client {username} operation status ...')
        self.client_operation_stats[username] = client_operation_status

    def add_client_step(self, username, client_step):
        logger.debug(f'Project {self.project_id}: adding client {username} client step ...')
        self.client_steps[username] = client_step

    def add_client_comm_round(self, username, client_comm_round):
        logger.debug(f'Project {self.project_id}: adding client {username} communication round ...')
        self.client_comm_rounds[username] = client_comm_round

    def add_client_monitoring_parameter(self, username, client_monitoring_parameter):
        logger.debug(f'Project {self.project_id}: adding client {username} monitoring parameters ...')
        self.client_monitoring_parameters[username] = client_monitoring_parameter

    def add_local_parameter(self, username, local_parameter):
        logger.debug(f'Project {self.project_id}: adding client {username} local parameters ...')
        self.local_parameters[username] = local_parameter

    def set_time_before_clean_up(self, time_before_clean_up):
        logger.debug(f'Project {self.project_id}: setting time_before_clean_up to {time_before_clean_up} ...')
        self.time_before_clean_up = time_before_clean_up

    # ########## getter functions
    def get_project_id(self):
        return self.project_id

    def get_status(self):
        return self.status

    def get_step(self):
        return self.step

    def get_comm_round(self):
        return self.comm_round

    def get_global_parameters(self):
        return self.global_parameters

    def get_local_parameters(self):
        return self.local_parameters

    def get_client_tokens(self):
        return self.client_tokens

    def get_average_computation_time(self):
        return self.average_computation_time

    def get_average_network_send_time(self):
        return self.average_network_send_time

    def get_average_network_receive_time(self):
        return self.average_network_receive_time

    def get_average_idle_time(self):
        return self.average_idle_time

    def is_global_parameters_client_agnostic(self):
        return self.global_parameters_client_agnostic

    def clean_me_up(self):
        return self.clean_up_flag
