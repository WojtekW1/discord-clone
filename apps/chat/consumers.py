import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import Channel, ChannelMembership, Message, DMConversation, UserBan
from .permissions import can_delete_any_message

User = get_user_model()

@sync_to_async
def is_banned(user_id):
    return UserBan.objects.filter(user_id=user_id, is_active=True).exists()

@sync_to_async
def has_channel_access(user_id, channel_id):
    ch = Channel.objects.get(pk=channel_id)
    if ch.is_public:
        return True
    return ChannelMembership.objects.filter(channel_id=channel_id, user_id=user_id).exists()

@sync_to_async
def create_channel_message(channel_id, user_id, text):
    msg = Message.objects.create(channel_id=channel_id, author_id=user_id, text=text)
    return msg.id

@sync_to_async
def create_dm_message(dm_id, user_id, text):
    msg = Message.objects.create(dm_conversation_id=dm_id, author_id=user_id, text=text)
    return msg.id

@sync_to_async
def serialize_message(msg: Message):
    msg = Message.objects.select_related("author").get(pk=msg.pk)
    return {
        "id": msg.id,
        "author": msg.author.username,
        "author_id": msg.author_id,
        "text": "[deleted]" if msg.is_deleted else msg.text,
        "image_url": msg.image.url if msg.image else "",
        "audio_url": msg.audio.url if msg.audio else "",
        "created_at": msg.created_at.isoformat(),
        "is_deleted": msg.is_deleted,
    }

@sync_to_async
def serialize_message_by_id(message_id: int):
    msg = Message.objects.select_related("author").get(pk=message_id)
    return {
        "id": msg.id,
        "author": msg.author.username,
        "author_id": msg.author_id,
        "text": "[deleted]" if msg.is_deleted else msg.text,
        "image_url": msg.image.url if msg.image else "",
        "audio_url": msg.audio.url if msg.audio else "",
        "created_at": msg.created_at.isoformat(),
        "is_deleted": msg.is_deleted,
    }

@sync_to_async
def delete_message(message_id, user):
    msg = Message.objects.select_related("author").get(pk=message_id)
    if msg.is_deleted:
        return None
    # author can delete own; moderator can delete any
    if msg.author_id != user.id and not can_delete_any_message(user):
        return None
    msg.is_deleted = True
    msg.text = ""
    msg.save(update_fields=["is_deleted", "text"])
    return {
        "id": msg.id,
        "scope": msg.scope(),
    }

@sync_to_async
def dm_access(user_id, dm_id):
    dm = DMConversation.objects.get(pk=dm_id)
    return (dm.user1_id == user_id) or (dm.user2_id == user_id)

@sync_to_async
def get_channel_member_ids(channel_id: int):
    return list(ChannelMembership.objects.filter(channel_id=channel_id).values_list("user_id", flat=True))

@sync_to_async
def get_dm_participant_ids(dm_id: int):
    dm = DMConversation.objects.get(pk=dm_id)
    return [dm.user1_id, dm.user2_id]

class BaseChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self._accepted = False
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        if await is_banned(user.id):
            await self.close(code=4403)
            return
        await self.accept()
        self._accepted = True

    async def send_event(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

class ChannelConsumer(BaseChatConsumer):
    async def connect(self):
        await super().connect()
        if not getattr(self, "_accepted", False):
            return
        self.channel_id = int(self.scope["url_route"]["kwargs"]["channel_id"])
        user = self.scope["user"]
        try:
            allowed = await has_channel_access(user.id, self.channel_id)
        except Channel.DoesNotExist:
            await self.close(code=4404)
            return
        if not allowed:
            await self.close(code=4403)
            return

        self.group_name = f"channel_{self.channel_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        # presence ping
        await self.channel_layer.group_send(self.group_name, {
            "type": "send_event",
            "payload": {"type": "user.status", "user": user.username, "status": "online", "ts": timezone.now().isoformat()}
        })

    async def disconnect(self, close_code):
        user = self.scope.get("user", None)
        if hasattr(self, "group_name"):
            if user and user.is_authenticated:
                await self.channel_layer.group_send(self.group_name, {
                    "type": "send_event",
                    "payload": {"type": "user.status", "user": user.username, "status": "offline", "ts": timezone.now().isoformat()}
                })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        data = json.loads(text_data or "{}")
        action = data.get("action", "send")

        if action == "delete":
            mid = int(data.get("message_id", 0))
            result = await delete_message(mid, user)
            if result:
                await self.channel_layer.group_send(self.group_name, {
                    "type": "send_event",
                    "payload": {"type": "message.delete", "message_id": mid}
                })
            return

        text = (data.get("text") or "").strip()
        if not text:
            return
        msg_id = await create_channel_message(self.channel_id, user.id, text)
        payload = await serialize_message_by_id(msg_id)

        await self.channel_layer.group_send(self.group_name, {
            "type": "send_event",
            "payload": {"type": "message.new", **payload}
        })

        member_ids = await get_channel_member_ids(self.channel_id)
        for uid in member_ids:
            if uid == user.id:
                continue
            await self.channel_layer.group_send(f"notify_{uid}", {
                "type": "send_event",
                "payload": {"type": "notify.message", "scope": f"channel:{self.channel_id}"}
            })

class DMConsumer(BaseChatConsumer):
    async def connect(self):
        await super().connect()
        if not getattr(self, "_accepted", False):
            return
        self.dm_id = int(self.scope["url_route"]["kwargs"]["dm_id"])
        user = self.scope["user"]
        try:
            allowed = await dm_access(user.id, self.dm_id)
        except DMConversation.DoesNotExist:
            await self.close(code=4404)
            return
        if not allowed:
            await self.close(code=4403)
            return

        self.group_name = f"dm_{self.dm_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        user = self.scope["user"]
        data = json.loads(text_data or "{}")
        action = data.get("action", "send")

        if action == "delete":
            mid = int(data.get("message_id", 0))
            result = await delete_message(mid, user)
            if result:
                await self.channel_layer.group_send(self.group_name, {
                    "type": "send_event",
                    "payload": {"type": "message.delete", "message_id": mid}
                })
            return

        text = (data.get("text") or "").strip()
        if not text:
            return
        msg_id = await create_dm_message(self.dm_id, user.id, text)
        payload = await serialize_message_by_id(msg_id)
        
        await self.channel_layer.group_send(self.group_name, {
            "type": "send_event",
            "payload": {"type": "message.new", **payload}
        })

        pids = await get_dm_participant_ids(self.dm_id)
        for uid in pids:
            if uid == user.id:
                continue
            await self.channel_layer.group_send(f"notify_{uid}", {
                "type": "send_event",
                "payload": {"type": "notify.message", "scope": f"dm:{self.dm_id}"}
            })
