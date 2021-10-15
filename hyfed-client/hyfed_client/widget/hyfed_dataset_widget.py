"""
    A widget to select the dataset files

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
from hyfed_client.util.gui import add_button

import tkinter as tk
from tkinter import messagebox


class HyFedDatasetWidget(tk.Tk):
    """ The base widget for the derived dataset widgets """

    def __init__(self, title):

        super().__init__()

        self.title(title)

        self.row_number = 1
        self.textbox_width = 20

        self.run_clicked = False

    def show(self):
        """ Show dataset widget """

        self.resizable(0, 0)
        self.protocol("WM_DELETE_WINDOW", self.ask_quit)
        self.mainloop()

    def add_quit_run_buttons(self):
        """ Quit and Run buttons """

        add_button(widget=self, button_label="Quit", column_number=0, on_click_function=self.ask_quit)
        add_button(widget=self, button_label="Run", column_number=1, on_click_function=self.click_on_run)

    def click_on_run(self):
        """ If participant clicked on Run, set run_clicked flag to True """

        self.run_clicked = True
        self.destroy()

    def ask_quit(self):
        """ Show exit confirmation message box to the participant """

        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.destroy()

    # getter function
    def is_run_clicked(self):
        return self.run_clicked
