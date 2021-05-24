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

# noise values are generated in the range [MIN_INT32, MAX_INT32)
MIN_INT32 = -2147483648
MAX_INT32 = 2147483647


def is_scalar_integer(value):
    """ e.g. 10, -2 """

    return type(value) == int


def is_scalar_float(value):
    """ e.g. -1.3, 4.0 """

    return type(value) == float


def is_numpy_array(values):
    """ e.g. array([1,2,3]) or array([3.2, 4.1]) """

    return type(values) == np.ndarray


def is_integer_numpy_array(numpy_array):
    """ e.g. array([1,2,3]) """

    if not is_numpy_array(numpy_array):
        return False

    dtype = numpy_array.dtype
    if dtype == np.int8 or dtype == np.int16 or dtype == np.int32 or dtype == np.int64:
        return True

    return False


def is_list_of_numpy_arrays(values):
    """ e.g. [array([1,2,3]), array([1.2, 3.4])] """

    if type(values) != list:
        return False

    # empty list
    if not values:
        return False

    # all elements of the list are numpy arrays
    for val in values:
        if not is_numpy_array(val):
            return False

    return True


def make_noisy(original_value):
    """ Generate noise value with the same shape as the original value, add it to the original value, and return both noise and noisy value """

    try:
        if is_scalar_integer(original_value):
            noise = np.random.randint(low=MIN_INT32, high=MAX_INT32)
            noisy_value = original_value + noise
            return noisy_value, noise

        if is_scalar_float(original_value):
            noise = np.random.uniform(low=MIN_INT32, high=MAX_INT32)
            noisy_value = original_value + noise
            return noisy_value, noise

        if is_numpy_array(original_value):
            if is_integer_numpy_array(original_value):
                noise = np.random.randint(low=MIN_INT32, high=MAX_INT32, size=original_value.shape)
            else:
                noise = np.random.uniform(low=MIN_INT32, high=MAX_INT32, size=original_value.shape)

            noisy_value = original_value + noise
            return noisy_value, noise

        if is_list_of_numpy_arrays(original_value):
            noise_list = []
            noisy_values = []
            for value in original_value:
                if is_integer_numpy_array(value):
                    noise = np.random.randint(low=MIN_INT32, high=MAX_INT32, size=value.shape)
                else:
                    noise = np.random.uniform(low=MIN_INT32, high=MAX_INT32, size=value.shape)
                noisy_values.append(value + noise)
                noise_list.append(noise)

            return noisy_values, noise_list

        return None, None

    except Exception as exp:
        print(exp)
        return None, None
