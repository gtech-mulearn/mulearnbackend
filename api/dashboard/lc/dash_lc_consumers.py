import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from db.learning_circle import UserCircleLink


class LcChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f"chat_{self.room_name}"
            self.lc_id = self.scope['url_route']['kwargs']['lc_id']
            self.user_id = self.scope['url_route']['kwargs']['user_id']

            user_circle_link = await self.get_user_circle_link()

            if user_circle_link is None:
                await self.close()
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

        except Exception as e:
            print(f"Error during WebSocket connection: {str(e)}")
            await self.close()

    @database_sync_to_async
    def get_user_circle_link(self):
        return UserCircleLink.objects.filter(
            user_id=self.user_id,
            circle_id=self.lc_id,
            accepted=True,
        ).first()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': message
            }
        )

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
