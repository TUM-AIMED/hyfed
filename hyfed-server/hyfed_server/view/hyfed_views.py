"""
    The API for client <-> server, webapp <-> server, and compensator <-> server communication

    Copyright 2021 Reza NasiriGerdeh, Julian Matschinske, and Reihaneh TorkzadehMahani. All Rights Reserved.

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


from django.http import HttpResponseForbidden, HttpResponseNotFound, HttpResponse, HttpResponseBadRequest
from django.contrib.auth import authenticate
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics, viewsets, status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.decorators import action


from hyfed_server.model.hyfed_models import HyFedProjectModel, TokenModel
from hyfed_server.util.hyfed_parameters import Parameter, AuthenticationParameter, CoordinationParameter, \
     SyncParameter, HyFedProjectParameter
from hyfed_server.util.pool import ProjectPool
from hyfed_server.models import UserModel
from hyfed_server.serializer.hyfed_serializers import UserSerializer, TokenSerializer, HyFedProjectSerializer
from hyfed_server.mappers import server_project, project_model, project_serializer
from hyfed_server.util.status import ProjectStatus

import os
import pickle
import threading
from shutil import make_archive
from wsgiref.util import FileWrapper

import logging
logger = logging.getLogger(__name__)

"""  a project pool to keep a copy of the projects in the memory """
project_pool = ProjectPool()


# ############### Decorator(s) ####################
def client_authentication(request_handler_function):
    """
        Decorator to authenticate the client using project_id, username, and token provided by the client
    """
    def wrapper(self, request, *params, **kwargs):
        try:
            # extract project_id, username, and token from the request body
            request_body = pickle.loads(request.body)

            authentication_parameters = request_body[Parameter.AUTHENTICATION]

            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            username = authentication_parameters[AuthenticationParameter.USERNAME]
            token = authentication_parameters[AuthenticationParameter.TOKEN]

            # if project is running, use the copy of the project in memory to authenticate the client
            if project_pool.is_running(project_id):

                running_project = project_pool.get_running_project(project_id)

                # check whether the client is a participant of the project
                if username not in running_project.get_client_tokens().keys():
                    logger.debug(f'Project {project_id}: client {username} is not a participant of the project!')
                    return HttpResponseBadRequest()

                # authenticate the client by comparing the token from the request and intended token
                intended_token = running_project.get_client_tokens()[username]

                if token != intended_token:
                    logger.debug(f'Project {project_id}: client {username} and token {token} not matched!')
                    return HttpResponseForbidden()

            # if project is NOT running (CREATED state), use project and token models to authenticate the client
            else:
                token_instance = TokenModel.objects.get(id=token)

                # check whether the client is a participant of the project
                if project_id != str(token_instance.project.id):
                    logger.debug(f"Project {project_id}: client {username} is not a participant of the project!")
                    return HttpResponseForbidden()

                # check whether username and token match
                if username != token_instance.participant.username:
                    logger.debug(f"Project {project_id}: client {username} and token {token} do not match!")
                    return HttpResponseForbidden()

            logger.debug(f'Project {project_id}: client {username} authenticated!')
        except Exception as auth_exception:
            logger.debug(auth_exception)
            return HttpResponseBadRequest()

        return request_handler_function(self, request, *params, **kwargs)

    return wrapper


def compensator_authentication(request_handler_function):
    """
        Decorator to authenticate the compensator using the hash values
    """

    def wrapper(self, request, *params, **kwargs):
        try:
            # extract project_id, username, and token from the request body
            request_body = pickle.loads(request.body)

            authentication_parameters = request_body[Parameter.AUTHENTICATION]

            hash_project_id = authentication_parameters[AuthenticationParameter.HASH_PROJECT_ID]
            hash_username = authentication_parameters[AuthenticationParameter.HASH_USERNAME_HASHES]
            hash_token = authentication_parameters[AuthenticationParameter.HASH_TOKEN_HASHES]

            # if project is not running, a bad request received from the compensator
            if not project_pool.is_running_hash_project(hash_project_id):
                return HttpResponseBadRequest()

            # get the project corresponding to the hash project ID
            project_id = project_pool.get_project_id(hash_project_id)
            running_project = project_pool.get_running_project(project_id)

            # check hash of the usernames received from the compensator matches that from the project
            if hash_username != running_project.get_hash_client_usernames():
                logger.debug(f'Project {running_project.get_project_id()}:  hash_username {hash_username}'
                             f' from compensator and {running_project.get_hash_client_usernames()} do not match!')
                return HttpResponseBadRequest()

            # check hash of the tokens received from the compensator matches that from the project
            if hash_token != running_project.get_hash_client_tokens():
                logger.debug(f'Project {running_project.get_project_id()}: hash_token {hash_token} from compensator'
                             f' and {running_project.get_hash_client_tokens()} do not match!')
                return HttpResponseBadRequest()

            logger.debug(f'Project {project_id}: compensator authenticated!')
        except Exception as auth_exception:
            logger.debug(auth_exception)
            return HttpResponseBadRequest()

        return request_handler_function(self, request, *params, **kwargs)

    return wrapper


# ############### View classes to serve CLIENT requests ####################
class ProjectJoinView(APIView):
    """ Handles the join process of the clients """

    permission_classes = (AllowAny,)

    def post(self, request):
        try:

            # extract the username, password, and token from the request body
            join_ok = True

            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]

            username = authentication_parameters[AuthenticationParameter.USERNAME]
            password = authentication_parameters[AuthenticationParameter.PASSWORD]
            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            token = authentication_parameters[AuthenticationParameter.TOKEN]

            # check whether username and password match
            client_instance = authenticate(username=username, password=password)
            if not client_instance:
                logger.debug(f'Client {username} and provided password do not match!')
                join_ok = False

            # get the project and token instances from the corresponding models
            project_model_instance = HyFedProjectModel.objects.get(id=project_id)
            token_instance = TokenModel.objects.get(id=token)

            # check whether token belongs to the project
            if token_instance.project.id != project_model_instance.id:
                logger.debug(f'Token {token} does not belong to project {project_id}!')
                join_ok = False

            # check whether token already used (by this client or any other client)
            if token_instance.participant:
                logger.debug(f'Token {token} already used by this/another client!')
                join_ok = False

            # check whether client already joined to the project by another token
            if TokenModel.objects.filter(participant=client_instance, project=project_model_instance).exists():
                logger.debug(f'Client {username} has already joined with a different token!')
                join_ok = False

            # if client authenticated, mark the token as used by the client
            if join_ok:
                token_instance.participant = client_instance
                token_instance.save()

            # for logging purposes
            if join_ok:
                logger.debug(f'Project {project_id}: client {username} join was successful!')
            else:
                logger.debug(f'Project {project_id}: client {username} join was NOT successful!')

            # if this client is the last one who joined, start the project
            if project_pool.should_start(project_id):
                project_pool.start_project(project_id)

        except HyFedProjectModel.DoesNotExist:
            logger.debug(f'Project ID {project_id} does not exist!')
            join_ok = False

        except TokenModel.DoesNotExist:
            logger.debug(f'Token {token} does not exist!')
            join_ok = False

        except Exception as join_exception:
            logger.debug(join_exception)
            join_ok = False

        response = {CoordinationParameter.CLIENT_JOINED: join_ok}
        serialized_response = pickle.dumps(response)

        return HttpResponse(content=serialized_response)


class ProjectInfoView(APIView):
    """
        Provide general info of the project such as project id, name, algorithm, and coordinator
        + derived project specific info
    """

    permission_classes = (AllowAny,)
    @client_authentication
    def get(self, request):
        try:
            # extract project id, token, and username (just for debugging) from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            token = authentication_parameters[AuthenticationParameter.TOKEN]
            username = authentication_parameters[AuthenticationParameter.USERNAME]

            # get tool name
            token_instance = TokenModel.objects.get(id=token)
            tool = token_instance.project.tool

            # get derived project model instance
            derived_instance = project_model[tool].objects.get(id=project_id)

            # serialize project general info
            serialized_project = project_serializer[tool]().to_representation(derived_instance)

            # prepare serialized response
            json_response = {Parameter.PROJECT: serialized_project}
            serialized_response = pickle.dumps(json_response)

            logger.debug(f"Project {project_id}: {tool} project info serialized to client {username} ...")

            return HttpResponse(content=serialized_response)

        except Exception as project_info_exception:
            logger.debug(f'Project {project_id}: {project_info_exception}')
            return HttpResponseBadRequest()


class ProjectStartedView(APIView):
    """ Tell clients whether the project started """

    permission_classes = (AllowAny,)

    @client_authentication
    def get(self, request):
        try:
            # extract project id from the request
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            username = authentication_parameters[AuthenticationParameter.USERNAME]

            # for logging purposes
            logger.debug(f'Project {project_id}: ProjectStarted view request received from client {username}!')

            # get status of the project from the pool and sent it to the client
            response = {CoordinationParameter.PROJECT_STARTED: project_pool.is_running(project_id)}
            serialized_response = pickle.dumps(response)
            return HttpResponse(content=serialized_response)

        except Exception as project_started_exception:
            logger.debug(f'Project {project_id}: {project_started_exception}')
            return HttpResponseBadRequest()


class ModelAggregationView(APIView):
    """ Get the clients' parameters and perform aggregation """

    permission_classes = (AllowAny,)

    @client_authentication
    def post(self, request):
        try:

            # extract project_id and username from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            username = authentication_parameters[AuthenticationParameter.USERNAME]

            # get the running project from the pool
            running_project = project_pool.get_running_project(project_id)

            logger.debug(f'Project {project_id}: local parameters received from client {username}!')

            # update client->server traffic counter
            request_size = int(request.headers['Content-Length'])
            running_project.add_to_client_server_traffic(request_size)

            # extract client parameters (e.g. sync and local) from the request body
            logger.debug(f'Project {project_id}: extracting client {username} parameters ...')
            running_project.extract_client_parameters(username, request_body)

            # if parameters from all clients received, start aggregation
            if len(running_project.get_local_parameters()) == len(running_project.get_client_tokens()):
                aggregation_thread = threading.Thread(target=running_project.aggregate)
                aggregation_thread.start()

        except Exception as model_aggregation_exception:
            logger.debug(f'Project {project_id}: {model_aggregation_exception}')
            return HttpResponseBadRequest()

        return HttpResponse()


