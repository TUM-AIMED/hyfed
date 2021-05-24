"""
    Stats client GUI

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
from hyfed_client.widget.hyfed_project_status_widget import HyFedProjectStatusWidget
from hyfed_client.util.hyfed_parameters import HyFedProjectParameter, ConnectionParameter, AuthenticationParameter

from stats_client.widget.stats_project_info_widget import StatsProjectInfoWidget
from stats_client.widget.stats_dataset_widget import StatsDatasetWidget
from stats_client.project.stats_client_project import StatsClientProject
from stats_client.util.stats_parameters import StatsProjectParameter

import threading

import logging
logger = logging.getLogger(__name__)


class StatsClientGUI:
    """ Stats Client GUI """

    def __init__(self):

        # create the join widget
        self.join_widget = JoinWidget(title="Stats Client",
                                      local_server_name="Localhost",
                                      local_server_url="http://localhost:8000",
                                      local_compensator_name="Localhost",
                                      local_compensator_url="http://localhost:8001",
                                      external_server_name="Stats-Server",
                                      external_server_url="https://stats_server_url",
                                      external_compensator_name="Stats-Compensator",
                                      external_compensator_url="https://stats_compensator_url")

        # show the join widget
        self.join_widget.show()

        # if join was NOT successful, terminate the client GUI
        if not self.join_widget.is_joined():
            return

        # if join was successful, get connection and authentication parameters from the join widget
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()

        #  create Stats project info widget based on the authentication and connection parameters
        self.stats_project_info_widget = StatsProjectInfoWidget(title="Stats Project Info",
                                                                connection_parameters=connection_parameters,
                                                                authentication_parameters=authentication_parameters)

        # Obtain Stats project info from the server
        # the project info will be set in project_parameters attribute of the info widget
        self.stats_project_info_widget.obtain_project_info()

        # if Stats project info cannot be obtained from the server, exit the GUI
        if not self.stats_project_info_widget.project_parameters:
            return

        # add basic info of the project such as project id, project name, description, and etc to the info widget
        self.stats_project_info_widget.add_project_basic_info()

        # add Stats specific project info to the widget
        self.stats_project_info_widget.add_stats_project_info()

        # add accept and decline buttons to the widget
        self.stats_project_info_widget.add_accept_decline_buttons()

        # show project info widget
        self.stats_project_info_widget.show()

        # if participant declined to proceed, exit the GUI
        if not self.stats_project_info_widget.is_accepted():
            return

        # if user agreed to proceed, create and show the Stats dataset selection widget
        self.stats_dataset_widget = StatsDatasetWidget(title="Stats Dataset Selection")
        self.stats_dataset_widget.add_quit_run_buttons()
        self.stats_dataset_widget.show()

        # if the participant didn't click on 'Run' button, terminate the client GUI
        if not self.stats_dataset_widget.is_run_clicked():
            return

        # if participant clicked on 'Run', get all the parameters needed
        # to create the client project from the widgets
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()
        project_parameters = self.stats_project_info_widget.get_project_parameters()

        server_url = connection_parameters[ConnectionParameter.SERVER_URL]
        compensator_url = connection_parameters[ConnectionParameter.COMPENSATOR_URL]
        username = authentication_parameters[AuthenticationParameter.USERNAME]
        token = authentication_parameters[AuthenticationParameter.TOKEN]
        project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]

        tool = project_parameters[HyFedProjectParameter.TOOL]
        algorithm = project_parameters[HyFedProjectParameter.ALGORITHM]
        project_name = project_parameters[HyFedProjectParameter.NAME]
        project_description = project_parameters[HyFedProjectParameter.DESCRIPTION]
        coordinator = project_parameters[HyFedProjectParameter.COORDINATOR]

        # Stats specific project info
        features = project_parameters[StatsProjectParameter.FEATURES]
        learning_rate = project_parameters[StatsProjectParameter.LEARNING_RATE]
        max_iterations = project_parameters[StatsProjectParameter.MAX_ITERATIONS]

        stats_dataset_file_path = self.stats_dataset_widget.get_dataset_file_path()

        # create Stats client project
        stats_client_project = StatsClientProject(username=username,
                                                  token=token,
                                                  server_url=server_url,
                                                  compensator_url=compensator_url,
                                                  project_id=project_id,
                                                  tool=tool,
                                                  algorithm=algorithm,
                                                  name=project_name,
                                                  description=project_description,
                                                  coordinator=coordinator,
                                                  result_dir='./stats_client/result',
                                                  log_dir='./stats_client/log',
                                                  stats_dataset_file_path=stats_dataset_file_path,
                                                  features=features,
                                                  learning_rate=learning_rate,
                                                  max_iterations=max_iterations)

        # run Stats client project as a thread
        stats_project_thread = threading.Thread(target=stats_client_project.run)
        stats_project_thread.setDaemon(True)
        stats_project_thread.start()

        # create and show Stats project status widget
        stats_project_status_widget = HyFedProjectStatusWidget(title="Stats Project Status",
                                                               project=stats_client_project)
        stats_project_status_widget.add_static_labels()
        stats_project_status_widget.add_progress_labels()
        stats_project_status_widget.add_status_labels()
        stats_project_status_widget.add_log_and_quit_buttons()
        stats_project_status_widget.show()


if __name__ == "__main__":
    client_gui = StatsClientGUI()
