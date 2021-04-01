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

from hyfed_server.model.hyfed_models import HyFedProjectModel, TokenModel
from hyfed_server.util.status import ProjectStatus

import logging
logger = logging.getLogger(__name__)


class ProjectPool:
    """ a pool of projects in the main memory """

    def __init__(self):
        self.project_pool = dict()  # indexed by project_id
        logger.debug("Project pool Created!")

    def add_project(self, derived_project_instance):
        """ add the project to the pool """

        try:
            project_id = str(derived_project_instance.get_project_id())
            self.project_pool[project_id] = derived_project_instance

            logger.debug(f"Project {project_id}: project added to the pool!")
        except Exception as exp:
            logger.error(exp)

    def start_project(self, project_id):
        """ start the project (ProjectStatus.CREATED -> ProjectStatus.PARAMETERS_READY) """

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

                # change the status of the project
                self.project_pool[project_id].set_status(ProjectStatus.PARAMETERS_READY)

                logger.info(f"Project {project_id}: started!")

        except Exception as exp:
            logger.error(f'Project {project_id}: {exp}')

    def is_running(self, project_id):
        """ Check whether the project specified with project_id is running """

        try:
            if project_id not in self.project_pool.keys():
                return False

            project_status = self.project_pool[project_id].get_status()

            return project_status != ProjectStatus.CREATED
        except Exception as check_exp:
            logger.error(f'Project {project_id}: {check_exp}')
            return False

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
        """ return the project instance specified with the project_id """

        if not self.is_running(project_id):
            return

        return self.project_pool[project_id]

    def clean_up_projects(self):
        """ Remove the processes marked as clean-up from the project pool """

        logger.debug("Removing the projects marked as clean-up from the pool ...")
        project_id_list = list(self.project_pool.keys())[:]
        for project_id in project_id_list:
            if self.project_pool[project_id].clean_me_up():
                logger.debug(f"Project {project_id} removed from the project pool!")
                del self.project_pool[project_id]

    def delete_project(self, project_id):
        """ Delete the project specified by project id """

        if not self.is_running(project_id):
            return

        # Project in Created, Failed, Aborted, and Done step can be manually deleted
        project_status = self.project_pool[project_id].get_status()
        if project_status == ProjectStatus.PARAMETERS_READY or project_status == ProjectStatus.AGGREGATING:
            return

        logger.debug(f"Project {project_id} removed from the project pool!")
        del self.project_pool[project_id]
