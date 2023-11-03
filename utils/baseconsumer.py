from channels.generic.websocket import WebsocketConsumer

class BaseConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        super().disconnect(close_code)