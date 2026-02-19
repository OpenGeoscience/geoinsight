from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.exceptions import StopConsumer
from channels.generic.websocket import JsonWebsocketConsumer


class AnalyticsConsumer(JsonWebsocketConsumer):
    def connect(self):
        project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'analytics_{project_id}'
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)
        raise StopConsumer()

    def send_notification(self, event):
        self.send_json(content=event['message'])


class ConversionConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.group_name = 'conversion'
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)
        raise StopConsumer()

    def send_notification(self, event):
        self.send_json(content=event['message'])
