"""
    A widget to join the project

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


from hyfed_client.util.hyfed_parameters import Parameter, CoordinationParameter, AuthenticationParameter, ConnectionParameter
from hyfed_client.util.gui import add_label_and_textbox, add_label_and_password_box, add_option_menu, add_button
from hyfed_client.util.endpoint import EndPoint

import requests
import pickle
from tkinter import messagebox
import tkinter as tk


class JoinWidget(tk.Tk):
    """ A widget enabling the participants to enter the username, password, etc to join the project """

    def __init__(self, title,
                 local_server_name="Localhost",
                 local_server_url="http://localhost:8000",
                 local_compensator_name="Localhost",
                 local_compensator_url="http://localhost:8001",
                 external_server_name="AIMed-TUM",
                 external_server_url="https://aimed_tum_url",
                 external_compensator_name="MRI-TUM",
                 external_compensator_url="https://mri_tum_url",
                 ):

        super().__init__()

        self.title(title)

        # server and compensator related attributes
        self.local_server_name = local_server_name
        self.local_server_url = local_server_url
        self.local_compensator_name = local_compensator_name
        self.local_compensator_url = local_compensator_url

        self.external_server_name = external_server_name
        self.external_server_url = external_server_url
        self.external_compensator_name = external_compensator_name
        self.external_compensator_url = external_compensator_url

        # a flag to indicate whether or not join process has been successful
        self.joined = False

        # joint widget GUI
        self.row_number = 1
        self.textbox_width = 20
        self.server_choice = add_option_menu(widget=self, label_text='Server',
                                             choices=(local_server_name, external_server_name))

        self.compensator_choice = add_option_menu(widget=self, label_text='Compensator',
                                                  choices=(local_compensator_name, external_compensator_name))

        self.username_entry = add_label_and_textbox(widget=self, label_text="Username")
        self.password_entry = add_label_and_password_box(widget=self, label_text="Password")
        self.project_id_entry = add_label_and_textbox(widget=self, label_text="Project ID")
        self.token_entry = add_label_and_textbox(widget=self, label_text="Token")

        add_button(widget=self, button_label="Quit", column_number=0, on_click_function=self.quit_project)
        add_button(widget=self, button_label="Join", column_number=1, on_click_function=self.join_project)

        #  these attributes are re-initialized in the join_project function
        self.username = ''
        self.token = ''
        self.server_name = ''
        self.server_url = ''
        self.compensator_name = ''
        self.compensator_url = ''
        self.project_id = ''

        # connection and and authentication parameters will be used in the next widgets (e.g. project info widget)
        self.connection_parameters = {}
        self.authentication_parameters = {}

    def show(self):
        """ Show the join widget """

        self.resizable(0, 0)
        self.mainloop()

    def quit_project(self):
        """ Close the join widget """

        self.joined = False
        self.destroy()

    def join_project(self):
        """ Get the value of authentication parameters from the participant and send join request to server """

        # extract the values entered by the participant
        self.server_name = self.server_choice.get()
        self.compensator_name = self.compensator_choice.get()
        self.username = self.username_entry.get()
        password = self.password_entry.get()
        self.token = self.token_entry.get()
        self.project_id = self.project_id_entry.get()

        # initialize server url based on server name
        if self.server_name == self.local_server_name:
            self.server_url = self.local_server_url
        elif self.server_name == self.external_server_name:
            self.server_url = self.external_server_url

        # initialize compensator url based on compensator name
        if self.compensator_name == self.local_compensator_name:
            self.compensator_url = self.local_compensator_url
        elif self.compensator_name == self.external_compensator_name:
            self.compensator_url = self.external_compensator_url

        # Ensure none of the input entries are empty
        if not self.username:
            messagebox.showerror("Error", "Username cannot be empty!")
            return

        if not password:
            messagebox.showerror("Error", "Password cannot be empty!")
            return

        if not self.project_id:
            messagebox.showerror("Error", "Project ID cannot be empty!")
            return

        if not self.token:
            messagebox.showerror("Error", "Token cannot be empty!")
            return

        # ensure server and compensator IPs are different
        server_ip = self.server_url.split(':')[1][2:]
        compensator_ip = self.compensator_url.split(':')[1][2:]

        if server_ip == compensator_ip and server_ip != '127.0.0.1' and server_ip != 'localhost':
            messagebox.showerror("Error", "Server and compensator IPs must be different!")
            return

        # send join request to the server
        try:
            request_body = {Parameter.AUTHENTICATION:
                                {AuthenticationParameter.USERNAME: self.username,
                                 AuthenticationParameter.PASSWORD: password,
                                 AuthenticationParameter.TOKEN: self.token,
                                 AuthenticationParameter.PROJECT_ID: self.project_id}
                            }
            serialized_request_body = pickle.dumps(request_body)

            response = requests.post(f'{self.server_url}/{EndPoint.PROJECT_JOIN}',
                                     data=serialized_request_body,
                                     timeout=60)

            if response.status_code != 200:
                messagebox.showerror("Error", f"Got response {response.status_code}!")
                return
        except Exception as io_exception:
            print(io_exception)
            messagebox.showerror("Error", "Connection failed!")
            return

        # check whether join was successful
        json_response = pickle.loads(response.content)
        self.joined = json_response[CoordinationParameter.CLIENT_JOINED]

        if not self.joined:
            messagebox.showerror("Error", "Authentication failed!")
            return

        # initialize connection parameters
        self.connection_parameters[ConnectionParameter.SERVER_NAME] = self.server_name
        self.connection_parameters[ConnectionParameter.SERVER_URL] = self.server_url
        self.connection_parameters[ConnectionParameter.COMPENSATOR_NAME] = self.compensator_name
        self.connection_parameters[ConnectionParameter.COMPENSATOR_URL] = self.compensator_url

        # initialize authentication parameters
        self.authentication_parameters[AuthenticationParameter.USERNAME] = self.username
        self.authentication_parameters[AuthenticationParameter.PROJECT_ID] = self.project_id
        self.authentication_parameters[AuthenticationParameter.TOKEN] = self.token

        self.destroy()

    # getter functions
    def is_joined(self):
        return self.joined

    def get_connection_parameters(self):
        return self.connection_parameters

    def get_authentication_parameters(self):
        return self.authentication_parameters
