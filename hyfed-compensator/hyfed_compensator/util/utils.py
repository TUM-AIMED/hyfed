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

from hyfed_compensator.util.data_type import DataType
import numpy as np

import logging
logger = logging.getLogger(__name__)

largest_prime_non_negative_int54 = 18014398509481951  # largest prime number that can fit in 54-bit integer


def aggregate(noise_values, data_type):
    """ Aggregate the noise values from the clients """

    # if noise_values is not a list or is an empty list
    if not type(noise_values) == list or not noise_values:
        return None

    if data_type == DataType.NON_NEGATIVE_INTEGER:
        return np.sum(noise_values) % largest_prime_non_negative_int54  # modular arithmetic

    if data_type == DataType.NEGATIVE_INTEGER or data_type == DataType.FLOAT:
        return np.sum(noise_values)

    if data_type == DataType.NUMPY_ARRAY_NON_NEGATIVE_INTEGER or data_type == DataType.LIST_NUMPY_ARRAY_NON_NEGATIVE_INTEGER:
        return np.sum(noise_values, axis=0) % largest_prime_non_negative_int54

    if data_type == DataType.NUMPY_ARRAY_NEGATIVE_INTEGER or data_type == DataType.NUMPY_ARRAY_FLOAT or \
            data_type == DataType.LIST_NUMPY_ARRAY_NEGATIVE_INTEGER or data_type == DataType.LIST_NUMPY_ARRAY_FLOAT:
        return np.sum(noise_values, axis=0)

    return None
