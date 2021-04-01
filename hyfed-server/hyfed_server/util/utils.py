"""
    Provides utility functions

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

import logging
logger = logging.getLogger(__name__)


def client_parameters_to_list(parameter_dict, parameter_name):
    """
        Convert the dictionary containing the clients' parameters to a list
    """

    parameter_list = []
    try:
        for username in parameter_dict.keys():
            parameter_list.append(parameter_dict[username][parameter_name])
    except Exception as exp:
        logger.error(exp)
        return []

    return parameter_list
