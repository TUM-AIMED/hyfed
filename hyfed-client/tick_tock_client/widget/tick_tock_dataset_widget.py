"""
    TickTock dataset widget to select the dataset file

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

from hyfed_client.widget.hyfed_dataset_widget import HyFedDatasetWidget
from hyfed_client.util.gui import add_label_and_textbox, add_button, select_file_path


class TickTockDatasetWidget(HyFedDatasetWidget):
    """ This widget enables users to add the file/directory dialogs and select dataset files/directories """

    def __init__(self, title):

        super().__init__(title=title)

        self.dataset_file_path_entry = add_label_and_textbox(widget=self, label_text='Dataset File',
                                                             increment_row_number=False)
        self.dataset_file_path = ''  # initialized in set_dataset_file_path function

        add_button(widget=self, button_label="Browse", column_number=2, increment_row_number=True,
                   on_click_function=self.set_dataset_file_path)

    def set_dataset_file_path(self):
        self.dataset_file_path = select_file_path(self.dataset_file_path_entry, file_types=[('txt files', '*.txt')])

    def get_dataset_file_path(self):
        return self.dataset_file_path


