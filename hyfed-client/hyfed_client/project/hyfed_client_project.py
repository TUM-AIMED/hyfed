"""
    A class providing the essential functionalities of the client such as sending client parameters,
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
from hyfed_client.util.hyfed_parameters import Parameter, CoordinationParameter, ClientParameter,\
    AuthenticationParameter
from hyfed_client.util.hyfed_steps import HyFedProjectStep
from hyfed_client.util.monitoring import Timer
from hyfed_client.util.operation import ClientOperation
from hyfed_client.util.endpoint import EndPoint

import pickle
import requests
import datetime
import time
import os
from pathlib import Path


class HyFedClientProject:
    """ A base class providing the basic functionalities of the client package for communication with the server """

    def __init__(self, username, token, project_id, server_url,
                 algorithm, name, description,  coordinator,
                 result_dir, log_dir):

        """ authentication parameters """
        self.username = username
        self.token = token
        self.project_id = project_id

        """ connection parameter """
        self.server_url = server_url

        """ project parameters """
        self.algorithm = algorithm
        self.name = name
        self.description = description
        self.coordinator = coordinator

        """ sync parameters """
        self.operation_status = OperationStatus.DONE
        self.project_step = HyFedProjectStep.INIT
        self.comm_round = 0
        self.project_status = ProjectStatus.CREATED

        """  current operation of the client """
        self.client_operation = ClientOperation.WAITING_FOR_START

        """ for logging """
        self.log_message_list = []

        """ model parameters exchanged between client and server """
        self.local_parameters = {}
        self.global_parameters = {}

        """ monitoring timers; they are reset in receive_server_parameters in communication round 1 """
        self.computation_timer = Timer(name='Computation')
        self.network_send_timer = Timer(name='Network Send')
        self.network_receive_timer = Timer(name='Network Receive')
        self.idle_timer = Timer('Idle')

        """ server inquiry period and timeouts (in seconds) """
        self.inquiry_period = 5
        self.inquiry_timeout = 60
        self.upload_parameters_timeout = 600
        self.download_parameters_timeout = 600
        self.download_result_timeout = 600

        """ result and log directories """
        self.result_dir = result_dir
        self.log_dir = log_dir

    # ####### project/operation status functions
    def is_project_done(self):
        return self.project_status == ProjectStatus.DONE

    def is_operation_failed(self):
        return self.operation_status == OperationStatus.FAILED

    def is_client_operation_aborted(self):
        return self.client_operation == ClientOperation.ABORTED

    def set_operation_status_done(self):
        """ If current operation is not failed/aborted, then set it to Done """

        if self.operation_status == OperationStatus.IN_PROGRESS:
            self.operation_status = OperationStatus.DONE

    def set_operation_status_in_progress(self):
        """ If previous operation is not failed/aborted, then set current operation status to In Progress """

        if self.operation_status == OperationStatus.DONE:
            self.operation_status = OperationStatus.IN_PROGRESS

    def set_operation_status_failed(self):
        self.log("Operation failed!")
        self.operation_status = OperationStatus.FAILED

    def set_client_operation_aborted(self):
        self.log("Aborting ...")
        self.client_operation = ClientOperation.ABORTED

    # ####### inquiry/download/upload period and timeout functions
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

    # ####### keep track of idle time
    def wait(self, seconds):
        """ wait while keeping track of idle time """

        self.idle_timer.start()
        time.sleep(seconds)
        self.idle_timer.stop()

    # ####### run the client project
    def run(self):
        """ run the client project """

        # log the general info of the project such as participant username, project id, coordinator username, etc
        self.log_project_info()

        # (I) Wait for server to start project
        self.wait_for_project_start()

        # if error occurred during the pickling of the authentication parameters, terminate the project run
        if self.is_operation_failed():
            return

        while True:
            # (II) download parameters from the serer
            self.receive_server_parameters()

            # if error occurred during the pickling of the authentication parameters, terminate the project
            if self.is_operation_failed():
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

            # (IV) share local parameters with the server
            self.send_client_parameters()

            # if error occurred during the pickling of the client parameters, terminate the project
            if self.is_operation_failed():
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

                if response.status_code != 200:
                    self.log(f"Got {response.status_code} status code from the server!")
                    time.sleep(self.inquiry_period)
                    continue

                json_response = pickle.loads(response.content)
                project_started = json_response[CoordinationParameter.PROJECT_STARTED]

                if project_started:
                    self.log("\n######################## PROJECT STARTED ##########################\n",
                             include_date=False)
                    return

                time.sleep(self.inquiry_period)

            except Exception as exception:
                self.log(f"\t{exception}\n")
                time.sleep(self.inquiry_period)

    # ####### (II) Obtain the parameters from the server (client <- server)
    def receive_server_parameters(self):
        """ Obtain server parameters (i.e. coordination and global (if ready)) from the server """

        self.client_operation = ClientOperation.WAITING_FOR_AGGREGATION

        self.wait(seconds=self.inquiry_period)

        # initialize client authentication parameters
        try:
            self.computation_timer.start()

            client_parameters = ClientParameter()
            client_parameters.set_authentication_parameters(username=self.username,
                                                            project_id=self.project_id,
                                                            token=self.token)
            serialized_client_parameters = pickle.dumps(client_parameters.jsonify_parameters())

            self.computation_timer.stop()
        except Exception as pickling_exp:
            self.log(f'\t{pickling_exp}\n')
            self.computation_timer.stop()
            self.set_operation_status_failed()
            self.set_client_operation_aborted()
            return

        while True:

            # Obtain parameters from the server
            try:
                self.log("Inquiring the server to see whether global parameters are ready ...")
                self.network_receive_timer.start()

                response = requests.get(url=f'{self.server_url}/{EndPoint.GLOBAL_MODEL}',
                                        data=serialized_client_parameters,
                                        timeout=self.download_parameters_timeout)

                self.network_receive_timer.stop()

            except Exception as network_exp:
                self.log(f'\t{network_exp}\n')
                self.network_receive_timer.stop()
                self.wait(seconds=self.inquiry_period)
                continue

            if response.status_code != 200:
                self.log(f"Got {response.status_code} status code from the server!")
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
                self.wait(seconds=self.inquiry_period)
                continue

            # make sure the client is synced with the server,
            # i.e. the same project id as well as communication round difference of at most 1 )
            self.computation_timer.start()

            if server_project_id != self.project_id:
                self.log("The project ID from the server and client do not match!")
                self.computation_timer.stop()
                self.set_client_operation_aborted()
                return

            if not (0 <= server_comm_round - self.comm_round <= 1):
                self.log("The difference between server and client communication rounds must be at most 1!")
                self.computation_timer.stop()
                self.set_client_operation_aborted()
                return

            # if the project is abort or failed at the server side, return
            if server_project_status == ProjectStatus.FAILED or server_project_status == ProjectStatus.ABORTED:
                self.project_status = server_project_status
                self.log(f"Got project {server_project_status} status from the server!")
                self.computation_timer.stop()
                self.set_client_operation_aborted()
                return

            # if the communication round at the server and client are the same,
            # the global parameters are not ready, so continue inquiring the server
            if server_comm_round == self.comm_round:
                self.log("Global parameters are NOT ready!")
                self.project_status = server_project_status
                self.computation_timer.stop()
                self.wait(seconds=self.inquiry_period)
                continue

            # if parameters are ready, sync with the server and extract global parameters
            if server_comm_round == self.comm_round + 1:
                self.log("Global parameters ready!")
                self.log(f"Starting communication round {server_comm_round} ...")

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
                global_parameters = server_parameters[Parameter.GLOBAL]
                self.global_parameters = global_parameters

                # computation timer already stopped during reset in communication round 1, so just re-stop the timer in
                # comm_round > 1
                if server_comm_round != 1:
                    self.computation_timer.stop()

                # update total duration of the timers
                # ignore timer values in Result and Finished steps
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

        self.client_operation = ClientOperation.COMPUTING_LOCAL_PARAMETERS
        self.computation_timer.start()
        self.set_operation_status_in_progress()
        self.local_parameters = {}
        self.log(f"######### Step {self.project_step }")

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
            self.post_compute_local_parameters()
            self.set_operation_status_failed()

    def post_compute_local_parameters(self):
        """
            Perform operations necessary after computing the local parameters;
            MUST be called after compute_local_parameters function in the derived class
        """

        self.set_operation_status_done()
        self.computation_timer.stop()

    def result_step(self):
        """ Download the result file (as zip) from the server and save it in the result directory in the Result step """

        self.set_operation_status_in_progress()
        self.client_operation = ClientOperation.DOWNLOADING_RESULTS

        # prepare authentication parameters
        try:
            request_data = {
                Parameter.AUTHENTICATION: {
                    AuthenticationParameter.USERNAME: self.username,
                    AuthenticationParameter.TOKEN: self.token,
                    AuthenticationParameter.PROJECT_ID: self.project_id
                }
            }
            serialized_request_data = pickle.dumps(request_data)

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
                                        data=serialized_request_data,
                                        timeout=self.download_result_timeout)

                if response.status_code != 200:
                    self.log(f"Got {response.status_code} status code from the server!")
                    time.sleep(self.inquiry_period)
                    continue
                else:
                    self.log("Done!")
                    break

            except Exception as exception:
                self.log(f"\t{exception}\n")
                time.sleep(self.inquiry_period)

        # save the result file
        try:
            self.log("Saving the result zip file ...")
            result_file_path = f'{self.result_dir}/result-{self.project_id}.zip'
            with open(result_file_path, 'wb') as result_file:
                result_file.write(response.content)

            self.log("Done!")

        except Exception as file_exp:
            self.log(f"\t{file_exp}\n")
            self.set_operation_status_failed()
            self.set_client_operation_aborted()
            return

        self.set_operation_status_done()

    def finished_step(self):
        """ Perform necessary operations in the finished step of the project """

        self.client_operation = ClientOperation.FINISHING_UP
        self.log_timers()
        if self.is_project_done():
            self.log("\n######################## PROJECT COMPLETED ##########################\n", include_date=False)

        self.save_log()
        self.set_operation_status_done()
        self.client_operation = ClientOperation.DONE

    # ####### (IV) share client parameters with the server (client -> server)
    def send_client_parameters(self):
        """ Send client parameters (authentication, sync, monitoring, and local) to the server """

        self.client_operation = ClientOperation.SENDING_LOCAL_PARAMETERS

        try:
            self.computation_timer.start()

            # prepare client parameters
            client_parameters = ClientParameter()
            client_parameters.set_authentication_parameters(username=self.username,
                                                            project_id=self.project_id,
                                                            token=self.token)
            client_parameters.set_sync_parameters(project_step=self.project_step,
                                                  comm_round=self.comm_round,
                                                  operation_status=self.operation_status)

            client_parameters.set_monitoring_parameters(computation_time=self.computation_timer.get_total_duration(),
                                                        network_send_time=self.network_send_timer.get_total_duration(),
                                                        network_receive_time=self.network_receive_timer.get_total_duration(),
                                                        idle_time=self.idle_timer.get_total_duration())

            client_parameters.set_local_parameters(local_parameters=self.local_parameters)

            serialized_client_parameters = pickle.dumps(client_parameters.jsonify_parameters())

            self.computation_timer.stop()

        except Exception as pickling_exp:
            self.log(f'\t{pickling_exp}\n')
            self.computation_timer.stop()
            self.set_operation_status_failed()
            self.set_client_operation_aborted()
            return

        while True:
            try:
                self.log("Sending client parameter values to the server ...")

                self.network_send_timer.start()
                response = requests.post(url=f'{self.server_url}/{EndPoint.MODEL_AGGREGATION}',
                                         data=serialized_client_parameters,
                                         timeout=self.upload_parameters_timeout)
                self.network_send_timer.stop()

                if response.status_code == 200:
                    self.log("Successful!")
                    return
                else:
                    self.log(f"got {response.status_code} status code from the server!")
                    self.wait(self.inquiry_period)
                    continue

            except Exception as exception:
                self.log(f"\t{exception}")
                self.network_send_timer.stop()
                self.wait(self.inquiry_period)

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
        self.log(f'Participant: {self.username}', include_date=False)
        self.log(f'Coordinator: {self.coordinator}', include_date=False)
        self.log(f'Project ID: {self.project_id}', include_date=False)
        self.log(f'Token: {self.token}', include_date=False)
        self.log(f'Project name: {self.name}', include_date=False)
        self.log(f'Project description: {self.description}', include_date=False)
        self.log(f'Algorithm: {self.algorithm}', include_date=False)

        self.log("\n", include_date=False)

    def log_timers(self):
        """ Put timer values at the end of the log widget/file """

        self.log("\nRuntime (seconds)", include_date=False)
        self.log(f"Computation time: {self.computation_timer.get_total_duration()}", include_date=False)
        self.log(f"Network send time: {self.network_send_timer.get_total_duration()}", include_date=False)
        self.log(f"Network receive time: {self.network_receive_timer.get_total_duration()}", include_date=False)
        self.log(f"Idle time: {self.idle_timer.get_total_duration()}", include_date=False)

    def save_log(self):
        """ Save log file """

        try:
            # create log directory
            Path(self.log_dir).mkdir(parents=True, exist_ok=True)
            os.chmod(self.log_dir, 0o700)

            # open log file
            log_file_path = f"{self.log_dir}/{self.project_id}.log"
            log_file = open(log_file_path, 'w')

            # write log messages to the log file
            for message in self.log_message_list:
                log_file.write(f'{message}\n')

            # close log file
            log_file.close()
        except Exception as io_exception:
            self.log(io_exception)
            self.set_operation_status_failed()

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

        if self.client_operation == ClientOperation.SENDING_LOCAL_PARAMETERS:
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
