import json

from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

from api.common.landing_stats import landing_stats

# The model signal receivers that lived here are in api/common/signals.py, registered by
# ApiConfig.ready() (issue 0030).


class GlobalCount(WebsocketConsumer):
    data = {}
    group_name = "landing_stats"

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
                self.group_name, 
                self.channel_name
            )
        self.accept()

        self.data = landing_stats.snapshot()

        self.send(text_data=json.dumps(self.data))
    
    def disconnect(self, code):
        # group_discard is a coroutine: without async_to_sync it was never
        # awaited, so closed sockets stayed in the group until Redis expired them.
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )
    
    def send_data(self, event):
        self.send(text_data=json.dumps(event['data']))