class GlobalModelView(APIView):
    """
        Provide the global parameters to the clients if they are ready (aggregation completed);
        Otherwise, tell clients to keep inquiring the server.
    """
    permission_classes = (AllowAny,)

    @client_authentication
    def get(self, request):
        try:
            # extract project_id, username, and comm_round from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            sync_parameters = request_body[Parameter.SYNCHRONIZATION]
            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            username = authentication_parameters[AuthenticationParameter.USERNAME]
            comm_round = sync_parameters[SyncParameter.COMM_ROUND]

            # get the running project from the pool
            running_project = project_pool.get_running_project(project_id)

            # update client->server traffic counter
            request_size = int(request.headers['Content-Length'])
            running_project.add_to_client_server_traffic(request_size)

            # prepare parameters sent to the clients (e.g. coordination and global parameters if ready)
            logger.debug(f'Project {project_id}: preparing client parameters ...')
            client_parameters_serialized = running_project.prepare_client_parameters(client_username=username,
                                                                                     client_comm_round=comm_round)

            # update server->client traffic counter
            response_size = len(client_parameters_serialized)
            running_project.add_to_server_client_traffic(response_size)

            return HttpResponse(content=client_parameters_serialized)
        except Exception as global_model_exception:
            logger.debug(f'Project {project_id}: {global_model_exception}')
            return HttpResponseBadRequest()


