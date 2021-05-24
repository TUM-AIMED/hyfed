"""
    A widget to show the progress and status of the project

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

from hyfed_client.util.gui import add_button, add_labels, create_log_widget
from hyfed_client.util.operation import ClientOperation
from hyfed_client.util.status import ProjectStatus

import threading

import tkinter as tk
from tkinter import messagebox, filedialog


class HyFedProjectStatusWidget(tk.Tk):
    """ This widget shows progress and status of project such as current communication round, project status, etc """

    def __init__(self, title, project):

        super().__init__()

        self.title(title)
        self.project = project

        # to keep track the rows in the project status widget
        self.row_number = 1

        # project progress related labels; re-initialized in add_progress_labels
        self.comm_round_label = None
        self.step_label = None

        # project status related labels; re-initialized in add_status_labels
        self.status_label = None
        self.operation_label = None

        # for blinking project status after project is done/failed/aborted
        self.blinking_color = 'black'

        # log widget related attributed
        self.log_widget = None
        self.log_textbox = None
        self.last_shown_log_index = 0

    def show(self):
        """ Show the project status widget """

        self.resizable(0, 0)
        self.protocol("WM_DELETE_WINDOW", self.ask_quit)

        # a thread to update the project step, status, communication round, etc in the widget
        update_status_widget_thread = threading.Thread(target=self.update_status_widget)
        update_status_widget_thread.setDaemon(True)
        update_status_widget_thread.start()

        # a thread to make the project status label blinking if the project status is done/failed/aborted
        make_status_label_blinking_thread = threading.Thread(target=self.make_status_label_blinking)
        make_status_label_blinking_thread.setDaemon(True)
        make_status_label_blinking_thread.start()

        self.mainloop()

    def add_static_labels(self):
        """ Add labels whose values do not change, e.g. project name or algorithm """

        add_labels(widget=self, left_label_text="Project Name:", right_label_text=self.project.get_name())
        add_labels(widget=self, left_label_text="Algorithm:", right_label_text=self.project.get_algorithm())

    def add_progress_labels(self):
        """ Add labels indicating the progress of the project, e.g. communication round or project step """

        self.comm_round_label = add_labels(widget=self, left_label_text="Communication Round:",
                                           right_label_text=self.project.get_comm_round())
        self.step_label = add_labels(widget=self, left_label_text="Project Step:",
                                     right_label_text=self.project.get_project_step())

    def add_status_labels(self):
        """ Add labels related to the status of the project, e.g. project status or client operations """

        self.status_label = add_labels(widget=self, left_label_text="Project Status:",
                                       right_label_text=self.project.get_project_status())
        self.operation_label = add_labels(widget=self, left_label_text="Client Operation:",
                                          right_label_text=self.project.get_client_operation())

    def add_log_and_quit_buttons(self):
        """ Quit, show & export log buttons """

        add_button(widget=self, button_label="Quit", column_number=0,
                   on_click_function=self.ask_quit, sticky="")
        add_button(widget=self, button_label="Show Log", column_number=1,
                   on_click_function=self.show_log_widget, sticky="")
        add_button(widget=self, button_label="Export Log", column_number=2,
                   on_click_function=self.export_log, sticky="")

    def update_progress_labels(self):
        """ Update the value of the progress labels, e.g. communication round  and project step """

        self.comm_round_label.configure(text=self.project.get_comm_round())
        self.step_label.configure(text=self.project.get_project_step_text())

    def update_status_labels(self):
        """" Update the value of the status labels """

        self.status_label.configure(text=self.project.get_project_status_text())
        self.operation_label.configure(text=self.project.get_client_operation())

    def update_status_widget(self):
        """ Update project status widget (e.g. progress and status labels) """

        try:
            self.update_progress_labels()
            self.update_status_labels()

            self.after(500, self.update_status_widget)  # update labels every 500 ms
        except Exception as exp:
            pass

    def ask_quit(self):
        """ Ask participant whether he/she is sure about closing the widget """

        if self.project.get_client_operation() == ClientOperation.FINISHING_UP:
            messagebox.showwarning("Wait", "Finishing up the project!")
            return

        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.abort()

    def abort(self):
        """ Close project status widget if participant click on 'Quit' or 'close' button and confirm the exit """

        self.project.save_log()
        self.close_log_widget()
        self.destroy()

    def make_status_label_blinking(self):
        """ Make project status label blinking if status is done/failed/aborted """

        if self.blinking_color == 'black':
            project_status = self.project.get_project_status()
            if project_status == ProjectStatus.DONE:
                self.blinking_color = 'green'
            elif project_status == ProjectStatus.FAILED or project_status == ProjectStatus.ABORTED:
                self.blinking_color = 'red'
        else:
            self.blinking_color = 'black'

        self.status_label.configure(fg=self.blinking_color)
        self.after(500, self.make_status_label_blinking)

    # ############ log widget functions #########
    def show_log_widget(self, log_widget_title='Log'):
        """ Open log widget """

        # if log widget is already open, do nothing
        if self.log_widget is not None:
            return

        # create the log window
        self.log_widget, self.log_textbox = create_log_widget(log_widget_title)

        # add log messages to the log textbox
        self.update_log_textbox()

        # show the log window
        self.log_widget.resizable(0, 0)
        self.log_widget.protocol("WM_DELETE_WINDOW", self.close_log_widget)
        self.log_widget.mainloop()

    def close_log_widget(self):
        """ Destroy the log widget """

        try:
            self.log_widget.destroy()
            self.log_widget = None
            self.log_textbox = None
            self.last_shown_log_index = 0
        except:
            pass

    def update_log_textbox(self):
        """ Add new log messages to the log widget """

        try:
            # if log widget is NOT open, do nothing
            if self.log_textbox is None:
                return

            # add the new log messages to the widget
            log_messages = self.project.get_log_message_list()
            for message_counter in range(self.last_shown_log_index, len(log_messages)):
                self.log_textbox.insert(tk.INSERT, log_messages[message_counter] + "\n")
                self.log_textbox.yview(tk.END)
            self.last_shown_log_index = len(log_messages)

            self.after(500, self.update_log_textbox)
        except Exception as exception:
            pass

    def export_log(self):
        """ Export log messages to a participant selected file """

        log_file_path = filedialog.asksaveasfilename(defaultextension=".log")
        if log_file_path is None:
            return
        self.project.save_log(file_path=log_file_path)
