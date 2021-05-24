"""
    Utility functions

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

import numpy as np

import logging
logger = logging.getLogger(__name__)


def is_scalar(value):
    """ e.g. 2 or 5.6 """

    return type(value) == int or type(value) == float


def is_numpy_array(values):
    """ e.g. array([1,2,3]) or array([[3.2, 4.1], [5, 6]]) """

    return type(values) == np.ndarray


def is_list_of_scalars(values):
    """ e.g. [1,2,4,5] or [1.3, 4.2] """

    if type(values) == list:

        # empty list
        if not values:
            return False

        # all elements of the list are scalar values
        for val in values:
            if not is_scalar(val):
                return False

        return True

    return False


def is_list_of_numpy_arrays(values):
    """ e.g. [array([1,2,3]), array([1.2, 3.4])] """

    if type(values) == list:

        # empty list
        if not values:
            return False

        # all elements of the list are numpy arrays
        for val in values:
            if not is_numpy_array(val):
                return False

        return True

    return False


def is_list_of_list_of_numpy_arrays(values):
    """ e.g. [ [array([1.0, 2.0, 3.0]), array([1.2, 3.4])], [array([2.5, 2.1, 3.4]), array([5.5, 3.2])]] """

    if type(values) == list:

        # empty list
        if not values:
            return False

        # all elements of the list are numpy arrays
        for value in values:
            if type(value) != list:
                return False
            for val in value:
                if not is_numpy_array(val):
                    return False

        return True

    return False


def aggregate(noise_values):
    """ Aggregate the noise values from the clients """

    if is_list_of_scalars(noise_values):
        return np.sum(noise_values)

    if is_list_of_numpy_arrays(noise_values):
        return np.sum(noise_values, axis=0)

    if is_list_of_list_of_numpy_arrays(noise_values):
        for numpy_array_index in range(len(noise_values[0])):
            return np.sum(np.array(noise_values), axis=0)

    return None
