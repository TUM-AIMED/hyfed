"""
    Django models (tables) to store the HyFed project, token, runtime, and network traffic attributes

    Copyright 2021 Reza NasiriGerdeh, Julian Matschinske, and Reihaneh TorkzadehMahani. All Rights Reserved.

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

from django.db import models
from hyfed_server.util.status import ProjectStatus
from hyfed_server.util.hyfed_steps import HyFedProjectStep

import uuid


PROJECT_STATES = ((ProjectStatus.CREATED, ProjectStatus.CREATED),
                  (ProjectStatus.PARAMETERS_READY, ProjectStatus.PARAMETERS_READY),
                  (ProjectStatus.AGGREGATING, ProjectStatus.AGGREGATING),
                  (ProjectStatus.DONE, ProjectStatus.DONE),
                  (ProjectStatus.ABORTED, ProjectStatus.ABORTED),
                  (ProjectStatus.FAILED, ProjectStatus.FAILED),)


class HyFedProjectModel(models.Model):
    """
        Common attributes of a project (description, coordination, synchronization, and monitoring)
        independent of the algorithm
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coordinator = models.ForeignKey('UserModel', on_delete=models.CASCADE)
    tool = models.CharField(max_length=255, default="")
    algorithm = models.CharField(max_length=255, default="")
    name = models.CharField(max_length=255, default="")
    description = models.CharField(max_length=255, default="")
    status = models.CharField(max_length=31, choices=PROJECT_STATES, default=ProjectStatus.CREATED)
    step = models.CharField(max_length=255, default=HyFedProjectStep.INIT)
    comm_round = models.PositiveIntegerField(default=1)  # communication round
    timer = models.ForeignKey('TimerModel', on_delete=models.CASCADE)
    traffic = models.ForeignKey('TrafficModel', on_delete=models.CASCADE)
    result_dir = models.CharField(max_length=1000, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TokenModel(models.Model):
    """
        Token to authenticate a participant (client);
        Each token corresponds exactly to one participant (1 -> 1 relationship);
        Each project can have multiple participants and each participant can be a member of multiple projects
        (N -> N relationship)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey('HyFedProjectModel', on_delete=models.CASCADE, related_name='participants')
    participant = models.ForeignKey('UserModel', on_delete=models.CASCADE, null=True, blank=True, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'participant')


class TimerModel(models.Model):
    """
        Runtime statistics of the clients (computation, network, and idle times) and
        the server (aggregation time) until current communication round;
        client statistics are averaged over the clients;
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_computation = models.FloatField(default=0.0)
    client_network_send = models.FloatField(default=0.0)
    client_network_receive = models.FloatField(default=0.0)
    client_idle = models.FloatField(default=0.0)
    compensator_computation = models.FloatField(default=0.0)
    compensator_network_send = models.FloatField(default=0.0)
    server_computation = models.FloatField(default=0.0)
    runtime_total = models.FloatField(default=0.0)


class TrafficModel(models.Model):
    """ Network traffic statistics client <-> server and client -> compensator  """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_server = models.CharField(max_length=32, default='0.00 KB')
    server_client = models.CharField(max_length=32, default='0.00 KB')
    client_compensator = models.CharField(max_length=32, default='0.00 KB')
    compensator_server = models.CharField(max_length=32, default='0.00 KB')
    traffic_total = models.CharField(max_length=32, default='0.00 KB')