class ResultDownloadView(APIView):
    """ Provides the clients with the result file """

    permission_classes = (AllowAny,)
    @client_authentication
    def get(self, request):
        try:

            # extract project_id and username (for debugging purposes) from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]
            username = authentication_parameters[AuthenticationParameter.USERNAME]  # for debugging purposes

            # get the result directory of the project
            hyfed_model_instance = HyFedProjectModel.objects.get(id=project_id)
            project_result_dir = f'{hyfed_model_instance.result_dir}/{project_id}'

            # zip the result directory if it has not already been zipped
            zip_file_name = f'{project_result_dir}.zip'
            if not os.path.exists(zip_file_name):
                logger.debug(f"Project {project_id}: zipping the result directory ..")
                make_archive(base_name=project_result_dir, format="zip", root_dir=project_result_dir)

            # create http response
            http_response = HttpResponse(FileWrapper(open(zip_file_name, 'rb')), content_type='application/zip')

            logger.debug(f"Project {project_id}: result zip file shared with client {username}!")

            return http_response
        except Exception as io_exception:
            logger.debug(f'Project {project_id}: {io_exception}')
            return HttpResponseBadRequest()


# ############### View classes to serve COMPENSATOR requests ####################
class ProjectAuthenticationView(APIView):
    """ Tell the compensator whether a project with the asked hash_id is running """

    permission_classes = (AllowAny,)

    def get(self, request):
        try:
            # extract the hash of the project ID from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            hash_project_id = authentication_parameters[AuthenticationParameter.HASH_PROJECT_ID]

            # if project specified by the hash_project_id is running,
            # provide the compensator with the number of clients in the project
            if project_pool.is_running_hash_project(hash_project_id):
                auth_ok = True
                project_id = project_pool.get_project_id(hash_project_id)
                client_count = len(project_pool.get_running_project(project_id).get_client_tokens())
            else:
                auth_ok = False
                client_count = -1

        except Exception as project_auth_exception:
            logger.error(project_auth_exception)
            auth_ok = False
            client_count = -1

        response = {AuthenticationParameter.PROJECT_AUTHENTICATED: auth_ok,
                    HyFedProjectParameter.CLIENT_COUNT: client_count}

        serialized_response = pickle.dumps(response)

        return HttpResponse(content=serialized_response)


