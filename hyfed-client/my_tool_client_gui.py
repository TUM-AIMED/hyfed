"""
    MyTool client GUI

    Copyright 2021 'My Name'. All Rights Reserved.

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

from my_tool_client.widget.my_tool_project_info_widget import MyToolProjectInfoWidget
from my_tool_client.widget.my_tool_dataset_widget import MyToolDatasetWidget
from my_tool_client.project.my_tool_client_project import MyToolClientProject

import threading

import logging
logger = logging.getLogger(__name__)


class MyToolClientGUI:
    """ MyTool Client GUI """

    def __init__(self):

        # create the join widget
        self.join_widget = JoinWidget(title="MyTool Client",
                                      local_server_name="Localhost",
                                      local_server_url="http://localhost:8000",
                                      local_compensator_name="Localhost",
                                      local_compensator_url="http://localhost:8001",
                                      external_server_name="MyTool-Server",
                                      external_server_url="https://my_tool_server_url",
                                      external_compensator_name="MyTool-Compensator",
                                      external_compensator_url="https://my_tool_compensator_url")

        # show the join widget
        self.join_widget.show()

        # if join was NOT successful, terminate the client GUI
        if not self.join_widget.is_joined():
            return

        # if join was successful, get connection and authentication parameters from the join widget
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()

        #  create MyTool project info widget based on the authentication and connection parameters
        self.my_tool_project_info_widget = MyToolProjectInfoWidget(title="MyTool Project Info",
                                                                   connection_parameters=connection_parameters,
                                                                   authentication_parameters=authentication_parameters)

        # Obtain MyTool project info from the server
        # the project info will be set in project_parameters attribute of the info widget
        self.my_tool_project_info_widget.obtain_project_info()

        # if MyTool project info cannot be obtained from the server, exit the GUI
        if not self.my_tool_project_info_widget.project_parameters:
            return

        # add basic info of the project such as project id, project name, description, and etc to the info widget
        self.my_tool_project_info_widget.add_project_basic_info()

        # add MyTool specific project info to the widget
        self.my_tool_project_info_widget.add_my_tool_project_info()

        # add accept and decline buttons to the widget
        self.my_tool_project_info_widget.add_accept_decline_buttons()

        # show project info widget
        self.my_tool_project_info_widget.show()

        # if participant declined to proceed, exit the GUI
        if not self.my_tool_project_info_widget.is_accepted():
            return

        # if user agreed to proceed, create and show the MyTool dataset selection widget
        self.my_tool_dataset_widget = MyToolDatasetWidget(title="MyTool Dataset Selection")
        self.my_tool_dataset_widget.add_quit_run_buttons()
        self.my_tool_dataset_widget.show()

        # if the participant didn't click on 'Run' button, terminate the client GUI
        if not self.my_tool_dataset_widget.is_run_clicked():
            return

        # if participant clicked on 'Run', get all the parameters needed
        # to create the client project from the widgets
        connection_parameters = self.join_widget.get_connection_parameters()
        authentication_parameters = self.join_widget.get_authentication_parameters()
        project_parameters = self.my_tool_project_info_widget.get_project_parameters()

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

        # create MyTool client project
        my_tool_client_project = MyToolClientProject(username=username,
                                                     token=token,
                                                     server_url=server_url,
                                                     compensator_url=compensator_url,
                                                     project_id=project_id,
                                                     tool=tool,
                                                     algorithm=algorithm,
                                                     name=project_name,
                                                     description=project_description,
                                                     coordinator=coordinator,
                                                     result_dir='./my_tool_client/result',
                                                     log_dir='./my_tool_client/log')

        # run MyTool client project as a thread
        my_tool_project_thread = threading.Thread(target=my_tool_client_project.run)
        my_tool_project_thread.setDaemon(True)
        my_tool_project_thread.start()

        # create and show MyTool project status widget
        my_tool_project_status_widget = HyFedProjectStatusWidget(title="MyTool Project Status",
                                                                 project=my_tool_client_project)
        my_tool_project_status_widget.add_static_labels()
        my_tool_project_status_widget.add_progress_labels()
        my_tool_project_status_widget.add_status_labels()
        my_tool_project_status_widget.add_log_and_quit_buttons()
        my_tool_project_status_widget.show()


if __name__ == "__main__":
    client_gui = MyToolClientGUI()
