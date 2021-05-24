"""
    A pool of projects kept in the memory

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
import hashlib

from hyfed_server.model.hyfed_models import HyFedProjectModel, TokenModel
from hyfed_server.util.status import ProjectStatus

import logging
logger = logging.getLogger(__name__)


class ProjectPool:
    """ A pool of projects in the main memory """

    def __init__(self):
        self.project_pool = dict()  # indexed by project_id
        self.hash_to_plain_id = dict()  # project_id_hash -> project_id
        logger.debug("Project pool Created!")

    def add_project(self, derived_project_instance):
        """ Add the project to the pool """

        try:
            project_id = str(derived_project_instance.get_project_id())
            self.project_pool[project_id] = derived_project_instance

            logger.debug(f"Project {project_id}: Project added to the pool!")
        except Exception as exp:
            logger.error(exp)

    def start_project(self, project_id):
        """ Start the project (ProjectStatus.CREATED -> ProjectStatus.PARAMETERS_READY) """

        try:

            if self.project_pool[project_id].get_status() == ProjectStatus.CREATED:

                # get the HyFed project model instance using project id
                hyfed_model_instance = HyFedProjectModel.objects.get(id=project_id)

                # extract the tokens of participants
                client_tokens = {}
                for token_instance in TokenModel.objects.filter(project=hyfed_model_instance):
                    client_tokens[token_instance.participant.username] = str(token_instance.id)

                # change status of the project in the database
                hyfed_model_instance.status = ProjectStatus.PARAMETERS_READY
                hyfed_model_instance.save()

                # initialize the token list in the project
                self.project_pool[project_id].set_client_tokens(tokens=client_tokens)

                # initialize the hash of the project_id, tokens, and usernames
                self.project_pool[project_id].set_hashes()

                # create hash_project_id -> project_id map
                hash_project_id = hashlib.sha256(project_id.encode('utf-8')).hexdigest()
                self.hash_to_plain_id[hash_project_id] = project_id

                # change the status of the project
                self.project_pool[project_id].set_status(ProjectStatus.PARAMETERS_READY)

                logger.debug(f"Project {project_id}: Started!")

        except Exception as exp:
            logger.error(f"Project {project_id}: Failed to start the project!")
            logger.error(f'Project {project_id}: The exception is: {exp}')

    def is_running(self, project_id):
        """ Check whether the project specified with project_id is running """

        try:
            # if project_id is not in the list of the ids in the pool, the project is not running
            if project_id not in self.project_pool.keys():
                return False

            # project is running if it is in the pool and its status is not CREATED
            project_status = self.project_pool[project_id].get_status()

            return project_status != ProjectStatus.CREATED

        except Exception as check_exp:
            logger.error(f'Project {project_id}: {check_exp}')
            return False

    def is_running_hash_project(self, project_id_hash):
        """ Check whether the project specified with project_id_hash is running """

        return project_id_hash in self.hash_to_plain_id.keys()

    def should_start(self, project_id):
        """ Check whether all clients joined to start the project """

        try:
            hyfed_model_instance = HyFedProjectModel.objects.get(id=project_id)
            unused_token_count = TokenModel.objects.filter(project=hyfed_model_instance, participant__isnull=True).count()

            return unused_token_count == 0
        except Exception as exp:
            logger.error(f'Project {project_id}: {exp}')
            return False

    def get_running_project(self, project_id):
        """ Get the project instance specified with the project_id"""

        if not self.is_running(project_id):
            return

        return self.project_pool[project_id]

    def get_project_id(self, hash_project_id):
        """ Get the project ID corresponding to hash_project_id """

        return self.hash_to_plain_id[hash_project_id]

    def clean_up_projects(self):
        """ Remove the processes marked as clean-up from the project pool """

        logger.debug("Removing the projects marked as clean-up from the pool ...")
        project_id_list = list(self.project_pool.keys())[:]
        for project_id in project_id_list:
            if self.project_pool[project_id].clean_me_up():

                # first delete hash_project_id
                hash_project_id = hashlib.sha256(project_id.encode('utf-8')).hexdigest()
                del self.hash_to_plain_id[hash_project_id]

                # delete project itself
                del self.project_pool[project_id]

                logger.debug(f"Project {project_id} removed from the project pool!")

    def delete_project(self, project_id):
        """ Delete the project specified by project id """

        if not self.is_running(project_id):
            return

        # Project in Created, Failed, Aborted, and Done step can be manually deleted
        project_status = self.project_pool[project_id].get_status()
        if project_status == ProjectStatus.PARAMETERS_READY or project_status == ProjectStatus.AGGREGATING:
            return

        # first delete hash_project_id
        hash_project_id = hashlib.sha256(project_id.encode('utf-8')).hexdigest()
        del self.hash_to_plain_id[hash_project_id]

        # delete project itself
        del self.project_pool[project_id]

        logger.debug(f"Project {project_id} removed from the project pool!")
