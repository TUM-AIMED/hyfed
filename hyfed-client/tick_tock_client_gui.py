"""
    TickTock client GUI

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
from hyfed_client.widget.project_status_widget import ProjectStatusWidget
from hyfed_client.util.hyfed_parameters import HyFedProjectParameter, ConnectionParameter, AuthenticationParameter

from tick_tock_client.widget.tick_tock_project_info_widget import TickTockProjectInfoWidget
from tick_tock_client.widget.tick_tock_dataset_widget import TickTockDatasetWidget
from tick_tock_client.project.tick_tock_client_project import TickTockClientProject

import threading

import logging
logger = logging.getLogger(__name__)


class TickTockClientGUI:
    """ TickTock Client GUI """

    def __init__(self):

        # create the join widget
        self.join_widget = JoinWidget(title="TickTock Client",
                                      local_server_name="Localhost",
                                      external_server_name="TickTock-Server",
                                      local_server_url="http://localhost:8000",
                                      external_server_url="https://tick-tock-server-url")

        # show the join widget
        self.join_widget.show()

        # if join was NOT successful, terminate the client GUI
        if not self.join_widget.is_joined():
            return

        # if join was successful, get connection and authentication parameters from the join widget
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()

        #  create TickTock project info widget based on the authentication and connection parameters
        self.tick_tock_project_info_widget = \
            TickTockProjectInfoWidget(title="TickTock Project Info",
                                      connection_parameters=connection_parameters,
                                      authentication_parameters=authentication_parameters)

        # Obtain TickTock project info from the server
        # the project info will be set in project_parameters attribute of the info widget
        self.tick_tock_project_info_widget.obtain_project_info()

        # if TickTock project info cannot be obtained from the server, exit the GUI
        if not self.tick_tock_project_info_widget.project_parameters:
            return

        # add basic info of the project such as project id, project name, description, and etc to the info widget
        self.tick_tock_project_info_widget.add_project_basic_info()

        # add TickTock specific project info (i.e. initial tic) to the widget
        self.tick_tock_project_info_widget.add_tick_tock_project_info()

        # add accept and decline buttons to the widget
        self.tick_tock_project_info_widget.add_accept_decline_buttons()

        # show project info widget
        self.tick_tock_project_info_widget.show()

        # if participant declined to proceed, exit the GUI
        if not self.tick_tock_project_info_widget.is_accepted():
            return

        # if user agreed to proceed, create and show the TickTock dataset selection widget
        self.tick_tock_dataset_widget = TickTockDatasetWidget(title="TickTock Dataset Selection")
        self.tick_tock_dataset_widget.add_quit_run_buttons()
        self.tick_tock_dataset_widget.show()

        # if the participant didn't click on 'Run' button, terminate the client GUI
        if not self.tick_tock_dataset_widget.is_run_clicked():
            return

        # if participant clicked on 'Run', get all the parameters needed
        # to create the client project from the widgets
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()
        project_parameters = self.tick_tock_project_info_widget.get_project_parameters()

        server_url = connection_parameters[ConnectionParameter.SERVER_URL]
        username = authentication_parameters[AuthenticationParameter.USERNAME]
        token = authentication_parameters[AuthenticationParameter.TOKEN]
        project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]

        algorithm = project_parameters[HyFedProjectParameter.ALGORITHM]
        project_name = project_parameters[HyFedProjectParameter.NAME]
        project_description = project_parameters[HyFedProjectParameter.DESCRIPTION]
        coordinator = project_parameters[HyFedProjectParameter.COORDINATOR]

        tick_tock_dataset_file_path = self.tick_tock_dataset_widget.get_dataset_file_path()

        # create TickTock client project
        tick_tock_client_project = TickTockClientProject(username=username,
                                                         token=token,
                                                         server_url=server_url,
                                                         project_id=project_id,
                                                         algorithm=algorithm,
                                                         name=project_name,
                                                         description=project_description,
                                                         coordinator=coordinator,
                                                         result_dir='./tick_tock_client/result',
                                                         log_dir='./tick_tock_client/log',
                                                         tick_tock_dataset_file_path=tick_tock_dataset_file_path)

        # run TickTock client project as a thread
        tick_tock_project_thread = threading.Thread(target=tick_tock_client_project.run)
        tick_tock_project_thread.setDaemon(True)
        tick_tock_project_thread.start()

        # create and show TickTock project status widget
        tick_tock_project_status_widget = ProjectStatusWidget(title="TickTock Project Status",
                                                              project=tick_tock_client_project)
        tick_tock_project_status_widget.add_log_and_quit_buttons()
        tick_tock_project_status_widget.show()


client_gui = TickTockClientGUI()
