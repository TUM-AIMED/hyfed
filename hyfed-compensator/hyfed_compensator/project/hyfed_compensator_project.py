"""
    The main class to obtain the compensation parameters from the clients, aggregate them,
    and share the aggregation results with the server

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

from hyfed_compensator.util.hyfed_parameters import Parameter, AuthenticationParameter, SyncParameter, ConnectionParameter, MonitoringParameter
from hyfed_compensator.util.status import OperationStatus
from hyfed_compensator.util.endpoint import EndPoint
from hyfed_compensator.util.utils import aggregate
from hyfed_compensator.util.monitoring import Timer, Counter

import pickle
import numpy as np
import time
import hashlib
import requests
from datetime import datetime

import logging
logger = logging.getLogger(__name__)


class HyFedCompensatorProject:
    """
        Provide main functions to communicate with the clients and server,
        and to aggregate the compensation parameters from the clients
    """

    def __init__(self, project_id_hash, client_count):
        """ Initialize the compensator project using the hash of the project ID and the number of clients """

        # for compensator to know whether it has received compensation parameters from all clients
        self.client_count = client_count

        # hash of the project ID, which should be the same for all clients
        self.project_id_hash = project_id_hash

        # authentication parameters from the clients
        self.client_token_hashes = list()
        self.client_username_hashes = list()

        # sync parameters from the clients
        self.client_steps = list()
        self.client_comm_rounds = list()

        # compensation parameters (noise values) from the clients
        self.client_compensation_parameters = list()

        # data type parameters from clients
        self.client_data_type_parameters = list()

        # clients tell compensator where to send the aggregated noise values
        self.server_urls = list()

        # aggregated parameters have the same parameter names as the local model parameters of the clients
        self.aggregated_compensation_parameters = dict()

        # to tell the server whether the aggregation of noise values have been successful
        self.operation_status = OperationStatus.DONE

        # monitoring timers
        self.computation_timer = Timer(name='Computation')
        self.network_send_timer = Timer(name='Network Send')

        # counter to track the traffic client -> compensator (in terms of bytes)
        self.client_compensator_traffic = Counter("client->compensator")

        self.upload_parameters_timeout = 600

        # used for garbage collection purposes
        self.last_updated_date = datetime.now().timestamp()

    def add_client_parameters(self, request):
        """ Append client's authentication, sync, connection, and compensation parameters to the corresponding lists """

        try:
            # new communication round starts for compensator if the parameters from the first client is received
            if len(self.client_compensation_parameters) == 0:
                self.computation_timer.new_round()
                self.network_send_timer.new_round()

            # add traffic size to client -> compensator traffic counter
            traffic_size = int(request.headers['Content-Length'])
            self.client_compensator_traffic.increment(traffic_size)
            logger.debug(f'Project {self.project_id_hash}: {traffic_size} bytes added to client -> compensator traffic.')

            self.computation_timer.start()

            # extract client parameters from the request body
            request_body = pickle.loads(request.body)

            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            sync_parameters = request_body[Parameter.SYNCHRONIZATION]
            compensation_parameters = request_body[Parameter.COMPENSATION]
            connection_parameters = request_body[Parameter.CONNECTION]
            data_type_parameters = request_body[Parameter.DATA_TYPE]

            # authentication parameters
            hash_username = authentication_parameters[AuthenticationParameter.HASH_USERNAME]
            hash_token = authentication_parameters[AuthenticationParameter.HASH_TOKEN]

            # sync parameters
            step = sync_parameters[SyncParameter.PROJECT_STEP]
            comm_round = sync_parameters[SyncParameter.COMM_ROUND]

            # connection parameter
            server_url = connection_parameters[ConnectionParameter.SERVER_URL]

            # add the parameters to the lists
            self.client_username_hashes.append(hash_username)
            self.client_token_hashes.append(hash_token)
            self.client_steps.append(step)
            self.client_comm_rounds.append(comm_round)
            self.server_urls.append(server_url)
            self.client_compensation_parameters.append(compensation_parameters)
            self.client_data_type_parameters.append(data_type_parameters)

            self.computation_timer.stop()

            logger.debug(f'Project {self.project_id_hash}: Client parameters added!')

        except Exception as add_parameter_exp:
            logger.error(f'Project {self.project_id_hash}: Adding client parameters was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {add_parameter_exp}')
            self.computation_timer.stop()
            self.set_operation_status_failed()

    def aggregate_client_parameters(self):
        """ Aggregate client parameters including the compensation parameters from all clients """

        try:
            self.computation_timer.start()

            logger.debug(f"Project {self.project_id_hash}: Aggregating client parameters ...")

            # make sure all clients are in the same step and communication round
            if not self.is_client_sync_ok():
                logger.error(f'Project {self.project_id_hash}: The step/comm_round of the clients are different!')
                self.computation_timer.stop()
                self.set_operation_status_failed()
                return

            # ensure all clients are coordinated by the same server
            if not self.is_server_url_same():
                logger.error(f'Project {self.project_id_hash}: Server URL is different for the clients!')
                self.computation_timer.stop()
                self.set_operation_status_failed()
                return

            # make sure compensator parameter names are the same across the clients
            if not self.is_client_compensation_parameters_ok():
                logger.error(f'Project {self.project_id_hash}: Compensation parameter names are different across clients!')
                self.computation_timer.stop()
                self.set_operation_status_failed()
                return

            # aggregate the compensation parameters
            for parameter_name in self.client_compensation_parameters[0].keys():
                compensation_values = self.compensation_parameter_to_list(parameter_name)
                parameter_data_type = self.client_data_type_parameters[0][parameter_name]
                aggregated_compensation_value = aggregate(compensation_values, parameter_data_type)
                self.aggregated_compensation_parameters[parameter_name] = -aggregated_compensation_value

            self.computation_timer.stop()

        except Exception as aggregate_exp:
            logger.error(f'Project {self.project_id_hash}: Aggregating the compensation parameters was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {aggregate_exp}')
            self.computation_timer.stop()
            self.set_operation_status_failed()

    def send_to_server(self):
        """ Send aggregated authentication, sync, monitoring, and compensation parameters to the server """

        # create and serialize request body
        parameters_serialized = self.prepare_server_parameters()

        max_tries = 10
        for _ in range(max_tries):
            try:

                logger.debug(f"Project {self.project_id_hash}: Sending the aggregated parameters to the server ...")

                self.network_send_timer.start()
                response = requests.post(url=f'{self.server_urls[0]}/{EndPoint.MODEL_COMPENSATION}',
                                         data=parameters_serialized,
                                         timeout=self.upload_parameters_timeout)

                if response.status_code == 200:
                    logger.debug(f"Project {self.project_id_hash}: Sending done!")
                    self.network_send_timer.stop()
                    return

                logger.error(f"Project {self.project_id_hash}: Sending failed, got {response.status_code} status code from the server!")
                self.network_send_timer.stop()

                time.sleep(30)
                continue
            except Exception as send_server_exp:
                logger.error(f"Project {self.project_id_hash}: Sending failed!")
                logger.error(f'Project {self.project_id_hash}: The exception is: {send_server_exp}')
                self.network_send_timer.stop()
                time.sleep(30)

    def aggregate_and_send(self):
        """ First aggregate, and then, send aggregated parameters to the server """

        # aggregate client parameters including compensation parameters
        self.aggregate_client_parameters()

        # send the aggregated parameters to the server
        self.send_to_server()

        # empty the lists/dictionaries for the next round
        self.client_token_hashes = list()
        self.client_username_hashes = list()
        self.client_steps = list()
        self.client_comm_rounds = list()
        self.client_compensation_parameters = list()
        self.client_data_type_parameters = list()
        self.server_urls = list()
        self.aggregated_compensation_parameters = dict()

    # ########## setter/getter functions
    def set_operation_status_done(self):
        """ If current operation is still in progress (not failed), then set it to Done """

        if self.operation_status == OperationStatus.IN_PROGRESS:
            self.operation_status = OperationStatus.DONE

    def set_operation_status_in_progress(self):
        """ If previous operation is done (not failed), then set current operation status to In Progress """

        if self.operation_status == OperationStatus.DONE:
            self.operation_status = OperationStatus.IN_PROGRESS

    def set_operation_status_failed(self):
        """ Regardless of the current status, set the operation status to Failed """

        logger.error("Operation failed!")
        self.operation_status = OperationStatus.FAILED

    def set_last_updated_date(self):
        self.last_updated_date = datetime.now().timestamp()

    def is_operation_failed(self):
        return self.operation_status == OperationStatus.FAILED

    def get_last_updated_date(self):
        return self.last_updated_date

    # ########## Helper functions
    def is_client_sync_ok(self):
        """ Ensure the project step and communication round of all clients is the same """

        try:
            logger.debug(f"Project {self.project_id_hash}: checking synchronization status of the clients ...")

            return (np.all(np.array(self.client_steps) == self.client_steps[0]) and
                    np.all(np.array(self.client_comm_rounds) == self.client_comm_rounds[0]))

        except Exception as sync_exp:
            logger.error(f'Project {self.project_id_hash}: Checking sync status of the clients was failed')
            logger.error(f'Project {self.project_id_hash}: The exception is: {sync_exp}')
            return False

    def is_server_url_same(self):
        """ Ensure the the server urls from all clients are the same """

        try:

            logger.debug(f"Project {self.project_id_hash}: Checking whether clients are coordinated by the same server ...")

            return np.all(np.array(self.server_urls) == self.server_urls[0])

        except Exception as server_url_exp:
            logger.error(f'Project {self.project_id_hash}: Checking server urls was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {server_url_exp}')
            return False

    def is_client_compensation_parameters_ok(self):
        """ Make sure the names of the compensation parameters are consistent across clients """
        try:
            logger.debug(f"Project {self.project_id_hash}: checking whether compensation parameter names are consistent across all clients ...")
            client1_compensation_parameter_names = self.client_compensation_parameters[0].keys()
            for client_parameters in self.client_compensation_parameters:

                if client_parameters.keys() != client1_compensation_parameter_names:
                    return False

            return True
        except Exception as compensation_param_exp:
            logger.error(f'Project {self.project_id_hash}: Checking compensation parameter names was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {compensation_param_exp}')
            return False

    def is_client_data_type_parameters_ok(self):
        """ Make sure the names of the data type parameters are consistent across clients """
        try:
            logger.debug(f"Project {self.project_id_hash}: checking whether data type parameter names are consistent across all clients ...")
            client1_data_type_parameter_names = self.client_data_type_parameters[0].keys()
            for client_parameters in self.client_data_type_parameters:
                if client_parameters.keys() != client1_data_type_parameter_names:
                    return False

            return True
        except Exception as compensation_param_exp:
            logger.error(f'Project {self.project_id_hash}: Checking data type parameter names was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {compensation_param_exp}')
            return False

    def should_aggregate_and_send(self):
        """ Check whether compensation parameters from all clients received """

        return len(self.client_username_hashes) == self.client_count

    def compensation_parameter_to_list(self, parameter_name):
        """
            Extract the compensation parameter of the clients specified with parameter_name as a list
        """

        compensation_parameter_list = []
        try:
            for compensation_parameter in self.client_compensation_parameters:
                compensation_parameter_list.append(compensation_parameter[parameter_name])
        except Exception as convert_exp:
            logger.error(f'Project {self.project_id_hash}: Converting compensation parameters to list was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {convert_exp}')
            self.set_operation_status_failed()

        return compensation_parameter_list

    def prepare_server_parameters(self):
        """ Prepare the parameters shared with the server """

        try:
            self.computation_timer.start()

            # initialize authentication parameters
            authentication_parameters = dict()

            hash_username_hashes = hashlib.sha256(''.join(sorted(self.client_username_hashes)).encode('utf-8')).hexdigest()
            hash_token_hashes = hashlib.sha256(''.join(sorted(self.client_token_hashes)).encode('utf-8')).hexdigest()

            authentication_parameters[AuthenticationParameter.HASH_PROJECT_ID] = self.project_id_hash
            authentication_parameters[AuthenticationParameter.HASH_USERNAME_HASHES] = hash_username_hashes
            authentication_parameters[AuthenticationParameter.HASH_TOKEN_HASHES] = hash_token_hashes

            # initialize synchronization parameters
            sync_parameters = dict()
            sync_parameters[SyncParameter.PROJECT_STEP] = self.client_steps[0]
            sync_parameters[SyncParameter.COMM_ROUND] = self.client_comm_rounds[0]
            sync_parameters[SyncParameter.OPERATION_STATUS] = self.operation_status

            monitoring_parameters = dict()
            monitoring_parameters[MonitoringParameter.COMPUTATION_TIME] = self.computation_timer.get_total_duration()
            monitoring_parameters[MonitoringParameter.NETWORK_SEND_TIME] = self.network_send_timer.get_total_duration()
            monitoring_parameters[MonitoringParameter.CLIENT_COMPENSATOR_TRAFFIC] = self.client_compensator_traffic.total_count

            # server parameters in json
            server_parameters_json = {Parameter.AUTHENTICATION: authentication_parameters,
                                      Parameter.SYNCHRONIZATION: sync_parameters,
                                      Parameter.MONITORING: monitoring_parameters,
                                      Parameter.COMPENSATION: self.aggregated_compensation_parameters
                                     }
            server_parameters_serialized = pickle.dumps(server_parameters_json)

            self.computation_timer.stop()

            return server_parameters_serialized

        except Exception as prepare_exp:
            logger.error(f'Project {self.project_id_hash}: Preparing server parameters was failed!')
            logger.error(f'Project {self.project_id_hash}: The exception is: {prepare_exp}')
            self.computation_timer.stop()
            self.set_operation_status_failed()
