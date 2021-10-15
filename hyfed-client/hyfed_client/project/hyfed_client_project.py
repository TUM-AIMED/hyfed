"""
    A class providing the essential functions of the client such as sending client parameters,
    receiving server parameters, downloading results, and logging.

    Copyright 2021 Reza NasiriGerdeh and Reihaneh TorkzadehMahani. All Rights Reserved.

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


from hyfed_client.util.status import OperationStatus, ProjectStatus
from hyfed_client.util.hyfed_parameters import Parameter, CoordinationParameter, SyncParameter, \
    MonitoringParameter, AuthenticationParameter, ConnectionParameter
from hyfed_client.util.hyfed_steps import HyFedProjectStep
from hyfed_client.util.monitoring import Timer
from hyfed_client.util.operation import ClientOperation
from hyfed_client.util.endpoint import EndPoint
from hyfed_client.util.utils import make_noisy

import hashlib
import pickle
import requests
import datetime
import time
import os
import numpy as np
from pathlib import Path


class HyFedClientProject:
    """ A base class providing basic functions of client package for communication with the server or compensator """

    def __init__(self, username, project_id, token, server_url, compensator_url,
                 name, description, tool, algorithm, coordinator, result_dir, log_dir):

        # authentication parameters
        self.username = username
        self.project_id = project_id
        self.token = token

        # connection parameters
        self.server_url = server_url
        self.compensator_url = compensator_url

        # project parameters
        self.name = name
        self.description = description
        self.tool = tool
        self.algorithm = algorithm
        self.coordinator = coordinator

        # sync parameters
        self.operation_status = OperationStatus.DONE
        self.project_step = HyFedProjectStep.INIT
        self.comm_round = 0
        self.project_status = ProjectStatus.CREATED

        #  current operation of the client
        self.client_operation = ClientOperation.WAITING_FOR_START

        # logging
        self.log_message_list = []

        # model related parameters client <-> server and client <-> compensator
        self.local_parameters = dict()
        self.global_parameters = dict()
        self.compensation_parameters = dict()  # a dictionary with the same keys as the self.local parameters but with noise values
        self.data_type_parameters = dict()   # a dictionary with the same keys as the self.local parameters but with data_type vlaues

        # a flag configurable in each project step, to hide the local parameters of the step from the server
        self.compensator_flag = False

        # dtype of parameter, will set by the developer using set_compensator_flag(data_type)
        self.parameter_data_type = dict()

        # a flag which indicates whether the compensator ever used in the project.
        # if so, a dummy parameter will be sent to compensator in the Result step to enforce the compensator to share
        # its monitoring parameters from the previous step with the server. This way, the compensator time will not be ignored for
        # the last step it was used
        self.compensator_ever_used = False

        # standard deviation of the Gaussian distribution to generate noise
        # for negative integers and floating-point values
        # the value of this parameter can be changed by the corresponding setter function
        self.gaussian_std = 1e6

        # monitoring timers; they are reset in receive_parameters_from_server in communication round 1
        self.computation_timer = Timer(name='Computation')
        self.network_send_timer = Timer(name='Network Send')
        self.network_receive_timer = Timer(name='Network Receive')
        self.idle_timer = Timer('Idle')

        # server inquiry period and timeouts (in seconds)
        self.inquiry_period = 5
        self.inquiry_timeout = 60
        self.upload_parameters_timeout = 600
        self.download_parameters_timeout = 600
        self.download_result_timeout = 600

        # result and log directories
        self.result_dir = result_dir
        self.log_dir = log_dir

    # ####### Project/operation status functions
    def is_project_done(self):
        return self.project_status == ProjectStatus.DONE

    def is_operation_status_failed(self):
        return self.operation_status == OperationStatus.FAILED

    def is_operation_status_done(self):
        return self.operation_status == OperationStatus.DONE

    def is_client_operation_aborted(self):
        return self.client_operation == ClientOperation.ABORTED

    def set_operation_status_done(self):
        """ If current operation is in progress, then set it to Done """

        if self.operation_status == OperationStatus.IN_PROGRESS:
            self.operation_status = OperationStatus.DONE

    def set_operation_status_in_progress(self):
        """ If previous operation is Done, then set current operation status to In Progress """

        if self.operation_status == OperationStatus.DONE:
            self.operation_status = OperationStatus.IN_PROGRESS

    def set_operation_status_failed(self):
        """ is called whenever exception occurred in any function """

        self.log("Operation failed!")
        self.operation_status = OperationStatus.FAILED
        self.set_client_operation_aborted()

    def set_client_operation_aborted(self):
        self.log("Aborting ...")
        self.client_operation = ClientOperation.ABORTED

    # ####### Inquiry/download/upload period and timeout functions
    def set_inquiry_period(self, inquiry_period):
        self.inquiry_period = inquiry_period

    def set_inquiry_timeout(self, inquiry_timeout):
        self.inquiry_timeout = inquiry_timeout

    def set_upload_parameters_timeout(self, upload_parameters_timeout):
        self.upload_parameters_timeout = upload_parameters_timeout

    def set_download_parameters_timeout(self, download_parameters_timeout):
        self.download_parameters_timeout = download_parameters_timeout

    def set_download_result_timeout(self, download_result_timeout):
        self.download_result_timeout = download_result_timeout

    # ####### Keep track of idle time
    def wait(self, seconds):
        """ wait while keeping track of idle time """

        # don't count the waiting time in the 'Init' step
        # because it might be the case that not all participants clicked on 'Run' button yet
        if self.project_step == HyFedProjectStep.INIT:
            time.sleep(seconds)
            return

        self.idle_timer.start()
        time.sleep(seconds)
        self.idle_timer.stop()

    # ####### Run the client project
    def run(self):
        """ The main pipeline of the client project """

        # log the general info of the project such as participant username, project id, coordinator username, etc
        self.log_project_info()

        # (I) wait for server to start project
        self.wait_for_project_start()

        # if error occurred during the pickling of the authentication parameters, terminate the project run
        if self.is_operation_status_failed():
            return

        while True:

            # (II) download parameters from the server
            self.receive_parameters_from_server()

            # if error occurred during the pickling of the authentication parameters, terminate the project
            if self.is_operation_status_failed():
                return

            # if operation aborted because of
            # (1) inconsistency in project IDs, (2) inconsistency in the communication rounds, or
            # (3)  project failure/aborted status from the server, then terminate the project
            if self.is_client_operation_aborted():
                return

            # (III) compute local parameters
            self.compute_local_parameters()

            # client is done with the project after it performs finish-up tasks
            if self.project_step == HyFedProjectStep.FINISHED:
                return

            # (IV) share local parameters with the server and compensation parameters with compensator if self.compensator_flag is True
            self.send_client_parameters()

            # if error occurred during the pickling of the client parameters, terminate the project
            if self.is_operation_status_failed():
                return

    # ####### (I) Wait until server starts project (client <- server)
    def wait_for_project_start(self):
        """ Inquire the server until server tells the client that project started """

        self.client_operation = ClientOperation.WAITING_FOR_START
        self.log("\n######################## WAIT FOR PROJECT START ##########################\n", include_date=False)

        # initialize client authentication parameters
        try:
            request_body = {
                Parameter.AUTHENTICATION: {
                    AuthenticationParameter.USERNAME: self.username,
                    AuthenticationParameter.TOKEN: self.token,
                    AuthenticationParameter.PROJECT_ID: self.project_id
                }
            }
            serialized_request_body = pickle.dumps(request_body)
        except Exception as pickling_exp:
            self.log(f'\t{pickling_exp}\n')
            self.set_operation_status_failed()
            self.set_client_operation_aborted()
            return

        while True:
            try:
                # inquire the server periodically
                self.log("Inquiring the server to see whether project started ...")
                response = requests.get(url=f'{self.server_url}/{EndPoint.PROJECT_STARTED}',
                                        data=serialized_request_body,
                                        timeout=self.inquiry_timeout)

                if response.status_code == 200:
                    json_response = pickle.loads(response.content)
                    project_started = json_response[CoordinationParameter.PROJECT_STARTED]

                    if project_started:
                        self.log("\n######################## PROJECT STARTED ##########################\n",
                                 include_date=False)
                        return
                else:
                    self.log(f"Got {response.status_code} status code from the server!")

                time.sleep(self.inquiry_period)

            except Exception as exception:
                self.log(f"\t{exception}\n")
                time.sleep(self.inquiry_period)

    # ####### (II) Obtain the parameters from the server (client <- server)
    def receive_parameters_from_server(self):
        """ Obtain server parameters (i.e. coordination and global (if ready)) from the server """

        self.client_operation = ClientOperation.WAITING_FOR_AGGREGATION

        self.wait(seconds=self.inquiry_period)

        # initialize client authentication parameters
        serialized_client_parameters = self.prepare_server_parameters(sync_param_flag=True, monitoring_param_flag=False, local_param_flag=False)
        if self.is_operation_status_failed():
            self.set_client_operation_aborted()
            return

        # Obtain parameters from the server
        while True:
            try:
                if self.project_step != HyFedProjectStep.RESULT:
                    self.log("Inquiring the server to see whether global parameters are ready ...")

                self.network_receive_timer.start()
                response = requests.get(url=f'{self.server_url}/{EndPoint.GLOBAL_MODEL}',
                                        data=serialized_client_parameters,
                                        timeout=self.download_parameters_timeout)

            except Exception as network_exp:
                self.log(f'\t{network_exp}\n')
                self.network_receive_timer.ignore()
                self.wait(seconds=self.inquiry_period)
                continue

            if response.status_code != 200:
                self.log(f"Got {response.status_code} status code from the server!")
                self.network_receive_timer.ignore()
                self.wait(seconds=self.inquiry_period)
                continue

            # deserialize the server response
            try:
                self.computation_timer.start()

                # extract coordination parameters
                server_parameters = pickle.loads(response.content)
                coordination_parameters = server_parameters[Parameter.COORDINATION]
                server_project_id = coordination_parameters[CoordinationParameter.PROJECT_ID]
                server_project_status = coordination_parameters[CoordinationParameter.PROJECT_STATUS]
                server_project_step = coordination_parameters[CoordinationParameter.PROJECT_STEP]
                server_comm_round = coordination_parameters[CoordinationParameter.COMM_ROUND]

                self.computation_timer.stop()

            except Exception as unpickling_exception:
                self.log(f'\t{unpickling_exception}\n')
                self.computation_timer.stop()
                self.network_receive_timer.ignore()
                self.wait(seconds=self.inquiry_period)
                continue

            # make sure the client is synced with the server,
            # i.e. the same project id as well as communication round difference of at most 1 )
            self.computation_timer.start()

            if server_project_id != self.project_id:
                self.log("The project ID from the server and client do not match!")
                self.computation_timer.stop()
                self.network_receive_timer.ignore()
                self.set_client_operation_aborted()
                return

            if not (0 <= server_comm_round - self.comm_round <= 1):
                self.log("The difference between server and client communication rounds must be at most 1!")
                self.computation_timer.stop()
                self.network_receive_timer.ignore()
                self.set_client_operation_aborted()
                return

            # if the project is abort or failed at the server side, return
            if server_project_status == ProjectStatus.FAILED or server_project_status == ProjectStatus.ABORTED:
                self.project_status = server_project_status
                self.log(f"Got project {server_project_status} status from the server!")
                self.computation_timer.stop()
                self.network_receive_timer.ignore()
                self.set_client_operation_aborted()
                return

            # if the communication round at the server and client are the same,
            # the global parameters are not ready, so continue inquiring the server
            if server_comm_round == self.comm_round:

                if self.project_step != HyFedProjectStep.RESULT:
                    self.log("Not ready!")

                self.project_status = server_project_status
                self.computation_timer.stop()
                self.network_receive_timer.ignore()
                self.wait(seconds=self.inquiry_period)
                continue

            # if parameters are ready, sync with the server and extract global parameters
            if server_comm_round == self.comm_round + 1:

                if self.project_step != HyFedProjectStep.RESULT:
                    self.log("Ready!")

                self.network_receive_timer.stop()

                # reset timers in the first communication round
                if server_comm_round == 1:
                    self.computation_timer.reset()
                    self.network_send_timer.reset()
                    self.network_receive_timer.reset()
                    self.idle_timer.reset()

                # sync with server
                self.comm_round = server_comm_round
                self.project_step = server_project_step
                self.project_status = server_project_status

                # set global parameters
                self.global_parameters = server_parameters[Parameter.GLOBAL]

                # computation timer already stopped during reset in communication round 1, so just stop the timer in
                # comm_round > 1
                if server_comm_round != 1:
                    self.computation_timer.stop()

                # update total duration of the timers
                # ignore timer values in Finished step and the step before (i.e. Result)
                if server_project_step != HyFedProjectStep.FINISHED:
                    self.computation_timer.new_round()
                    self.network_send_timer.new_round()
                    self.network_receive_timer.new_round()
                    self.idle_timer.new_round()

                return

    # ####### (III) compute local model parameters
    def pre_compute_local_parameters(self):
        """
            Perform necessary operations to prepare client for computing the local parameters;
            MUST be called before compute_local_parameters function in the derived class
        """

        self.client_operation = ClientOperation.COMPUTING_PARAMETERS
        self.computation_timer.start()
        self.set_operation_status_in_progress()
        self.local_parameters = dict()
        self.compensation_parameters = dict()
        self.data_type_parameters = dict()
        self.unset_compensator_flag()
        self.log(f"######### Communication round # {self.comm_round }")
        self.log(f"### Step: {self.project_step}")

        if not (self.project_step == HyFedProjectStep.RESULT or self.project_step == HyFedProjectStep.FINISHED):
            self.log("Computing local model parameters ...")

    def compute_local_parameters(self):
        """  Compute local parameters from the local data; Will be OVERRIDDEN in the derived class """

        try:

            self.pre_compute_local_parameters()  # MUST be called BEFORE step functions

            # ############## HyFed local parameter computation steps
            if self.project_step == HyFedProjectStep.INIT:
                pass
            elif self.project_step == HyFedProjectStep.RESULT:
                self.result_step()  # the result step downloads the result file as zip
            elif self.project_step == HyFedProjectStep.FINISHED:
                self.finished_step()  # The operations in the last step of the project

            self.post_compute_local_parameters()  # # MUST be called AFTER step functions
        except Exception as compute_exception:
            self.log(compute_exception)
            self.set_operation_status_failed()
            self.post_compute_local_parameters()

    def post_compute_local_parameters(self):
        """
            Perform operations necessary after computing the local parameters;
            MUST be called after compute_local_parameters function in the derived class
        """

        self.set_operation_status_done()
        self.computation_timer.stop()

        if not (self.project_step == HyFedProjectStep.RESULT or self.project_step == HyFedProjectStep.FINISHED):
            if self.is_operation_status_done():
                self.log("Done!")
            else:
                self.log("Failed!")

    def result_step(self):
        """ Download the result file (as zip) from the server and save it in the result directory in the Result step """

        self.client_operation = ClientOperation.DOWNLOADING_RESULTS

        # prepare authentication parameters
        try:
            request_body = {
                Parameter.AUTHENTICATION: {
                    AuthenticationParameter.USERNAME: self.username,
                    AuthenticationParameter.TOKEN: self.token,
                    AuthenticationParameter.PROJECT_ID: self.project_id
                }
            }
            serialized_request_body = pickle.dumps(request_body)

        except Exception as pickling_exp:
            self.log(f'\t{pickling_exp}\n')
            self.set_operation_status_failed()
            self.set_client_operation_aborted()
            return

        # get the result zip file from the server
        while True:
            try:
                self.log(f"Downloading result zip file ...")
                result_url = f'{self.server_url}/{EndPoint.RESULT_DOWNLOAD}'

                response = requests.get(url=result_url,
                                        data=serialized_request_body,
                                        timeout=self.download_result_timeout)

                if response.status_code == 200:
                    self.log("Done!")
                    break
                else:
                    self.log(f"Failed: Got {response.status_code} status code from the server!")
                    time.sleep(self.inquiry_period)

            except Exception as exception:
                self.log(f"\t{exception}\n")
                time.sleep(self.inquiry_period)

        try:
            # create result directory
            Path(self.result_dir).mkdir(parents=True, exist_ok=True)
            os.chmod(self.result_dir, 0o700)

            # save the result file into the result directory
            self.log("Saving the result zip file ...")
            result_file_path = f'{self.result_dir}/result-{self.project_id}.zip'
            with open(result_file_path, 'wb') as result_file:
                result_file.write(response.content)

            self.log("Done!")

        except Exception as file_exp:
            self.log("Failed!")
            self.log(f"\t{file_exp}\n")
            self.set_operation_status_failed()
            self.set_client_operation_aborted()
            return

    def finished_step(self):
        """ Perform necessary operations in the finished step of the project """

        self.client_operation = ClientOperation.FINISHING_UP
        self.log_timers()
        if self.is_project_done():
            self.log("\n######################## PROJECT COMPLETED ##########################\n", include_date=False)

        self.save_log()
        self.client_operation = ClientOperation.DONE

    # ####### (IV) Share (noisy) local parameters with server and compensation parameters with compensator
    def send_parameters_to_server(self):
        """ Send (noisy) local, auth, sync, and monitoring parameters to the server """

        server_parameters_serialized = self.prepare_server_parameters()
        if self.is_operation_status_failed():
            return

        self.client_operation = ClientOperation.SENDING_PARAMETERS

        while True:
            try:
                if self.is_compensator_flag_set():
                    self.log("Sending NOISY LOCAL MODEL parameters to the SERVER ...")
                else:
                    if self.project_step != HyFedProjectStep.RESULT:
                        self.log("Sending LOCAL MODEL parameters to the SERVER ...")

                self.network_send_timer.start()
                response = requests.post(url=f'{self.server_url}/{EndPoint.MODEL_AGGREGATION}',
                                         data=server_parameters_serialized,
                                         timeout=self.upload_parameters_timeout)
                self.network_send_timer.stop()

                if response.status_code == 200:
                    self.log("Done!")
                    return
                else:
                    self.log(f"Failed: got {response.status_code} status code from the server!")
                    self.wait(self.inquiry_period)

            except Exception as exception:
                self.log("Failed!")
                self.log(f"\t{exception}")
                self.network_send_timer.stop()
                self.wait(self.inquiry_period)

    def send_parameters_to_compensator(self):
        """ Send compensation, auth, and sync parameters to the compensator """

        compensator_parameters_serialized = self.prepare_compensator_parameters()
        if self.is_operation_status_failed():
            return

        self.client_operation = ClientOperation.SENDING_PARAMETERS

        while True:
            try:
                self.log("Sending NOISE values to the COMPENSATOR ...")

                self.network_send_timer.start()
                response = requests.post(url=f'{self.compensator_url}/{EndPoint.NOISE_AGGREGATION}',
                                         data=compensator_parameters_serialized,
                                         timeout=self.upload_parameters_timeout)
                self.network_send_timer.stop()

                if response.status_code == 200:
                    response_json = pickle.loads(response.content)
                    should_retry = response_json[SyncParameter.SHOULD_RETRY]

                    if not should_retry:
                        self.log("Done!")
                        return
                    else:
                        self.log("Should retry!")
                        self.wait(self.inquiry_period)

                else:
                    self.log(f"Failed: Got {response.status_code} status code from the compensator!")
                    self.wait(self.inquiry_period)

            except Exception as exception:
                self.log("Failed!")
                self.log(f"\t{exception}")
                self.network_send_timer.stop()
                self.wait(self.inquiry_period)

    def send_client_parameters(self):
        """ Send client parameters to the server | compensator """

        # to enforce the compensator to send its monitoring parameters to the server
        # so that its computation and network time from the last step it was used is considered
        if self.compensator_ever_used and self.project_step == HyFedProjectStep.RESULT:
            self.set_compensator_flag({})

        if self.compensator_flag:
            # add noise to the local model parameters
            self.make_local_parameters_noisy()
            if self.is_operation_status_failed():
                self.log("Failed!")
                return

            self.log("Done!")

            # randomly select the order of sending parameters to server/compensator
            if np.random.randint(2) == 0:
                self.send_parameters_to_server()
                self.send_parameters_to_compensator()
            else:
                self.send_parameters_to_compensator()
                self.send_parameters_to_server()
        else:
            self.send_parameters_to_server()

    # ####### Compensator related functions
    def set_compensator_flag(self, data_type):
        self.compensator_flag = True
        self.compensator_ever_used = True
        self.parameter_data_type = data_type

    def unset_compensator_flag(self):
        self.compensator_flag = False
        self.parameter_data_type = dict()

    def is_compensator_flag_set(self):
        return self.compensator_flag

    def make_local_parameters_noisy(self):
        """ Add HIGH noise to the local parameter values """

        self.client_operation = ClientOperation.PREPARING_PARAMETERS

        try:
            self.log("Making the local model highly NOISY ...")
            self.computation_timer.start()

            # for each local parameter, do
            for local_parameter_name in self.local_parameters.keys():

                # get the value(s) of the local parameter
                local_parameter_values = self.local_parameters[local_parameter_name]

                # make the local model parameters noisy
                noisy_local_parameter_values, noise_values = make_noisy(local_parameter_values,
                                                                        self.parameter_data_type[local_parameter_name],
                                                                        self.gaussian_std)

                # if error occurred in making the parameter value noisy, fail project
                if noisy_local_parameter_values is None or noise_values is None:
                    self.log("Unsupported local parameter format!")
                    self.log("The local model parameter values must be:")
                    self.log("(1) scalar, e.g. 3 or 4.5")
                    self.log("(2) numpy array, e.g. array([1,2,3]) or array([[3.2, 4.1], [1.1, 4.5, 5.6]])")
                    self.log("(3) list of numpy arrays, e.g. [array([1,2,3]), array([1.2, 3.4])]")
                    self.set_operation_status_failed()
                    self.set_client_operation_aborted()
                    return

                # put noisy local model values in the local parameters
                self.local_parameters[local_parameter_name] = noisy_local_parameter_values

                # add noise values to the compensation parameters
                self.compensation_parameters[local_parameter_name] = noise_values

                # add data type info of the local parameter into data_type parmaeters
                self.data_type_parameters[local_parameter_name] = self.parameter_data_type[local_parameter_name]

            self.computation_timer.stop()

        except Exception as noise_exp:
            self.log("Failed!")
            self.log(f'\t{noise_exp}\n')
            self.computation_timer.stop()
            self.set_operation_status_failed()
            self.set_client_operation_aborted()

    # ####### Helper functions
    def prepare_server_parameters(self, sync_param_flag=True, monitoring_param_flag=True, local_param_flag=True):
        """ Prepare the parameters shared with the server """

        self.client_operation = ClientOperation.PREPARING_PARAMETERS

        try:
            self.computation_timer.start()

            # initialize authentication parameters
            authentication_parameters = dict()
            authentication_parameters[AuthenticationParameter.PROJECT_ID] = self.project_id
            authentication_parameters[AuthenticationParameter.USERNAME] = self.username
            authentication_parameters[AuthenticationParameter.TOKEN] = self.token

            # initialize synchronization parameters
            sync_parameters = dict()

            if sync_param_flag:
                sync_parameters[SyncParameter.PROJECT_STEP] = self.project_step
                sync_parameters[SyncParameter.COMM_ROUND] = self.comm_round
                sync_parameters[SyncParameter.OPERATION_STATUS] = self.operation_status
                sync_parameters[SyncParameter.COMPENSATOR_FLAG] = self.compensator_flag

            # initialize monitoring parameters
            monitoring_parameters = dict()

            if monitoring_param_flag:
                monitoring_parameters[MonitoringParameter.COMPUTATION_TIME] = self.computation_timer.get_total_duration()
                monitoring_parameters[MonitoringParameter.NETWORK_SEND_TIME] = self.network_send_timer.get_total_duration()
                monitoring_parameters[MonitoringParameter.NETWORK_RECEIVE_TIME] = self.network_receive_timer.get_total_duration()
                monitoring_parameters[MonitoringParameter.IDLE_TIME] = self.idle_timer.get_total_duration()

            # initialize local model parameters
            local_parameters = dict()
            if local_param_flag:
                local_parameters = self.local_parameters

            # server parameters in json
            parameters_json = {Parameter.AUTHENTICATION: authentication_parameters,
                               Parameter.SYNCHRONIZATION: sync_parameters,
                               Parameter.MONITORING: monitoring_parameters,
                               Parameter.LOCAL: local_parameters
                               }
            parameters_serialized = pickle.dumps(parameters_json)

            self.computation_timer.stop()

            return parameters_serialized

        except Exception as pickling_exp:
            self.log(f'\t{pickling_exp}\n')
            self.computation_timer.stop()
            self.set_operation_status_failed()
            self.set_client_operation_aborted()

    def prepare_compensator_parameters(self):
        """ Prepare the parameters shared with the compensator """

        self.client_operation = ClientOperation.PREPARING_PARAMETERS

        try:
            self.computation_timer.start()

            # initialize authentication parameters
            authentication_parameters = dict()

            hash_project_id = hashlib.sha256(self.project_id.encode('utf-8')).hexdigest()
            hash_username = hashlib.sha256(self.username.encode('utf-8')).hexdigest()
            hash_token = hashlib.sha256(self.token.encode('utf-8')).hexdigest()

            authentication_parameters[AuthenticationParameter.HASH_PROJECT_ID] = hash_project_id
            authentication_parameters[AuthenticationParameter.HASH_USERNAME] = hash_username
            authentication_parameters[AuthenticationParameter.HASH_TOKEN] = hash_token

            # initialize synchronization parameters
            sync_parameters = dict()
            sync_parameters[SyncParameter.PROJECT_STEP] = self.project_step
            sync_parameters[SyncParameter.COMM_ROUND] = self.comm_round

            # initialize connection parameters
            connection_parameters = dict()
            connection_parameters[ConnectionParameter.SERVER_URL] = self.server_url

            # compensator parameters in json
            parameters_json = {Parameter.AUTHENTICATION: authentication_parameters,
                               Parameter.SYNCHRONIZATION: sync_parameters,
                               Parameter.CONNECTION: connection_parameters,
                               Parameter.COMPENSATION: self.compensation_parameters,
                               Parameter.DATA_TYPE: self.data_type_parameters
                               }
            parameters_serialized = pickle.dumps(parameters_json)

            self.computation_timer.stop()

            return parameters_serialized

        except Exception as pickling_exp:
            self.log(f'\t{pickling_exp}\n')
            self.computation_timer.stop()
            self.set_operation_status_failed()
            self.set_client_operation_aborted()

    # ####### log functions
    def log(self, message, include_date=True):
        """ Add message to the log list """

        if include_date:
            current_time = datetime.datetime.today().strftime("[%d/%b/%Y %H:%M:%S]")
            log_message = f'{current_time}   {message}'
        else:
            log_message = message

        self.log_message_list += [log_message]

    def log_project_info(self):
        """ Put the general info of the project at the beginning of the log file/widget """

        self.log(f'Server URL: {self.server_url}', include_date=False)
        self.log(f'Compensator URL: {self.compensator_url}', include_date=False)
        self.log(f'Participant: {self.username}', include_date=False)
        self.log(f'Coordinator: {self.coordinator}', include_date=False)
        self.log(f'Project ID: {self.project_id}', include_date=False)
        self.log(f'Token: {self.token}', include_date=False)
        self.log(f'Tool: {self.tool}', include_date=False)
        self.log(f'Algorithm: {self.algorithm}', include_date=False)
        self.log(f'Project name: {self.name}', include_date=False)
        self.log(f'Project description: {self.description}', include_date=False)

        self.log("\n", include_date=False)

    def log_timers(self):
        """ Put timer values at the end of the log widget/file """

        self.log("\nRuntime (seconds)", include_date=False)
        self.log(f"Computation time: {self.computation_timer.get_total_duration()}", include_date=False)
        self.log(f"Network send time: {self.network_send_timer.get_total_duration()}", include_date=False)
        self.log(f"Network receive time: {self.network_receive_timer.get_total_duration()}", include_date=False)
        self.log(f"Idle time: {self.idle_timer.get_total_duration()}", include_date=False)

    def save_log(self, file_path=None):
        """ Save log file """

        try:
            if file_path is None:
                # create log directory
                Path(self.log_dir).mkdir(parents=True, exist_ok=True)
                os.chmod(self.log_dir, 0o700)

                # create log file path
                log_file_path = f"{self.log_dir}/{self.project_id}.log"
            else:
                log_file_path = f"{file_path}"

            # open log file
            log_file = open(log_file_path, 'w')

            # write log messages to the log file
            for message in self.log_message_list:
                log_file.write(f'{message}\n')

            # close log file
            log_file.close()
        except Exception as io_exception:
            self.log(io_exception)
            self.set_operation_status_failed()

    # ####### setter functions
    def set_gaussian_std(self, gaussian_std):
        if gaussian_std < 1000:
            self.gaussian_std = 1000
        else:
            self.gaussian_std = gaussian_std

    # ####### getter functions
    def get_name(self):
        return self.name

    def get_description(self):
        return self.description

    def get_algorithm(self):
        return self.algorithm

    def get_comm_round(self):
        return self.comm_round

    def get_project_status(self):
        return self.project_status

    def get_project_step(self):
        return self.project_step

    def get_project_status_text(self):
        """ Customized text to be shown in status widget for project status """

        if self.client_operation == ClientOperation.SENDING_PARAMETERS:
            return '-'

        if self.client_operation == ClientOperation.WAITING_FOR_AGGREGATION and self.project_status == ProjectStatus.PARAMETERS_READY:
            return '-'

        return self.project_status

    def get_project_step_text(self):
        """ Customized text to be shown in status widget for project step """

        if self.operation_status == ClientOperation.WAITING_FOR_START:
            return '-'

        return self.project_step

    def get_client_operation(self):
        return self.client_operation

    def get_log_message_list(self):
        return self.log_message_list
