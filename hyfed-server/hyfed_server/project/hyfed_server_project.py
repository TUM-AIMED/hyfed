"""
    Provides the base functions of the server including client and compensator synchronization and operation check,
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
from hyfed_server.util.hyfed_parameters import Parameter, SyncParameter, MonitoringParameter, AuthenticationParameter, CoordinationParameter
from hyfed_server.util.monitoring import Timer, Counter
from hyfed_server.model.hyfed_models import HyFedProjectModel, TimerModel, TrafficModel
from hyfed_server.util.utils import client_parameters_to_list, aggregate_parameters
from hyfed_server.util.hyfed_steps import HyFedProjectStep
from hyfed_server.models import UserModel
from hyfed_server.util.hyfed_parameters import HyFedProjectParameter
from hyfed_server.util.data_type import DataType

from pathlib import Path
import copy
import os
import numpy as np
import time
import hashlib
import pickle

import logging
logger = logging.getLogger(__name__)


class HyFedServerProject:
    """
        A base class that provides the essential functions of the server package
        including client/compensator sync check, pre/post-aggregation operation, result preparation, and etc.
        The local parameters of the clients in this and all derived classes or compensator parameters are NEVER saved in a permanent storage.
        Only timer values, project info, and synchronization attributes are saved in the database after aggregation.
        The instances are in the memory (project pool) when the project is created and
        destroyed when the project is completed/failed/aborted.
    """

    def __init__(self, creation_request, project_model):
        """ Initialize the base project based on the project parameters from the creation request """

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

        logger.debug(f"{tool} project {project_instance.id} created!")

        #  project coordination and sync parameters
        self.project_id = str(project_instance.id)
        self.algorithm = algorithm
        self.status = project_instance.status
        self.step = project_instance.step
        self.comm_round = project_instance.comm_round
        logger.debug(f"Project {project_instance.id}: Project coordination and sync attributes initialized!")

        # base dir to save the results of the project; re-initialized in the derived class
        self.result_dir = result_dir

        # for authentication of the clients using the copy of the project in the memory (process pool);
        # indexed by the client's username; initialized in ProjectPool.start_project function and NEVER re-initialized
        self.client_tokens = dict()

        # checking the operation status of the clients before aggregation; indexed by the client's username;
        # re-initialized in ModelAggregationView in each communication round.
        self.client_operation_stats = dict()

        # checking whether the clients and server are synced; indexed by the client's username;
        # re-initialized in ModelAggregationView in each communication round.
        self.client_steps = dict()
        self.client_comm_rounds = dict()
        self.client_compensator_flags = dict()

        # the value of the monitoring parameters of the clients (i.e. computation time, network send/receive time, and idle time);
        # indexed by the client username; re-initialized in ModelAggregationView in each communication round.
        self.client_monitoring_parameters = dict()

        # the value of the (noisy) local model parameters from the clients; indexed by the client's username;
        # re-initialized in ModelAggregationView in each communication round.
        self.local_parameters = dict()

        # the parameter values from the compensator such as aggregated noise, operation status, and etc """
        self.compensator_parameters = dict()

        # the value of the global model parameters shared with the clients;
        # computed in aggregate function of the DERIVED class in each communication round.
        self.global_parameters = dict()

        # to identify to which communication round the current value of the self.global_parameters

        # determine whether or not global parameter values are the same for all clients
        self.global_parameters_client_agnostic = True

        # determine whether the server should wait for compensator before aggregation; re-initialized in the is_client_sync_ok function
        self.compensator_flag = False

        self.participants_clicked_run = set()  # used to determine the start time of the project; updated in prepare_client_parameters function
        self.start_time = 0.0  # the approximate time all participants clicked on Run button

        # timers to track the computation (i.e. aggregation and result preparation) time of the server in each round
        self.computation_timer = Timer(name='Server Computation')

        # the average (over clients) value of the clients' monitoring timers;
        # updated every communication round in post_aggregate function
        self.client_computation = 0.0
        self.client_network_send = 0.0
        self.client_network_receive = 0.0
        self.client_idle = 0.0

        # compensator times (computation and network send)
        self.compensator_computation = 0.0
        self.compensator_network_send = 0.0

        # counters to track the traffic (in terms of bytes)
        self.client_server_traffic = Counter("client->server")
        self.server_client_traffic = Counter("server->client")
        self.compensator_server_traffic = Counter("compensator->server")
        self.client_compensator_traffic = Counter("client->compensator")  # will be provided by the compensator

        # attributes to clean up the project
        self.time_before_clean_up = 300  # in seconds
        self.clean_up_flag = False  # will be set to True if project fails/aborted/completed

        # attributes to authenticate the compensator; re-initialized in set_hashes function
        self.hash_project_id = ''
        self.hash_client_tokens = ''
        self.hash_client_usernames = ''

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
            logger.error(f"Project {self.project_id}: Failed to check the clients' operation status parameters!")
            logger.error(f'Project {self.project_id}: The exception is: {exp}')
            operation_ok = False

        return operation_ok

    def is_client_sync_ok(self):
        """
            Check the synchronization status of the clients;
            Before aggregation, the project step and communication round of all clients must be
            the same as the server's; Moreover, compensator_flag value should be the same for all clients
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

            compensator_flag_array = np.array(list(self.client_compensator_flags.values()))
            if not np.all(compensator_flag_array == compensator_flag_array[0]):
                logger.debug(f"Project {self.project_id}: compensator flag is not the same across all clients!")
                sync_ok = False
            else:
                self.compensator_flag = compensator_flag_array[0]

        except Exception as exp:
            logger.error(f"Project {self.project_id}: Failed to check the clients' sync parameters!")
            logger.error(f'Project {self.project_id}: The exception is: {exp}')
            sync_ok = False

        return sync_ok

    def is_compensator_sync_and_operation_ok(self):
        """
            Check the synchronization and operation status of the compensator
        """

        logger.debug(f"Project {self.project_id}: checking synchronization and operation status of the compensator ...")

        try:
            if not self.compensator_parameters:
                logger.debug(f"Project {self.project_id}: compensator parameters are empty!")
                return False

            if self.compensator_parameters[Parameter.SYNCHRONIZATION][SyncParameter.OPERATION_STATUS] != OperationStatus.DONE:
                logger.debug(f"Project {self.project_id}: Operation status is NOT DONE at compensator!")
                return False

            if self.compensator_parameters[Parameter.SYNCHRONIZATION][SyncParameter.COMM_ROUND] != self.comm_round:
                logger.debug(f"Project {self.project_id}: communication round in server and compensator are different!")
                return False

            if self.compensator_parameters[Parameter.SYNCHRONIZATION][SyncParameter.PROJECT_STEP] != self.step:
                logger.debug(f"Project {self.project_id}: project step in server and compensator are different!")
                return False

        except Exception as exp:
            logger.error(f"Project {self.project_id}: Failed to check the compensator's sync and operation status parameters!")
            logger.error(f'Project {self.project_id}: The exception is: {exp}')
            return False

        return True

    # ########## pre|post aggregation functions
    def pre_aggregate(self):
        """
            Performs pre-aggregation operations such as checking the client operation and synchronization status;
            MUST be called at the beginning of the aggregate function in all derived classes.
        """""

        logger.debug(f'Project {self.project_id}: ####### Communication round # {self.comm_round}')
        logger.debug(f'Project {self.project_id}: #### step {self.step}')
        logger.debug(f'Project {self.project_id}: ## pre-aggregate')

        # clear the global parameters from the previous round
        self.global_parameters = dict()

        # check clients' operation status as well as ensure clients are synced with the server
        if not self.is_client_operation_ok() or not self.is_client_sync_ok():
            self.project_failed()
            return

        # if compensator is used to hide model parameter values
        if self.compensator_flag:

            # to inform clients and coordinator that server is waiting for compensator
            if not self.is_compensator_parameters_received():
                self.set_status(ProjectStatus.WAITING_FOR_COMPENSATOR)
                self.update_project_model()

            # wait until compensator parameters received
            while not self.is_compensator_parameters_received():
                time.sleep(1)

            # check whether sync and operation status was OK in compensator
            if not self.is_compensator_sync_and_operation_ok():
                self.project_failed()
                return

            # update the monitoring parameters
            self.update_compensator_monitoring_parameters()

            # add compensation parameters to the local parameters for aggregation
            self.add_compensation_parameters()

        # From server perspective, new round is the beginning of the aggregation process
        self.computation_timer.new_round()

        # start aggregation timer; it will be stopped in the post_aggregate function
        self.computation_timer.start()

        # if the project status is not FAILED/ABORTED, then go to AGGREGATING status
        if self.status != ProjectStatus.FAILED or self.status != ProjectStatus.ABORTED:
            self.set_status(ProjectStatus.AGGREGATING)

        # update project status in the database (to be visible in webapp)
        self.update_project_model()

    def aggregate(self):
        """ Will be OVERRIDDEN in the derived class  """

        self.pre_aggregate()
        if self.status != ProjectStatus.AGGREGATING:  # if project failed or aborted, skip aggregation
            self.post_aggregate()
            return

        logger.debug(f'Project {self.project_id}: ## aggregate')

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

        logger.debug(f'Project {self.project_id}: ## post-aggregate')

        # clear the client-related dictionaries except monitoring parameters
        self.client_operation_stats = dict()
        self.client_steps = dict()
        self.client_comm_rounds = dict()
        self.local_parameters = dict()
        self.compensator_flag = False
        self.compensator_parameters = dict()
        self.client_compensator_flags = dict()

        # if project failed/aborted, mark the project for clean-up
        if self.status != ProjectStatus.AGGREGATING:
            self.computation_timer.stop()
            self.update_project_model()  # update status and step to make them visible to the webapp
            self.clean_up_project()
            return

        # if aggregation was OK, compute average timer values of the clients
        self.client_computation = self.compute_client_average_time(MonitoringParameter.COMPUTATION_TIME)
        self.client_network_send = self.compute_client_average_time(MonitoringParameter.NETWORK_SEND_TIME)
        self.client_network_receive = self.compute_client_average_time(MonitoringParameter.NETWORK_RECEIVE_TIME)
        self.client_idle = self.compute_client_average_time(MonitoringParameter.IDLE_TIME)

        # clear client monitoring parameters
        self.client_monitoring_parameters = dict()

        # update average timer values and aggregation time in the database
        self.update_timer_model()

        # update network traffic stats in the traffic model
        self.update_traffic_model()

        # if updating timer and traffic values was NOT OK, mark the project for clean-up
        if self.status != ProjectStatus.AGGREGATING:
            self.computation_timer.stop()
            self.update_project_model()
            self.clean_up_project()
            return

        # if this is the last step (HyFedProjectStep.FINISHED) and project is not failed/aborted,
        # set status to Done and mark the project for clean-up
        if self.step == HyFedProjectStep.FINISHED:
            logger.debug(f"Project {self.project_id}: completed!")
            self.set_status(ProjectStatus.DONE)
            self.computation_timer.stop()
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

        self.computation_timer.stop()

    def result_step(self):
        """
           FINISHED project status directs post_aggregate function to
           get the project done and mark the project for clean-up
        """

        self.set_step(HyFedProjectStep.FINISHED)

    def compute_aggregated_parameter(self, parameter_name, parameter_data_type):
        clients_parameters = []
        try:
            for username in self.client_tokens.keys():
                clients_parameters.append(self.local_parameters[username][parameter_name])

            if self.compensator_flag:

                # aggregate client noisy parameters
                # modular arithmetic for client noisy parameters that are non-negative integers
                aggregated_noisy_parameters = aggregate_parameters(clients_parameters, parameter_data_type)

                # aggregated noise, already computed by the compensator using modular arithmetic for non-negative integers
                aggregated_noise = self.local_parameters[self.hash_client_usernames][parameter_name]

                # aggregate the aggregated-noise and aggregated-client-noisy-parameters
                # modular arithmetic for non-negative integers
                aggregated_value = aggregate_parameters([aggregated_noisy_parameters, aggregated_noise], parameter_data_type)

            else:
                if parameter_data_type == DataType.NON_NEGATIVE_INTEGER or \
                   parameter_data_type == DataType.NEGATIVE_INTEGER or parameter_data_type == DataType.FLOAT:
                        aggregated_value = np.sum(clients_parameters)

                else:
                    aggregated_value = np.sum(clients_parameters, axis=0)

            return aggregated_value

        except Exception as exp:
            logger.error(exp)
            return None

    # ########## clean-up|failure|abort function(s)
    def clean_up_project(self):
        """
            Mark project as clean-up so that it is removed from the project pool
        """
        # clear dictionaries
        self.global_parameters = dict()
        self.client_operation_stats = dict()
        self.client_steps = dict()
        self.client_comm_rounds = dict()
        self.client_monitoring_parameters = dict()
        self.local_parameters = dict()
        self.compensator_parameters = dict()
        self.client_compensator_flags = dict()

        # wait for time_before_clean_up seconds before marking the project as clean-up
        time.sleep(self.time_before_clean_up)

        # the project will be removed from the pool
        self.clean_up_flag = True

        logger.debug(f'Project {self.project_id}: project marked for clean-up!')

    def project_failed(self):
        """ Perform necessary operations if the project failed """

        logger.error(f'Project {self.project_id}: project failed!')
        self.set_status(ProjectStatus.FAILED)
        self.update_project_model()

    def project_aborted(self):
        """ Do necessary operation if coordinator aborted the project """

        logger.error(f'Project {self.project_id}: project aborted!')
        self.set_status(ProjectStatus.ABORTED)
        self.update_project_model()

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
            timer_instance = TimerModel.objects.get(id=project_instance.timer.id)

            timer_instance.client_computation = np.round(self.client_computation, 2)
            timer_instance.client_network_send = np.round(self.client_network_send, 2)
            timer_instance.client_network_receive = np.round(self.client_network_receive, 2)
            timer_instance.client_idle = np.round(self.client_idle, 2)
            timer_instance.compensator_computation = np.round(self.compensator_computation, 2)
            timer_instance.compensator_network_send = np.round(self.compensator_network_send, 2)
            timer_instance.server_computation = np.round(self.computation_timer.get_total_duration(), 2)
            timer_instance.runtime_total = np.round(time.time() - self.start_time, 2)

            timer_instance.save()

            logger.debug(f'Project {self.project_id}: Timer model updated!')

        except Exception as model_exception:
            logger.error(f'Project {self.project_id}: {model_exception}')
            self.project_failed()

    def update_traffic_model(self):
        """ Update network traffic stats in the database """

        try:

            project_instance = HyFedProjectModel.objects.get(id=self.project_id)
            traffic_instance = TrafficModel.objects.get(id=project_instance.traffic.id)

            traffic_instance.client_server = self.client_server_traffic.get_total_count()
            traffic_instance.server_client = self.server_client_traffic.get_total_count()
            traffic_instance.compensator_server = self.compensator_server_traffic.get_total_count()
            traffic_instance.client_compensator = self.client_compensator_traffic.get_total_count()

            total_traffic = self.client_server_traffic.total_count + self.server_client_traffic.total_count + \
                            self.compensator_server_traffic.total_count + self.client_compensator_traffic.total_count
            total_traffic_counter = Counter("Total")
            total_traffic_counter.increment(total_traffic)
            traffic_instance.traffic_total = total_traffic_counter.get_total_count()

            traffic_instance.save()

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
            client_compensator_flag = sync_parameters[SyncParameter.COMPENSATOR_FLAG]

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
        self.add_client_compensator_flag(username, client_compensator_flag)
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
        """ Update the client -> server traffic counter """

        self.client_server_traffic.increment(traffic_size)
        logger.debug(f'Project {self.project_id}: {traffic_size} bytes added to client -> server traffic.')

    def add_to_server_client_traffic(self, traffic_size):
        """ Update the server -> client traffic counter """

        self.server_client_traffic.increment(traffic_size)
        logger.debug(f'Project {self.project_id}: {traffic_size} bytes added to server -> client traffic.')

    def add_to_compensator_server_traffic(self, traffic_size):
        """ Update the compensator -> server traffic counter """

        self.compensator_server_traffic.increment(traffic_size)
        logger.debug(f'Project {self.project_id}: {traffic_size} bytes added to compensator -> server traffic.')

    def prepare_client_parameters(self, client_username, client_comm_round):
        """ Prepare the parameters shared with the clients """
        try:

            # the number of participants who clicked on the 'Run' button is the same as the number of times the
            # prepare_client_parameters function has been called in the 'Init' step for a different participant
            if self.step == HyFedProjectStep.INIT:
                if client_username not in self.participants_clicked_run:
                    self.participants_clicked_run.add(client_username)

                # if all participant clicked on the 'Run' button, then initialized start time
                if len(self.participants_clicked_run) == len(self.client_tokens):
                    self.set_start_time()

            coordination_parameters = dict()

            coordination_parameters[CoordinationParameter.PROJECT_ID] = self.project_id
            coordination_parameters[CoordinationParameter.PROJECT_STATUS] = self.status
            coordination_parameters[CoordinationParameter.PROJECT_STEP] = self.step
            coordination_parameters[CoordinationParameter.COMM_ROUND] = self.comm_round

            # based on client_comm_round decide whether global parameters already shared by the client
            if client_comm_round != self.comm_round:
                if self.is_global_parameters_client_agnostic():
                    global_parameters = self.global_parameters
                else:
                    global_parameters = self.global_parameters[client_username]
            else:
                global_parameters = dict()

            parameters_json = {Parameter.COORDINATION: coordination_parameters, Parameter.GLOBAL: global_parameters}
            parameters_serialized = pickle.dumps(parameters_json)

            return parameters_serialized
        except Exception as prep_exp:
            logger.error(f'Project {self.project_id}: {prep_exp}')
            self.project_failed()

    # ########## setter functions
    # def set_global_parameters(self, parameter_name, parameter_value):
    #     self.global_parameters[parameter_name] = parameter_value
    #
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
        logger.debug(f'Project {self.project_id}: client tokens initialized!')

    def set_start_time(self):
        self.start_time = time.time()
        logger.debug(f'Project {self.project_id}: start time initialized!')

    def set_hashes(self):
        """ computes hash(project_id) and hash(hash(X_1) + ... + hash(X_k)), where X is token/username of a client """

        # hash of project ID
        self.hash_project_id = hashlib.sha256(self.project_id.encode('utf-8')).hexdigest()

        # hash of usernames
        username_hash_list = list()
        for username in self.client_tokens.keys():
            username_hash_list.append(hashlib.sha256(username.encode('utf-8')).hexdigest())
        self.hash_client_usernames = hashlib.sha256(''.join(sorted(username_hash_list)).encode('utf-8')).hexdigest()

        # hash of tokens
        token_hash_list = list()
        for token in self.client_tokens.values():
            token_hash_list.append(hashlib.sha256(token.encode('utf-8')).hexdigest())
        self.hash_client_tokens = hashlib.sha256(''.join(sorted(token_hash_list)).encode('utf-8')).hexdigest()

        logger.debug(f'Project {self.project_id}: project_id, username, and token hash values initialized!')

    def set_compensator_parameters(self, compensator_parameters):
        self.compensator_parameters = compensator_parameters

    def update_compensator_monitoring_parameters(self):
        """ Extract the computation and network_send_time of compensator and set them in the corresponding attributes """

        self.compensator_computation = self.compensator_parameters[Parameter.MONITORING][MonitoringParameter.COMPUTATION_TIME]
        self.compensator_network_send = self.compensator_parameters[Parameter.MONITORING][MonitoringParameter.NETWORK_SEND_TIME]

        client_compensator_traffic = self.compensator_parameters[Parameter.MONITORING][MonitoringParameter.CLIENT_COMPENSATOR_TRAFFIC]
        self.client_compensator_traffic = Counter("Client->Compensator")
        self.client_compensator_traffic.increment(client_compensator_traffic)

    def add_compensation_parameters(self):
        """ Add compensation parameters (similar to local parameters) to self.local_parameters to be considered in aggregation"""

        # extract username and compensation parameters
        compensator_username = self.compensator_parameters[Parameter.AUTHENTICATION][AuthenticationParameter.HASH_USERNAME_HASHES]
        compensation_parameters = self.compensator_parameters[Parameter.COMPENSATION]
        self.add_local_parameter(compensator_username, compensation_parameters)

    def add_client_operation_status(self, username, client_operation_status):
        logger.debug(f'Project {self.project_id}: adding client {username} operation status ...')
        self.client_operation_stats[username] = client_operation_status

    def add_client_step(self, username, client_step):
        logger.debug(f'Project {self.project_id}: adding client {username} client step ...')
        self.client_steps[username] = client_step

    def add_client_comm_round(self, username, client_comm_round):
        logger.debug(f'Project {self.project_id}: adding client {username} communication round ...')
        self.client_comm_rounds[username] = client_comm_round

    def add_client_compensator_flag(self, username, client_compensator_flag):
        logger.debug(f'Project {self.project_id}: adding client {username} compensator flag ...')
        self.client_compensator_flags[username] = client_compensator_flag

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

    def get_hash_client_tokens(self):
        return self.hash_client_tokens

    def get_hash_client_usernames(self):
        return self.hash_client_usernames

    def get_average_computation_time(self):
        return self.client_computation

    def get_average_network_send_time(self):
        return self.client_network_send

    def get_average_network_receive_time(self):
        return self.client_network_receive

    def get_average_idle_time(self):
        return self.client_idle

    def is_global_parameters_client_agnostic(self):
        return self.global_parameters_client_agnostic

    def clean_me_up(self):
        return self.clean_up_flag

    def is_compensator_parameters_received(self):
        return bool(self.compensator_parameters)
