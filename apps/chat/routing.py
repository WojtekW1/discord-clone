from django.urls import re_path
from . import consumers
from . import consumers_notify
from . import consumers_voice

websocket_urlpatterns = [
    re_path(r"^ws/chat/channel/(?P<channel_id>\d+)/$", consumers.ChannelConsumer.as_asgi()),
    re_path(r"^ws/chat/dm/(?P<dm_id>\d+)/$", consumers.DMConsumer.as_asgi()),
    re_path(r"^ws/notify/$", consumers_notify.NotifyConsumer.as_asgi()),
    re_path(r"^ws/voice/(?P<voice_id>\d+)/$", consumers_voice.VoiceConsumer.as_asgi()),
]
