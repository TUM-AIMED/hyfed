"""
    server-side Stats project to aggregate the local parameters from the clients

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

from hyfed_server.project.hyfed_server_project import HyFedServerProject
from hyfed_server.util.hyfed_steps import HyFedProjectStep
from hyfed_server.util.status import ProjectStatus
from hyfed_server.util.utils import client_parameters_to_list

from stats_server.util.stats_steps import StatsProjectStep
from stats_server.util.stats_parameters import StatsGlobalParameter, StatsLocalParameter, StatsProjectParameter
from stats_server.util.stats_algorithms import StatsAlgorithm
from hyfed_server.util.data_type import DataType

import numpy as np

import logging
logger = logging.getLogger(__name__)


class StatsServerProject(HyFedServerProject):
    """ Server side of Stats project """

    def __init__(self, creation_request, project_model):
        """ Initialize Stats project attributes based on the values set by the coordinator """

        # initialize base project
        super().__init__(creation_request, project_model)

        try:
            # save project (hyper-)parameters in the project model and initialize the project
            stats_model_instance = project_model.objects.get(id=self.project_id)

            # features
            features = creation_request.data[StatsProjectParameter.FEATURES]
            stats_model_instance.features = features
            self.features = [feature.strip() for feature in features.split(',')]

            # learning rate and max iterations if algorithm is logistic regression
            if self.algorithm == StatsAlgorithm.LOGISTIC_REGRESSION:
                # learning rate
                learning_rate = float(creation_request.data[StatsProjectParameter.LEARNING_RATE])
                stats_model_instance.learning_rate = learning_rate
                self.learning_rate = learning_rate

                # max iterations
                max_iterations = int(creation_request.data[StatsProjectParameter.MAX_ITERATIONS])
                stats_model_instance.max_iterations = max_iterations
                self.max_iterations = max_iterations

            # result directory
            result_dir = "stats_server/result"
            stats_model_instance.result_dir = result_dir
            self.result_dir = result_dir

            # save the model
            stats_model_instance.save()
            logger.debug(f"Project {self.project_id}: Stats specific attributes initialized!")

            # used to keep track the iteration number in the logistic regression algorithm
            self.current_iteration = 1

            # global attributes
            self.global_sample_count = 0
            self.global_mean = 0.0
            self.global_variance = 0.0
            self.global_beta = []

        except Exception as model_exp:
            logger.error(model_exp)
            self.project_failed()

    # ############### Project step functions ####################
    def init_step(self):
        """  Init step of Stats at the server side """

        try:
            # get the sample counts from the clients and compute global sample count, which is used in the next steps
            self.global_sample_count = self.compute_aggregated_parameter(StatsLocalParameter.SAMPLE_COUNT, DataType.NON_NEGATIVE_INTEGER)

            # decide on the next step based on the algorithm name
            if self.algorithm == StatsAlgorithm.VARIANCE:
                # tell clients to go to the SUM step
                self.set_step(StatsProjectStep.SUM)

            elif self.algorithm == StatsAlgorithm.LOGISTIC_REGRESSION:
                self.global_beta = np.zeros((len(self.features)+1, 1))  # +1 is for the intercept (B0)

                # tell clients to go to the BETA step
                self.set_step(StatsProjectStep.BETA)

                # send global betas to the clients
                self.global_parameters[StatsGlobalParameter.BETA] = self.global_beta

        except Exception as init_exception:
            logger.error(f'Project {self.project_id}: {init_exception}')
            self.project_failed()

    def sum_step(self):  # variance algorithm
        """ Aggregate the sample sums from the clients to compute global mean """

        try:
            # get the sample sums from the clients and compute the global mean
            self.global_mean = self.compute_aggregated_parameter(StatsLocalParameter.SUM, DataType.NUMPY_ARRAY_FLOAT) / self.global_sample_count

            # tell clients to go to the SSE step
            self.set_step(StatsProjectStep.SSE)

            # send global mean to the clients
            self.global_parameters[StatsGlobalParameter.MEAN] = self.global_mean

        except Exception as sum_exception:
            logger.error(f'Project {self.project_id}: {sum_exception}')
            self.project_failed()

    def sse_step(self):  # variance algorithm
        """ Aggregate the sum square error values from the clients to compute global variance """

        try:
            # get the sum square error values from the clients and compute the global variance
            self.global_variance = self.compute_aggregated_parameter(StatsLocalParameter.SSE, DataType.NUMPY_ARRAY_FLOAT) / self.global_sample_count

            # this is the last computational step of the variance algorithm, so prepare the results
            self.prepare_results()

            # tell clients to go to the RESULT step to download the results
            self.set_step(HyFedProjectStep.RESULT)

        except Exception as sse_exception:
            logger.error(f'Project {self.project_id}: {sse_exception}')
            self.project_failed()

    def beta_step(self):  # logistic regression algorithm
        """ Aggregate the local betas from the clients to compute global beta """

        try:
            # get the weighted local betas from the clients, compute the global beta
            self.global_beta  = self.compute_aggregated_parameter(StatsLocalParameter.BETA, DataType.NUMPY_ARRAY_FLOAT) / self.global_sample_count

            # if this is the last iteration, then prepare the results and tell clients to go to the Result step
            if self.current_iteration == self.max_iterations:
                self.prepare_results()
                self.set_step(HyFedProjectStep.RESULT)
                return

            # increment current iteration
            self.current_iteration += 1

            # share the global beta with the clients
            self.global_parameters[StatsGlobalParameter.BETA] = self.global_beta

        except Exception as beta_exception:
            logger.error(f'Project {self.project_id}: {beta_exception}')
            self.project_failed()

    def prepare_results(self):
        """ Prepare result files for Stats project """

        try:
            project_result_dir = self.create_result_dir()

            if self.algorithm == StatsAlgorithm.VARIANCE:

                # Open result file of the variance algorithm
                variance_result_file = open(f'{project_result_dir}/variance-result.csv', 'w')

                # write header to the result file
                variance_result_file.write('total_samples')
                for feature in self.features:
                    variance_result_file.write(f',mean_{feature},variance_{feature}')
                variance_result_file.write("\n")

                # write results to the file
                variance_result_file.write(f'{self.global_sample_count}')
                for feature_counter in np.arange(len(self.features)):
                    variance_result_file.write(f',{self.global_mean[feature_counter]},{self.global_variance[feature_counter]}')
                variance_result_file.write("\n")

                # close result file
                variance_result_file.close()

            elif self.algorithm == StatsAlgorithm.LOGISTIC_REGRESSION:
                # Open result file of the logistic regression algorithm
                regression_result_file = open(f'{project_result_dir}/logistic-regression-result.csv', 'w')

                # write header to the result file
                regression_result_file.write('total_samples,learning_rate,max_iterations')
                regression_result_file.write(',B0')
                for feature in self.features:
                    regression_result_file.write(f',beta_{feature}')
                regression_result_file.write("\n")

                # write results to the file
                flatten_beta = self.global_beta.flatten()
                regression_result_file.write(f'{self.global_sample_count},{self.learning_rate},{self.max_iterations}')
                regression_result_file.write(f',{flatten_beta[0]}')
                for feature_counter in np.arange(len(self.features)):
                    regression_result_file.write(f',{flatten_beta[feature_counter+1]}')
                regression_result_file.write("\n")

                # close result file
                regression_result_file.close()

        except Exception as io_error:
            logger.error(f"Result file write error: {io_error}")
            self.project_failed()

    # ##############  Stats specific aggregation code
    def aggregate(self):
        """ OVERRIDDEN: perform Stats project specific aggregations """

        # The following four lines MUST always be called before the aggregation starts
        super().pre_aggregate()
        if self.status != ProjectStatus.AGGREGATING:  # if project failed or aborted, skip aggregation
            super().post_aggregate()
            return

        logger.debug(f'Project {self.project_id}: ## aggregate')

        if self.step == HyFedProjectStep.INIT:  # The first step name MUST always be HyFedProjectStep.INIT
            self.init_step()
        elif self.step == StatsProjectStep.SUM:  # variance algorithm
            self.sum_step()
        elif self.step == StatsProjectStep.SSE:  # variance algorithm
            self.sse_step()
        elif self.step == StatsProjectStep.BETA:  # logistic regression algorithm
            self.beta_step()
        elif self.step == HyFedProjectStep.RESULT:
            super().result_step()

        # The following line MUST be the last function call in the aggregate function
        super().post_aggregate()
