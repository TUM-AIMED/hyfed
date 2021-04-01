"""
    A widget to obtain the project info from the server and display them to the participant

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

from hyfed_client.util.gui import add_label_and_textbox, add_button
from hyfed_client.util.hyfed_parameters import AuthenticationParameter, Parameter, HyFedProjectParameter, ConnectionParameter
from hyfed_client.util.endpoint import EndPoint

import requests
import tkinter as tk
import pickle
import time
from tkinter import messagebox


class HyFedProjectInfoWidget(tk.Tk):
    """ This widget employs the authentication parameters to obtain the project info from the server """

    def __init__(self, title, authentication_parameters, connection_parameters):

        super().__init__()

        self.title(title)

        # required to get project info from the server
        self.server_url = connection_parameters[ConnectionParameter.SERVER_URL]
        self.username = authentication_parameters[AuthenticationParameter.USERNAME]
        self.token = authentication_parameters[AuthenticationParameter.TOKEN]
        self.project_id = authentication_parameters[AuthenticationParameter.PROJECT_ID]

        # self.project_parameters will be initialized in obtain_project_info function
        self.project_parameters = {}

        # a flag to indicate whether the participant accepted to proceed with the project
        self.accepted = False

        # project info widget GUI
        self.row_number = 1
        add_label_and_textbox(self, label_text="Username",
                              value=self.username, status='disabled')
        add_label_and_textbox(self, label_text="Server Name",
                              value=connection_parameters[ConnectionParameter.SERVER_NAME], status='disabled')
        add_label_and_textbox(self, label_text="Server URL",
                              value=self.server_url, status='disabled')

    def show(self):
        """ Show the project info widget """

        self.resizable(0, 0)
        self.protocol("WM_DELETE_WINDOW", self.ask_quit)
        self.mainloop()

    def add_accept_decline_buttons(self):
        """ Decline and accept buttons """

        add_button(widget=self, button_label="Decline", column_number=0, on_click_function=self.ask_quit)
        add_button(widget=self, button_label="Accept", column_number=1, on_click_function=self.accept_to_proceed)

    def accept_to_proceed(self):
        """ Set the accepted flag to True if participant accepted to proceed """

        self.accepted = True
        self.destroy()

    def obtain_project_info(self):
        """ Send a get request to the server to obtain the project basic info (e.g. project name) """

        max_tries = 20
        for _ in range(max_tries):
            try:
                # create request body using authentication parameter values
                request_body = {Parameter.AUTHENTICATION:
                                    {AuthenticationParameter.USERNAME: self.username,
                                     AuthenticationParameter.TOKEN: self.token,
                                     AuthenticationParameter.PROJECT_ID: self.project_id}
                                }

                serialized_request_body = pickle.dumps(request_body)

                # send a request to server to obtain the project info
                response = requests.get(url=f'{self.server_url}/{EndPoint.PROJECT_INFO}',
                                        data=serialized_request_body,
                                        timeout=60)

                if response.status_code != 200:
                    print(f"Got response {response.status_code}!")
                    time.sleep(10)
                    continue

                # deserialize response and initialize project_parameters
                json_response = pickle.loads(response.content)
                self.project_parameters = json_response[Parameter.PROJECT]
                return

            except Exception as exception:
                print(exception)
                time.sleep(10)

    def add_project_basic_info(self):
        """
            Add project basic info including project id, algorithm,
            project name, project description, and coordinator to the project info widget
        """

        add_label_and_textbox(self, label_text="Project ID",
                              value=self.project_parameters[HyFedProjectParameter.ID], status='disabled')
        add_label_and_textbox(self, label_text="Token",
                              value=self.token, status='disabled')
        add_label_and_textbox(self, label_text="Project Name",
                              value=self.project_parameters[HyFedProjectParameter.NAME], status='disabled')
        add_label_and_textbox(self, label_text="Project Description",
                              value=self.project_parameters[HyFedProjectParameter.DESCRIPTION], status='disabled')

        add_label_and_textbox(self, label_text="Algorithm",
                              value=self.project_parameters[HyFedProjectParameter.ALGORITHM], status='disabled')
        add_label_and_textbox(self, label_text="Coordinator",
                              value=self.project_parameters[HyFedProjectParameter.COORDINATOR], status='disabled')

    def ask_quit(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.destroy()

    # getter functions
    def get_project_parameters(self):
        return self.project_parameters

    def is_accepted(self):
        return self.accepted
