"""
    Parameters exchanged client <-> server and client <-> compensator

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
        There are nine general categories of the parameters exchanged clients <-> server and client <-> compensator:
        client -> server: authentication, synchronization, monitoring, and local parameters
        server -> client: coordination, project, and global parameters
        client -> compensator: authentication, synchronization, connection, data_type, and compensation parameters
        compensator -> client: synchronization parameters
    """

    AUTHENTICATION = "authentication_parameter"
    SYNCHRONIZATION = "synchronization_parameter"
    MONITORING = "monitoring_parameter"
    PROJECT = "project_parameter"
    COORDINATION = "coordination_parameter"
    CONNECTION = "connection_parameter"
    GLOBAL = "global_parameter"
    LOCAL = "local_parameter"
    COMPENSATION = "compensation_parameter"
    DATA_TYPE = "data_type_parameter"


class AuthenticationParameter:
    """  Parameters to authenticate the client """

    # client -> server
    USERNAME = "username"
    PASSWORD = "password"
    PROJECT_ID = "project_id"
    TOKEN = "token"

    # client -> compensator
    HASH_USERNAME = "hash_username"
    HASH_TOKEN = "hash_token"
    HASH_PROJECT_ID = "hash_project_id"


class SyncParameter:
    """ Client -> server or client <-> compensator parameters to ensure clients, server, and compensator are synced """

    # client -> server and client -> compensator
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"

    # client -> server
    OPERATION_STATUS = "operation_status"
    COMPENSATOR_FLAG = "compensator_flag"

    # compensator -> client
    SHOULD_RETRY = "should_retry"


class MonitoringParameter:
    """ Client -> server parameters to breakdown the runtime  of the client """

    COMPUTATION_TIME = "computation_time"
    NETWORK_SEND_TIME = "network_send_time"
    NETWORK_RECEIVE_TIME = "network_receive_time"
    IDLE_TIME = "idle_time"


class HyFedProjectParameter:
    """ Server -> client project parameters """

    ID = "id"
    TOOL = "tool"
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
    """ Mostly used in the client """

    SERVER_NAME = "server_name"
    SERVER_URL = "server_url"  # client -> compensator
    COMPENSATOR_NAME = "compensator_name"
    COMPENSATOR_URL = "compensator_url"
