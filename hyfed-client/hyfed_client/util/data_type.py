"""
    Data types specified by the developer to determine which kind of noise masking is used integer/Gaussian

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


class DataType:

    NON_NEGATIVE_INTEGER = 1
    NEGATIVE_INTEGER = 2
    FLOAT = 3

    NUMPY_ARRAY_NON_NEGATIVE_INTEGER = 4
    NUMPY_ARRAY_NEGATIVE_INTEGER = 5
    NUMPY_ARRAY_FLOAT = 6

    LIST_NUMPY_ARRAY_NON_NEGATIVE_INTEGER = 7
    LIST_NUMPY_ARRAY_NEGATIVE_INTEGER = 8
    LIST_NUMPY_ARRAY_FLOAT = 9