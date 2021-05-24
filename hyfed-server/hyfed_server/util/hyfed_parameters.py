"""
    Parameters exchanged server <-> client, server <-> webapp, and server <-> compensator

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
         There are eight general categories of the parameters exchanged server <-> clients , server <-> webapp, and
         compensator <-> server
         client -> server: authentication, synchronization, monitoring, and local parameters
         server -> client: coordination, project, global parameters
         webapp -> server: authentication and project parameters
         server -> webapp: project parameters
         compensator -> server: authentication, synchronization, monitoring, and compensation parameters
         server -> compensator: project parameters
    """

    AUTHENTICATION = "authentication_parameter"
    SYNCHRONIZATION = "synchronization_parameter"
    MONITORING = "monitoring_parameter"
    LOCAL = "local_parameter"
    PROJECT = "project_parameter"
    COORDINATION = "coordination_parameter"
    GLOBAL = "global_parameter"
    COMPENSATION = "compensation_parameter"


class AuthenticationParameter:
    """ client -> server and compensator <-> server parameters to authenticate the client, compensator, or project """

    # client -> server
    USERNAME = "username"
    PASSWORD = "password"
    TOKEN = "token"
    PROJECT_ID = "project_id"

    # compensator -> server
    HASH_PROJECT_ID = "hash_project_id"
    HASH_USERNAME_HASHES = "hash_username_hashes"
    HASH_TOKEN_HASHES = "hash_token_hashes"

    # server -> compensator
    PROJECT_AUTHENTICATED = "project_authenticated"


class SyncParameter:
    """ client -> server or compensator -> server parameters to ensure clients, compensator, and server are synced """

    # client -> server and compensator -> server
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"
    OPERATION_STATUS = "operation_status"

    # client -> server
    COMPENSATOR_FLAG = "compensator_flag"


class MonitoringParameter:
    """ client -> server | compensator -> server parameters to breakdown the runtime  of the client | compensator """

    # client -> server
    NETWORK_RECEIVE_TIME = "network_receive_time"
    IDLE_TIME = "idle_time"

    # client -> server and compensator -> server
    COMPUTATION_TIME = "computation_time"
    NETWORK_SEND_TIME = "network_send_time"

    # compensator -> server
    CLIENT_COMPENSATOR_TRAFFIC = "client_compensator_traffic"


class HyFedProjectParameter:
    """ server -> client, server -> webapp, server -> compensator project info parameters """

    # server -> client and server -> webapp
    ID = "id"
    ALGORITHM = "algorithm"
    TOOL = "tool"
    NAME = "name"
    DESCRIPTION = "description"

    # server -> client
    COORDINATOR = "coordinator"

    # server -> compensator
    CLIENT_COUNT = "client_count"


class CoordinationParameter:
    """ server -> client parameters for coordination purposes """

    PROJECT_ID = "project_id"
    PROJECT_STATUS = "project_status"
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"
    PROJECT_STARTED = "project_started"
    CLIENT_JOINED = "client_joined"