class ModelCompensationView(APIView):
    """ Get the compensation parameters from the compensator """

    permission_classes = (AllowAny,)

    @compensator_authentication
    def post(self, request):
        try:

            # extract the hash of the project ID from the request body
            request_body = pickle.loads(request.body)
            authentication_parameters = request_body[Parameter.AUTHENTICATION]
            hash_project_id = authentication_parameters[AuthenticationParameter.HASH_PROJECT_ID]

            # get the running project associated with the hash project ID
            project_id = project_pool.get_project_id(hash_project_id)
            running_project = project_pool.get_running_project(project_id)

            logger.debug(f"Project {project_id}: compensator parameters received!")

            # if compensator parameters already received, ignore the request
            if running_project.is_compensator_parameters_received():
                logger.debug(f'Project {project_id}: compensator parameters ignored because they have been already received!')
                return HttpResponseBadRequest()

            # add traffic size to compensator -> server traffic counter
            request_size = int(request.headers['Content-Length'])
            running_project.add_to_compensator_server_traffic(request_size)

            # init compensator parameters of the corresponding project
            running_project.set_compensator_parameters(request_body)
            logger.debug(f'Project {project_id}: compensator parameters initialized.')

        except Exception as model_compensation_exception:
            logger.debug(f'Project {project_id}: {model_compensation_exception}')
            return HttpResponseBadRequest()

        return HttpResponse()


# ############### View classes to serve WEBAPP requests ####################
class SignupView(generics.CreateAPIView):
    """ Sign up a new account"""

    queryset = UserModel.objects.all()
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)


class TokenBlacklistView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
            return HttpResponse()
        except Exception as token_black_list_exp:
            logger.error(token_black_list_exp)
            return HttpResponseBadRequest()


class UserInfo(APIView):
    def get(self, request):
        return Response(UserSerializer().to_representation(request.user))


