"""
    Parameters exchanged client <-> server

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


class Parameter:
    """
        There are seven general categories of the parameters exchanged between the clients and the server:
        client -> server: authentication, synchronization, monitoring, and local parameters
        server -> client: coordination, project, global parameters
    """

    AUTHENTICATION = "authentication_parameter"
    SYNCHRONIZATION = "synchronization_parameter"
    MONITORING = "monitoring_parameter"
    LOCAL = "local_parameter"
    PROJECT = "project_parameter"
    COORDINATION = "coordination_parameter"
    GLOBAL = "global_parameter"


class AuthenticationParameter:
    """ Client -> server parameters to authenticate the client """

    USERNAME = "username"
    PASSWORD = "password"
    PROJECT_ID = "project_id"
    TOKEN = "token"


class SyncParameter:
    """ Client -> server parameters to ensure the clients and server are synced """

    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"
    OPERATION_STATUS = "operation_status"


class MonitoringParameter:
    """ Client -> server parameters to breakdown the runtime  of the client """

    COMPUTATION_TIME = "computation_time"
    NETWORK_SEND_TIME = "network_send_time"
    NETWORK_RECEIVE_TIME = "network_receive_time"
    IDLE_TIME = "idle_time"


class HyFedProjectParameter:
    """ Server -> client project info parameters """

    ID = "id"
    ALGORITHM = "algorithm"
    NAME = "name"
    DESCRIPTION = "description"
    COORDINATOR = "coordinator"


class CoordinationParameter:
    """ Server -> client parameters for coordination purposes """

    PROJECT_ID = "project_id"
    PROJECT_STATUS = "project_status"
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"
    PROJECT_STARTED = "project_started"
    CLIENT_JOINED = "client_joined"


class ConnectionParameter:
    """ Only used in the client """
    SERVER_NAME = "server_name"
    SERVER_URL = "server_url"


class ClientParameter:
    """
        A class to bundle client parameters including authentication, sync, monitoring, and local parameters
        that are sent to the server in each communication round
    """

    def __init__(self):
        self.authentication_parameters = {}
        self.sync_parameters = {}
        self.monitoring_parameters = {}
        self.local_parameters = {}

    def set_authentication_parameters(self, username, token, project_id):
        self.authentication_parameters[AuthenticationParameter.USERNAME] = username
        self.authentication_parameters[AuthenticationParameter.TOKEN] = token
        self.authentication_parameters[AuthenticationParameter.PROJECT_ID] = project_id

    def set_sync_parameters(self, project_step, comm_round, operation_status):
        self.sync_parameters[SyncParameter.PROJECT_STEP] = project_step
        self.sync_parameters[SyncParameter.COMM_ROUND] = comm_round
        self.sync_parameters[SyncParameter.OPERATION_STATUS] = operation_status

    def set_monitoring_parameters(self, computation_time, network_send_time, network_receive_time, idle_time):
        self.monitoring_parameters[MonitoringParameter.COMPUTATION_TIME] = computation_time
        self.monitoring_parameters[MonitoringParameter.NETWORK_SEND_TIME] = network_send_time
        self.monitoring_parameters[MonitoringParameter.NETWORK_RECEIVE_TIME] = network_receive_time
        self.monitoring_parameters[MonitoringParameter.IDLE_TIME] = idle_time

    def set_local_parameters(self, local_parameters):
        self.local_parameters = local_parameters

    def jsonify_parameters(self):
        return {Parameter.AUTHENTICATION: self.authentication_parameters,
                Parameter.SYNCHRONIZATION: self.sync_parameters,
                Parameter.MONITORING: self.monitoring_parameters,
                Parameter.LOCAL: self.local_parameters}
