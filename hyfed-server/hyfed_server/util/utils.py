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

from hyfed_server.util.data_type import DataType
import numpy as np

import logging
logger = logging.getLogger(__name__)


largest_prime_non_negative_int54 = 18014398509481951  # largest prime number that can fit in 54-bit integer


def aggregate_parameters(noisy_parameters, data_type):
    """ Aggregate the noisy parameter values from the clients """

    # if  noisy parameter values is not a list or is an empty list
    if not type(noisy_parameters) == list or not noisy_parameters:
        return None

    if data_type == DataType.NON_NEGATIVE_INTEGER:
        return np.sum(noisy_parameters) % largest_prime_non_negative_int54  # modular arithmetic

    if data_type == DataType.NEGATIVE_INTEGER or data_type == DataType.FLOAT:
        return np.sum(noisy_parameters)

    if data_type == DataType.NUMPY_ARRAY_NON_NEGATIVE_INTEGER or data_type == DataType.LIST_NUMPY_ARRAY_NON_NEGATIVE_INTEGER:
        return np.sum(noisy_parameters, axis=0) % largest_prime_non_negative_int54

    if data_type == DataType.NUMPY_ARRAY_NEGATIVE_INTEGER or data_type == DataType.NUMPY_ARRAY_FLOAT or \
            data_type == DataType.LIST_NUMPY_ARRAY_NEGATIVE_INTEGER or data_type == DataType.LIST_NUMPY_ARRAY_FLOAT:
        return np.sum(noisy_parameters, axis=0)

    return None


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