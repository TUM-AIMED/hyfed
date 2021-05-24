"""
    Serializer classes to serialize the models

    Copyright 2021 Julian Matschinske, Reza NasiriGerdeh, and Reihaneh TorkzadehMahani. All Rights Reserved.

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


from rest_framework import serializers
from hyfed_server.models import UserModel
from hyfed_server.model.hyfed_models import TokenModel, HyFedProjectModel, TimerModel, TrafficModel


# ############### Serializer classes to serve WEBAPP requests ####################
class UserSerializer(serializers.ModelSerializer):
    """
        Serializes the user information
    """

    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        """
            Create a user instance (account) when the user signs up
        """
        user = super(UserSerializer, self).create(validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user

    class Meta:
        # TODO: remove attributes not needed
        model = UserModel
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'password', 'date_joined')
        write_only_fields = ('password',)
        read_only_fields = ('id', 'date_joined',)


class HyFedProjectSerializer(serializers.ModelSerializer):
    """
        Serializes the HyFed project model fields to WebApp and client
    """

    id = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    coordinator = serializers.SerializerMethodField()

    # runtime stats
    client_computation = serializers.SerializerMethodField()
    client_network_send = serializers.SerializerMethodField()
    client_network_receive = serializers.SerializerMethodField()
    client_idle = serializers.SerializerMethodField()
    compensator_computation = serializers.SerializerMethodField()
    compensator_network_send = serializers.SerializerMethodField()
    server_computation = serializers.SerializerMethodField()
    runtime_total = serializers.SerializerMethodField()

    # traffic stats between components
    client_server = serializers.SerializerMethodField()
    server_client = serializers.SerializerMethodField()
    client_compensator = serializers.SerializerMethodField()
    compensator_server = serializers.SerializerMethodField()
    traffic_total = serializers.SerializerMethodField()

    def get_id(self, instance):
        """ Convert id from UUID type to string """
        return str(instance.id)

    def get_coordinator(self, instance):
        """ Get the username of the coordinator """
        return instance.coordinator.username

    def get_roles(self, instance):
        """
            Get the role(s) (coordinator|participant|both) of the user
        """
        roles = []

        try:
            if instance.coordinator == self.context['request'].user:
                roles.append('coordinator')

            if self.context['request'].user in UserModel.objects.filter(projects__project=instance).all():
                roles.append('participant')

            return roles
        except:
            return ['-']

    # functions to get the client/compensator/server times
    def get_client_computation(self, instance):
        return instance.timer.client_computation

    def get_client_network_send(self, instance):
        return instance.timer.client_network_send

    def get_client_network_receive(self, instance):
        return instance.timer.client_network_receive

    def get_client_idle(self, instance):
        return instance.timer.client_idle

    def get_compensator_computation(self, instance):
        return instance.timer.compensator_computation

    def get_compensator_network_send(self, instance):
        return instance.timer.compensator_network_send

    def get_server_computation(self, instance):
        return instance.timer.server_computation

    def get_runtime_total(self, instance):
        return instance.timer.runtime_total

    def get_client_server(self, instance):
        return instance.traffic.client_server

    def get_server_client(self, instance):
        return instance.traffic.server_client

    def get_client_compensator(self, instance):
        return instance.traffic.client_compensator

    def get_compensator_server(self, instance):
        return instance.traffic.compensator_server

    def get_traffic_total(self, instance):
        return instance.traffic.traffic_total

    class Meta:
        model = HyFedProjectModel
        fields = ('id', 'coordinator', 'tool', 'algorithm', 'name', 'description', 'status', 'step', 'comm_round',
                  'roles', 'created_at', 'client_computation', 'client_network_send', 'client_network_receive', 'client_idle',
                  'compensator_computation', 'compensator_network_send', 'server_computation', 'runtime_total',
                  'client_server', 'server_client', 'client_compensator', 'compensator_server', 'traffic_total')

        read_only_fields = ('id', 'created_at',)


class TokenSerializer(serializers.ModelSerializer):
    """
        Serializes the token with customized fields
    """

    username = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    def get_username(self, instance):
        try:
            return instance.participant.username
        except:
            return "-"

    def get_roles(self, instance):
        roles = []

        try:
            if instance.participant.id == instance.project.coordinator.id:
                roles.append('coordinator')
                roles.append('participant')
            else:
                roles.append('participant')

            return roles
        except:
            return ['-']

    class Meta:
        model = TokenModel
        fields = ('id', 'username', 'roles')


class TimerSerializer(serializers.ModelSerializer):

    class Meta:
        model = TimerModel
        fields = ('id', 'computation', 'network_send', 'network_receive', 'idle', 'aggregation')


class TrafficSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficModel
        fields = ('id', 'client_server', 'server_client')
