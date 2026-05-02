from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Channel, ChannelMembership, DMConversation, Message, UserBan
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

def _is_banned(user):
    return UserBan.objects.filter(user=user, is_active=True).exists()

@login_required
def upload_message(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    if _is_banned(request.user):
        return HttpResponseForbidden("Banned")

    scope = (request.POST.get("scope") or "").strip()
    text = (request.POST.get("text") or "").strip()

    image = request.FILES.get("image")
    audio = request.FILES.get("audio")

    if not (text or image or audio):
        return JsonResponse({"ok": False, "error": "Empty message"}, status=400)

    if scope.startswith("channel:"):
        channel_id = int(scope.split(":")[1])
        ch = get_object_or_404(Channel, pk=channel_id)

        if (not ch.is_public) and (not ChannelMembership.objects.filter(channel=ch, user=request.user).exists()):
            return HttpResponseForbidden("No access")

        msg = Message.objects.create(channel=ch, author=request.user, text=text, image=image, audio=audio)
        channel_layer = get_channel_layer()

        # 1) realtime message.new do kanału
        async_to_sync(channel_layer.group_send)(f"channel_{ch.id}", {
            "type": "send_event",
            "payload": {"type": "message.new", **serialize_msg(msg)}
        })

        # 2) notify badge do członków kanału
        member_ids = list(ChannelMembership.objects.filter(channel_id=ch.id).values_list("user_id", flat=True))
        for uid in member_ids:
            if uid == request.user.id:
                continue
            async_to_sync(channel_layer.group_send)(f"notify_{uid}", {
                "type": "send_event",
                "payload": {"type": "notify.message", "scope": f"channel:{ch.id}"}
            })

        return JsonResponse({"ok": True, "redirect": f"/?c={ch.id}"})

    if scope.startswith("dm:"):
        dm_id = int(scope.split(":")[1])
        dm = get_object_or_404(DMConversation, pk=dm_id)

        # stabilny check dostępu
        if request.user.id not in (dm.user1_id, dm.user2_id):
            return HttpResponseForbidden("No access")

        msg = Message.objects.create(dm_conversation=dm, author=request.user, text=text, image=image, audio=audio)
        channel_layer = get_channel_layer()

        # 1) realtime message.new do DM
        async_to_sync(channel_layer.group_send)(f"dm_{dm.id}", {
            "type": "send_event",
            "payload": {"type": "message.new", **serialize_msg(msg)}
        })

        # 2) notify badge do drugiego uczestnika
        for uid in (dm.user1_id, dm.user2_id):
            if uid == request.user.id:
                continue
            async_to_sync(channel_layer.group_send)(f"notify_{uid}", {
                "type": "send_event",
                "payload": {"type": "notify.message", "scope": f"dm:{dm.id}"}
            })

        return JsonResponse({"ok": True, "redirect": f"/?d={dm.id}"})

    return JsonResponse({"ok": False, "error": "Bad scope"}, status=400)

def serialize_msg(msg):
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
