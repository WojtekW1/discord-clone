from django.urls import path
from . import views
from .upload_views import upload_message
from .reactions_views import toggle_reaction
from .report_views import report_user
from .presence_views import presence_snapshot
from .voice_views import join_voice, leave_voice

app_name = "chat"

urlpatterns = [
    path("", views.home, name="home"),
    path("presence/", presence_snapshot, name="presence_snapshot"),
    path("channels/create/", views.create_channel, name="create_channel"),
    path("channels/<int:channel_id>/join/", views.join_channel, name="join_channel"),
    path("dm/start/<int:user_id>/", views.start_dm, name="start_dm"),
    path("moderation/ban/<int:user_id>/", views.ban_user, name="ban_user"),
    path("moderation/unban/<int:ban_id>/", views.unban_user, name="unban_user"),
    path("upload/", upload_message, name="upload_message"),
    path("reactions/toggle/", toggle_reaction, name="toggle_reaction"),
    path("moderation/report/", report_user, name="report_user"),
    path("voice/<int:voice_id>/join/", join_voice, name="join_voice"),
    path("voice/<int:voice_id>/leave/", leave_voice, name="leave_voice"),
    path("voice/create/", views.create_voice_channel, name="create_voice_channel"),
]
