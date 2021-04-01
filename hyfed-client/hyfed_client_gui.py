"""
    HyFed client GUI

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

from hyfed_client.widget.join_widget import JoinWidget
from hyfed_client.widget.hyfed_project_info_widget import HyFedProjectInfoWidget
from hyfed_client.widget.hyfed_dataset_widget import HyFedDatasetWidget
from hyfed_client.widget.project_status_widget import ProjectStatusWidget
from hyfed_client.util.hyfed_parameters import HyFedProjectParameter, ConnectionParameter, AuthenticationParameter
from hyfed_client.project.hyfed_client_project import HyFedClientProject

import threading

import logging
logger = logging.getLogger(__name__)


class HyFedClientGUI:
    """ HyFed Client GUI """

    def __init__(self):

        # create the join widget
        self.join_widget = JoinWidget(title="HyFed Client",
                                      local_server_name="Localhost",
                                      external_server_name="HyFed-Server",
                                      local_server_url="http://localhost:8000",
                                      external_server_url="https://hyfed-server-url")

        # show the join widget
        self.join_widget.show()

        # if join was NOT successful, terminate the client GUI
        if not self.join_widget.is_joined():
            return

        # if join was successful, get connection and authentication parameters from the join widget
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()

        #  create HyFed project info widget based on the authentication and connection parameters
        self.hyfed_project_info_widget = \
            HyFedProjectInfoWidget(title="HyFed Project Info",
                                   connection_parameters=connection_parameters,
                                   authentication_parameters=authentication_parameters)

        # Obtain HyFed project info from the server
        # the project info will be set in project_parameters attribute of the info widget
        self.hyfed_project_info_widget.obtain_project_info()

        # if HyFed project info cannot be obtained from the server, exit the GUI
        if not self.hyfed_project_info_widget.project_parameters:
            return

        # add basic info of the project such as project id, project name, description, and etc to the info widget
        self.hyfed_project_info_widget.add_project_basic_info()

        # add accept and decline buttons to the widget
        self.hyfed_project_info_widget.add_accept_decline_buttons()

        # show project info widget
        self.hyfed_project_info_widget.show()

        # if participant declined to proceed, exit the GUI
        if not self.hyfed_project_info_widget.is_accepted():
            return

        # if user agreed to proceed, create and show the HyFed dataset selection widget
        self.hyfed_dataset_widget = HyFedDatasetWidget(title="HyFed Dataset Selection")
        self.hyfed_dataset_widget.add_quit_run_buttons()
        self.hyfed_dataset_widget.show()

        # if the participant didn't click on 'Run' button, terminate the client GUI
        if not self.hyfed_dataset_widget.is_run_clicked():
            return

        # if participant clicked on 'Run', get all the parameters needed
        # to create the client project from the widgets
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()
        project_parameters = self.hyfed_project_info_widget.get_project_parameters()

        server_url = connection_parameters[ConnectionParameter.SERVER_URL]
        username = authentication_parameters[AuthenticationParameter.USERNAME]
        token = authentication_parameters[AuthenticationParameter.TOKEN]
        project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]

        algorithm = project_parameters[HyFedProjectParameter.ALGORITHM]
        project_name = project_parameters[HyFedProjectParameter.NAME]
        project_description = project_parameters[HyFedProjectParameter.DESCRIPTION]
        coordinator = project_parameters[HyFedProjectParameter.COORDINATOR]

        # create HyFed client project
        hyfed_client_project = HyFedClientProject(username=username,
                                                  token=token,
                                                  server_url=server_url,
                                                  project_id=project_id,
                                                  algorithm=algorithm,
                                                  name=project_name,
                                                  description=project_description,
                                                  coordinator=coordinator,
                                                  result_dir='./hyfed_client/result',
                                                  log_dir='./hyfed_client/log')

        # run HyFed client project as a thread
        hyfed_project_thread = threading.Thread(target=hyfed_client_project.run)
        hyfed_project_thread.setDaemon(True)
        hyfed_project_thread.start()

        # create and show HyFed project status widget
        hyfed_project_status_widget = ProjectStatusWidget(title="HyFed Project Status",
                                                          project=hyfed_client_project)
        hyfed_project_status_widget.add_log_and_quit_buttons()
        hyfed_project_status_widget.show()


client_gui = HyFedClientGUI()
