from django.db import models
from django.conf import settings
from django.db.models import Q, UniqueConstraint
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Channel(models.Model):
    name = models.CharField(max_length=64, unique=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_channels")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        permissions = [
            ("can_manage_channels", "Can create/manage channels"),
        ]

    def __str__(self):
        return f"#{self.name}"

class ChannelMembership(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="channel_memberships")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["channel", "user"], name="uniq_channel_member")
        ]

class DMConversation(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dm_user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="dm_user2")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user1", "user2"], name="uniq_dm_pair")
        ]

    @staticmethod
    def get_or_create_pair(a, b):
        if a.id == b.id:
            raise ValueError("DM with self not allowed")
        u1, u2 = (a, b) if a.id < b.id else (b, a)
        obj, _ = DMConversation.objects.get_or_create(user1=u1, user2=u2)
        return obj

    def participants(self):
        return [self.user1, self.user2]

class UserBan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bans")
    banned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="bans_made")
    reason = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        permissions = [
            ("can_ban_user", "Can ban/unban users"),
        ]

    def __str__(self):
        return f"Ban({self.user_id}, active={self.is_active})"

class Message(models.Model):
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, null=True, blank=True, related_name="messages")
    dm_conversation = models.ForeignKey(DMConversation, on_delete=models.CASCADE, null=True, blank=True, related_name="messages")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages")
    text = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="images/", blank=True, null=True)
    audio = models.FileField(upload_to="audio/", blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        permissions = [
            ("can_delete_any_message", "Can delete any message"),
        ]

    def clean(self):
        # at least one content
        if not (self.text or self.image or self.audio):
            raise ValueError("Message must contain text or an attachment")

    def scope(self):
        if self.channel_id:
            return f"channel:{self.channel_id}"
        if self.dm_conversation_id:
            return f"dm:{self.dm_conversation_id}"
        return "unknown"

    def __str__(self):
        if self.text:
            return f"{self.author}: {self.text[:30]}"
        return f"Message({self.id})"

class MessageReaction(models.Model):
    message = models.ForeignKey("Message", on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=16)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["message", "user", "emoji"], name="uniq_msg_user_emoji")
        ]

class UserReport(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made")
    reported = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_received")
    reason = models.CharField(max_length=300, default="")
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=32, default="new")

class VoiceChannel(models.Model):
    name = models.CharField(max_length=64, unique=True)
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_voice_channels")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"🔊 {self.name}"

class VoiceMembership(models.Model):
    voice_channel = models.ForeignKey(VoiceChannel, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voice_memberships")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["voice_channel", "user"], name="uniq_voice_member")
        ]