class UserViewSet(viewsets.ModelViewSet):
    """ Show the list of users """
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """ Viewset to create, list, and delete the projects """

    serializer_class = HyFedProjectSerializer

    def create(self, request, *args, **kwargs):
        """ Create the project """

        try:
            # first clean-up the projects marked as clean-up in the project pool
            project_pool.clean_up_projects()

            # ######## create the project
            # extract the tool name from the webapp request
            tool = request.data[HyFedProjectParameter.TOOL]

            # create the project and save the corresponding model instance in the database
            derived_project = server_project[tool](request, project_model[tool])

            # add the project to the project pool
            project_pool.add_project(derived_project)

            # ######### serialize the project
            data = request.data
            context = {'request': request}

            # retrieve and serialize derived project model instance
            derived_model_instance = project_model[tool].objects.get(id=derived_project.get_project_id())
            derived_model_serialized = project_serializer[tool](data=data, context=context).to_representation(derived_model_instance)

            return Response(derived_model_serialized)

        except Exception as creation_exp:
            logger.debug(f"Project creation exception: {creation_exp}")
            return HttpResponseBadRequest()

    def get_queryset(self):
        """ Show the project(s) """
        try:
            # if request url is in the form of /projects/project_id/
            if len(str(self.request.path).split('/')) == 4:
                # extract project id from url
                project_id = str(self.request.path).split('/')[2]

                # extract tool name from the model
                project_instance = HyFedProjectModel.objects.get(id=project_id)
                tool = project_instance.tool

                # set serializer to the derived serializer class
                ProjectViewSet.serializer_class = project_serializer[tool]

                return project_model[tool].objects.filter(Q(coordinator=self.request.user) |
                                                          Q(participants__participant=self.request.user)).distinct()
            else:
                ProjectViewSet.serializer_class = HyFedProjectSerializer
                return HyFedProjectModel.objects.filter(Q(coordinator=self.request.user) |
                                                        Q(participants__participant=self.request.user)).distinct()

        except Exception as queryset_exp:
            logger.debug(f"get_queryset exception: {queryset_exp}")
            return HttpResponseBadRequest()

    def destroy(self, request, *args, **kwargs):
        """ Delete the project"""

        logger.debug(f" Project {self.get_object().id}: being deleted!")

        if self.get_object().coordinator != self.request.user:
            return HttpResponseForbidden('Only coordinator can delete the project!')

        project_pool.delete_project(self.get_object().id)

        return super(ProjectViewSet, self).destroy(request)

    @action(detail=True, methods=['get'])
    def tokens(self, request, *args, **kwargs):
        """ List the tokens of the project """

        project_instance = self.get_object()
        if project_instance.coordinator != request.user:
            return HttpResponseForbidden('Tokens can only be viewed by the project coordinator!')

        return Response(TokenSerializer(many=True).to_representation(project_instance.participants))

    @action(detail=True, methods=['post'])
    def create_token(self, request, *args, **kwargs):
        """ Create a token for the project """

        project_instance = self.get_object()

        if project_instance.coordinator != request.user:
            return HttpResponseForbidden('Tokens can only be created by the project coordinator!')

        token = TokenModel.objects.create(project=project_instance, participant=None)

        logger.debug(f"Project {project_instance.id}: token {token.id} created!")

        return Response(TokenSerializer().to_representation(token))

    @action(detail=True)
    def download_results(self, request, *args, **kwargs):
        """ Download the project result zip file using the webapp """

        try:
            project_instance = self.get_object()
            project_id = project_instance.id
            zip_file_path = f'{project_instance.result_dir}/{project_id}.zip'

            http_response = HttpResponse(FileWrapper(open(zip_file_path, 'rb')), content_type='application/zip')
            http_response['Content-Disposition'] = f'attachment; filename="{project_id}.zip"'

            logger.debug(f"Project {project_id}: result file downloaded by participant {request.user} through WebApp!")

            return http_response
        except Exception as io_exception:
            logger.debug(io_exception)
            return HttpResponseBadRequest()


class TokenViewSet(viewsets.ModelViewSet):
    """ List the tokens of the project """
    serializer_class = TokenSerializer

    def get_queryset(self):
        return TokenModel.objects.filter(project__coordinator=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """ Delete the token """

        try:
            token_instance = self.get_object()

            # if user already joined, don't delete the token
            if token_instance.participant:
                return HttpResponseForbidden()
            self.perform_destroy(token_instance)

            logger.debug(f"Project {token_instance.project.id}: token {token_instance.id} deleted!")

        except TokenModel.DoesNotExist:
            return HttpResponseNotFound()

        return Response(status=status.HTTP_204_NO_CONTENT)
