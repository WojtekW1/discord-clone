import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.core.cache import cache

ONLINE_KEY = "online_users_ids"
PRESENCE_GROUP = "presence"

@sync_to_async
def set_online(user_id: int, online: bool):
    ids = cache.get(ONLINE_KEY, set())
    ids = set(ids)
    if online:
        ids.add(user_id)
    else:
        ids.discard(user_id)
    cache.set(ONLINE_KEY, list(ids), timeout=3600)
    

class NotifyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return
    
        self.user = user
        self.group = f"notify_{user.id}"
    
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.channel_layer.group_add(PRESENCE_GROUP, self.channel_name)
    
        # ONLINE w cache (po ID)
        await set_online(user.id, True)
    
        await self.accept()
    
        # info do siebie (opcjonalnie)
        await self.send(text_data=json.dumps({"type": "status.self", "online": True}))
    
        # broadcast do wszystkich
        await self.channel_layer.group_send(PRESENCE_GROUP, {
            "type": "send_event",
            "payload": {"type": "presence.user", "user_id": user.id, "online": True}
        })

    async def disconnect(self, close_code):
        if hasattr(self, "user"):
            await set_online(self.user.id, False)
            await self.channel_layer.group_send(PRESENCE_GROUP, {
                "type": "send_event",
                "payload": {"type": "presence.user", "user_id": self.user.id, "online": False}
            })

        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

        await self.channel_layer.group_discard(PRESENCE_GROUP, self.channel_name)

    async def send_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))