"""
    MyTool dataset widget to select the dataset file(s)

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

from hyfed_client.widget.hyfed_dataset_widget import HyFedDatasetWidget
from hyfed_client.util.gui import add_label_and_textbox, add_button, select_file_path


class MyToolDatasetWidget(HyFedDatasetWidget):
    """ This widget enables users to add the file/directory dialogs and select dataset files/directories """

    def __init__(self, title):

        super().__init__(title=title)

