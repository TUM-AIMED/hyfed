"""
    Client-side Stats project to compute local parameters

    Copyright 2021 Reza NasiriGerdeh and Reihaneh TorkzadehMahani. All Rights Reserved.

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

from hyfed_client.project.hyfed_client_project import HyFedClientProject
from hyfed_client.util.hyfed_steps import HyFedProjectStep

from stats_client.util.stats_steps import StatsProjectStep
from stats_client.util.stats_parameters import StatsGlobalParameter, StatsLocalParameter
from stats_client.util.stats_algorithms import StatsAlgorithm

import numpy as np
import pandas as pd


class StatsClientProject(HyFedClientProject):
    """
        A class that provides the computation functions to compute local parameters
    """

    def __init__(self, username, token, project_id, server_url,
                 algorithm, name, description, coordinator, result_dir, log_dir,
                 stats_dataset_file_path, features, learning_rate, max_iterations):  # Stats specific arguments

        super().__init__(username=username, token=token, project_id=project_id, server_url=server_url,
                         algorithm=algorithm, name=name, description=description, coordinator=coordinator,
                         result_dir=result_dir, log_dir=log_dir)

        # Stats specific project attributes
        self.features = [feature.strip() for feature in features.split(',')]
        self.learning_rate = learning_rate
        self.max_iterations = max_iterations

        # Stats specific dataset related attributes
        self.stats_dataset_file_path = stats_dataset_file_path
        self.x_matrix = np.array([])  # re-initialized in the init_step function
        self.y_vector = np.array([])  # re-initialized in the init_step function

    # ########## Stats step functions
    def init_step(self):
        """ initialize dataset related attributes """

        try:
            # open stats dataset file and initialize x_matrix and y_vector attributes
            dataset_df = pd.read_csv(self.stats_dataset_file_path)
            self.x_matrix = np.array(dataset_df[self.features])
            self.y_vector = np.array(dataset_df.iloc[:, -1]).reshape(-1, 1)

            # if the algorithm is logistic regression, then add 1's column for the intercept (B0)
            if self.algorithm == StatsAlgorithm.LOGISTIC_REGRESSION:
                self.x_matrix = np.hstack((np.ones((self.x_matrix.shape[0], 1)), self.x_matrix))

            # get the number of samples
            sample_count = self.x_matrix.shape[0]

            # send the sample count to the server
            self.local_parameters[StatsLocalParameter.SAMPLE_COUNT] = sample_count

        except Exception as io_exception:
            self.log(io_exception)
            self.set_operation_status_failed()

    def sum_step(self):  # variance algorithm
        """ Compute sum over samples """

        try:
            sample_sum = np.sum(self.x_matrix, axis=0)

            # send sample sum to the server
            self.local_parameters[StatsLocalParameter.SUM] = sample_sum

        except Exception as sum_exception:
            self.log(sum_exception)
            self.set_operation_status_failed()

    def sse_step(self):  # variance algorithm
        """ Compute the sum square error between the sample values and the global mean """

        try:
            # extract global mean from the global parameters
            global_mean = self.global_parameters[StatsGlobalParameter.MEAN]

            # compute sse
            sse = np.sum(np.square(self.x_matrix - global_mean), axis=0)

            # share sse with the server
            self.local_parameters[StatsLocalParameter.SSE] = sse

        except Exception as sse_exception:
            self.log(sse_exception)
            self.set_operation_status_failed()

    def beta_step(self):  # logistic regression algorithm
        """ Compute local betas """

        try:
            # extract global beta from the global parameters
            global_beta = self.global_parameters[StatsGlobalParameter.BETA]

            # compute predicted y
            x_dot_beta = np.dot(self.x_matrix, global_beta)
            y_predicted = 1 / (1 + np.exp(-x_dot_beta))

            # compute local gradients
            local_sample_count = self.x_matrix.shape[0]
            local_gradient = np.dot(self.x_matrix.T, (y_predicted - self.y_vector)) / local_sample_count

            # compute local betas
            local_beta = global_beta - self.learning_rate * local_gradient

            # computed weighted local beta
            weighted_local_beta = local_sample_count * local_beta

            # share the weighted local betas with the server
            self.local_parameters[StatsLocalParameter.BETA] = weighted_local_beta

        except Exception as beta_exception:
            self.log(beta_exception)
            self.set_operation_status_failed()

    def compute_local_parameters(self):
        """ OVERRIDDEN: Compute the local parameters in each step of the Stats algorithms """

        try:

            super().pre_compute_local_parameters()  # MUST be called BEFORE step functions

            # ############## Stats specific local parameter computation steps
            if self.project_step == HyFedProjectStep.INIT:
                self.init_step()
            elif self.project_step == StatsProjectStep.SUM:  # variance algorithm
                self.sum_step()
            elif self.project_step == StatsProjectStep.SSE:  # variance algorithm
                self.sse_step()
            elif self.project_step == StatsProjectStep.BETA:  # logistic regression algorithm
                self.beta_step()
            elif self.project_step == HyFedProjectStep.RESULT:
                super().result_step()  # downloads the result file as zip (it is algorithm-agnostic)
            elif self.project_step == HyFedProjectStep.FINISHED:
                super().finished_step()  # the operations in the last step of the project is algorithm-agnostic

            super().post_compute_local_parameters()  # MUST be called AFTER step functions
        except Exception as computation_exception:
            self.log(computation_exception)
            super().post_compute_local_parameters()
            self.set_operation_status_failed()
