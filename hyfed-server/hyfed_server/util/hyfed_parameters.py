"""
    Parameters exchanged client <-> server and webapp <-> server

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
        There are seven general categories of the parameters exchanged between the clients and the server
         or from the server to the webapp:
         client -> server: authentication, synchronization, monitoring, and local parameters
         server -> client: coordination, project, global parameters
         webapp -> server: authentication and project parameters
         server -> webapp: project parameters
    """
    AUTHENTICATION = "authentication_parameter"
    SYNCHRONIZATION = "synchronization_parameter"
    MONITORING = "monitoring_parameter"
    LOCAL = "local_parameter"
    PROJECT = "project_parameter"
    COORDINATION = "coordination_parameter"
    GLOBAL = "global_parameter"


class AuthenticationParameter:
    """ client -> server parameters to authenticate the client """
    USERNAME = "username"
    PASSWORD = "password"
    TOKEN = "token"
    PROJECT_ID = "project_id"


class SyncParameter:
    """ client -> server parameters to ensure the clients and server are synced """
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"
    OPERATION_STATUS = "operation_status"


class MonitoringParameter:
    """ client -> server parameters to breakdown the runtime  of the client """
    COMPUTATION_TIME = "computation_time"
    NETWORK_SEND_TIME = "network_send_time"
    NETWORK_RECEIVE_TIME = "network_receive_time"
    IDLE_TIME = "idle_time"


class HyFedProjectParameter:
    """ server -> client and server -> webapp project info parameters """

    ID = "id"
    ALGORITHM = "algorithm"
    TOOL = "tool"
    NAME = "name"
    DESCRIPTION = "description"
    COORDINATOR = "coordinator"


class CoordinationParameter:
    """ server -> client parameters for coordination purposes """

    PROJECT_ID = "project_id"
    PROJECT_STATUS = "project_status"
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"
    PROJECT_STARTED = "project_started"
    CLIENT_JOINED = "client_joined"


class ServerParameter:
    """
        A class to bundle the parameters sent from the server to the clients in each communication round;
        project parameters are shared with the clients only once (not in each communication round)
        after the clients join, and therefore, they are not part of this class.
    """
    def __init__(self):
        self.coordination_parameters = {}
        self.global_parameters = {}

    def set_coordination_parameters(self, project_id, project_status, project_step, comm_round):
        self.coordination_parameters[CoordinationParameter.PROJECT_ID] = project_id
        self.coordination_parameters[CoordinationParameter.PROJECT_STATUS] = project_status
        self.coordination_parameters[CoordinationParameter.PROJECT_STEP] = project_step
        self.coordination_parameters[CoordinationParameter.COMM_ROUND] = comm_round

    def set_global_parameters(self, global_parameters):
        self.global_parameters = global_parameters

    def jsonify_parameters(self, client_username=''):

        """
            client_username='' implies the global parameters values are the same for all clients (client-agnostic type).
            In this case, jsonify the global parameters as they are.
            Otherwise, each client needs to be sent the corresponding global parameter values,
            so use the client's username to extract the client's global parameters before jsonifying them.
        """
        if not client_username:
            return {Parameter.COORDINATION: self.coordination_parameters,
                    Parameter.GLOBAL: self.global_parameters}
        else:
            return {Parameter.COORDINATION: self.coordination_parameters,
                    Parameter.GLOBAL: self.global_parameters[client_username]}
