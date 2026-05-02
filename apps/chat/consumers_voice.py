import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .models import VoiceChannel, VoiceMembership, UserBan

User = get_user_model()

@sync_to_async
def voice_access(user_id: int, voice_id: int) -> bool:
    if UserBan.objects.filter(user_id=user_id, is_active=True).exists():
        return False
    # wymagamy membership (join przez HTTP)
    return VoiceMembership.objects.filter(voice_channel_id=voice_id, user_id=user_id).exists()

@sync_to_async
def get_username(user_id: int) -> str:
    return User.objects.get(pk=user_id).username

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return

        self.voice_id = int(self.scope["url_route"]["kwargs"]["voice_id"])
        allowed = await voice_access(user.id, self.voice_id)
        if not allowed:
            await self.close(code=4403)
            return

        self.user = user
        self.group_name = f"voice_{self.voice_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # poinformuj innych, że dołączył
        await self.channel_layer.group_send(self.group_name, {
            "type": "relay",
            "payload": {"type": "peer.join", "user_id": user.id, "username": user.username}
        })

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            if hasattr(self, "user"):
                await self.channel_layer.group_send(self.group_name, {
                    "type": "relay",
                    "payload": {"type": "peer.leave", "user_id": self.user.id}
                })

    async def receive(self, text_data=None, bytes_data=None):
        """
        Klient wysyła:
        {type:'webrtc.offer'|'webrtc.answer'|'webrtc.ice', to:<user_id>, from:<user_id>, data:{...}}
        """
        user = self.scope["user"]
        try:
            msg = json.loads(text_data or "{}")
        except Exception:
            return

        mtype = msg.get("type")
        to_id = msg.get("to")
        data = msg.get("data")

        if mtype not in ("webrtc.offer", "webrtc.answer", "webrtc.ice"):
            return
        if not to_id or not data:
            return

        # relay do grupy, ale każdy klient filtruje po "to"
        await self.channel_layer.group_send(self.group_name, {
            "type": "relay",
            "payload": {
                "type": mtype,
                "to": int(to_id),
                "from": user.id,
                "from_name": user.username,
                "data": data
            }
        })

    async def relay(self, event):
        await self.send(text_data=json.dumps(event["payload"]))