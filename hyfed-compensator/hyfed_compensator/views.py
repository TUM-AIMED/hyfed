"""
    The view class(es) for client -> compensator communication

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

from hyfed_compensator.util.hyfed_parameters import Parameter, AuthenticationParameter, ConnectionParameter, HyFedProjectParameter, SyncParameter
from hyfed_compensator.util.endpoint import EndPoint
from hyfed_compensator.project.hyfed_compensator_project import HyFedCompensatorProject

from django.http import HttpResponse, HttpResponseBadRequest
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

import pickle
import threading
import time
import requests
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

project_pool = dict()  # a pool of authenticated projects; indexed by project_id_hash
auth_in_progress = set()  # set of projects whose authentication is in progress


def clean_up_projects():
    """ Consider projects that have not been updated for 3 days as completed/failed and remove them from the pool """

    three_days = 3 * 24 * 3600
    for hash_project_id in list(project_pool.keys()):
        if (datetime.now().timestamp() - project_pool[hash_project_id].get_last_updated_date()) > three_days:

            del project_pool[hash_project_id]
            logger.debug(f"Project {hash_project_id}: Removed from the project pool!")


def authenticate_project(hash_project_id, server_url):
    """ Query server to see whether the project ID whose hash is hash_project_id exists on the server """

    logger.debug(f"Project {hash_project_id}: Authenticating the project ...")

    # create and serialize request body
    request_body = {Parameter.AUTHENTICATION: {AuthenticationParameter.HASH_PROJECT_ID: hash_project_id}}
    serialized_request_body = pickle.dumps(request_body)

    # send a request to server to authenticate the project
    max_tries = 10
    for _ in range(max_tries):
        try:
            logger.debug(f"Project {hash_project_id}: Sending project authentication request to the server ...")
            response = requests.get(url=f'{server_url}/{EndPoint.PROJECT_AUTHENTICATION}',
                                    data=serialized_request_body,
                                    timeout=60)

            if response.status_code == 200:

                # remove the project_id_hash from in progress projects
                auth_in_progress.discard(hash_project_id)

                # deserialize response
                json_response = pickle.loads(response.content)
                project_authenticated = json_response[AuthenticationParameter.PROJECT_AUTHENTICATED]
                client_count = json_response[HyFedProjectParameter.CLIENT_COUNT]

                # if project does not exist on the server, then return
                if not project_authenticated:
                    logger.debug(f"Project {hash_project_id}: Project was not authenticated!")
                    return

                # if project exists on the server, then create the corresponding compensator project and put it into project_pool
                logger.debug(f"Project {hash_project_id}: Project authenticated!")

                project_pool[hash_project_id] = HyFedCompensatorProject(hash_project_id, client_count)
                logger.debug(f"Project {hash_project_id}: Project added to the pool!")

                # remove old projects from the pool
                clean_up_projects()

                return

            else:
                logger.error(f"Project {hash_project_id}: Got response {response.status_code} from the server!")
                time.sleep(5)

        except Exception as project_auth_exp:
            logger.error(f"Project {hash_project_id}: Sending failed!")
            logger.error(f'Project {hash_project_id}: The exception is: {project_auth_exp}')
            time.sleep(5)


class NoiseAggregationView(APIView):
    """ Get the client parameters including noise values (compensation parameters) from the clients and aggregate them """

    permission_classes = (AllowAny,)

    def post(self, request):
        try:

            # extract server URL and the hash of project ID from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            connection_parameters = request_body[Parameter.CONNECTION]
            hash_project_id = authentication_parameters[AuthenticationParameter.HASH_PROJECT_ID]
            server_url = connection_parameters[ConnectionParameter.SERVER_URL]

            # if the project already authenticated
            if hash_project_id in project_pool.keys():

                # update the last day the project accessed
                project_pool[hash_project_id].set_last_updated_date()

                # add the client parameters to the corresponding attributes
                project_pool[hash_project_id].add_client_parameters(request)

                # aggregate client parameters including noise values if they are received from all clients
                if project_pool[hash_project_id].should_aggregate_and_send():
                    aggregate_send_thread = threading.Thread(target=project_pool[hash_project_id].aggregate_and_send)
                    aggregate_send_thread.setDaemon(True)
                    aggregate_send_thread.start()

                # tell the client not to retry
                should_retry = False
                response = {SyncParameter.SHOULD_RETRY: should_retry}
                serialized_response = pickle.dumps(response)
                return HttpResponse(content=serialized_response)

            # if the project authentication is in progress, tell the client to retry later
            if hash_project_id in auth_in_progress:
                logger.debug(f"Project {hash_project_id}: Project authentication is in progress!")
                should_retry = True
                response = {SyncParameter.SHOULD_RETRY: should_retry}
                serialized_response = pickle.dumps(response)
                return HttpResponse(content=serialized_response)

            # if the project has not been authenticated yet, then initiate the authentication
            auth_in_progress.add(hash_project_id)
            project_auth_thread = threading.Thread(target=authenticate_project, args=(hash_project_id, server_url,))
            project_auth_thread.setDaemon(True)
            project_auth_thread.start()

            # tell the client to retry
            should_retry = True
            response = {SyncParameter.SHOULD_RETRY: should_retry}
            serialized_response = pickle.dumps(response)
            return HttpResponse(content=serialized_response)

        except Exception as view_exception:
            logger.error(view_exception)
            return HttpResponseBadRequest()
