"""
    Name of the parameters exchanged  compensator <-> client and compensator <-> server

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


class Parameter:
    """
        There are six general categories of the parameters exchanged client <-> compensator and compensator <-> server:
        client -> compensator: authentication, synchronization, connection, and compensation parameters
        compensator -> client: synchronization parameters
        compensator -> server: authentication, synchronization, monitoring, and compensation parameters
        server -> compensator: project parameters
    """

    AUTHENTICATION = "authentication_parameter"
    SYNCHRONIZATION = "synchronization_parameter"
    CONNECTION = "connection_parameter"
    PROJECT = "project_parameter"
    COMPENSATION = "compensation_parameter"
    MONITORING = "monitoring_parameter"
    DATA_TYPE = "data_type_parameter"


class AuthenticationParameter:
    """ compensator <-> server and client -> compensator parameters to authenticate the compensator, clients, and project """

    # compensator -> server
    HASH_USERNAME_HASHES = "hash_username_hashes"
    HASH_TOKEN_HASHES = "hash_token_hashes"

    # server -> compensator
    PROJECT_AUTHENTICATED = "project_authenticated"

    # client -> compensator
    HASH_USERNAME = "hash_username"
    HASH_TOKEN = "hash_token"

    # client -> compensator and compensator -> server
    HASH_PROJECT_ID = "hash_project_id"


class SyncParameter:
    """ compensator -> server and compensator <-> client parameters to ensure
        the clients, compensator, and server are synced """

    # client -> compensator , compensator -> server
    PROJECT_STEP = "project_step"
    COMM_ROUND = "communication_round"

    # compensator -> server
    OPERATION_STATUS = "operation_status"

    # compensator -> client
    SHOULD_RETRY = "should_retry"


class ConnectionParameter:
    """ client -> compensator parameters """

    SERVER_URL = "server_url"


class HyFedProjectParameter:
    """ Server -> compensator project parameters """

    CLIENT_COUNT = "client_count"


class MonitoringParameter:
    """ compensator -> server parameters to take into account the time spent at the compensator and traffic size received from the clients """

    COMPUTATION_TIME = "computation_time"
    NETWORK_SEND_TIME = "network_send_time"
    CLIENT_COMPENSATOR_TRAFFIC = "client_compensator_traffic"
