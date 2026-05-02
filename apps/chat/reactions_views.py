from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.db.models import Count
from .models import Message, MessageReaction, UserBan
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@login_required
def toggle_reaction(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    if UserBan.objects.filter(user=request.user, is_active=True).exists():
        return HttpResponseForbidden("Banned")

    mid = int(request.POST.get("message_id", "0"))
    emoji = (request.POST.get("emoji") or "").strip()

    if not mid or not emoji:
        return JsonResponse({"ok": False}, status=400)

    msg = get_object_or_404(Message, pk=mid)

    obj = MessageReaction.objects.filter(message=msg, user=request.user, emoji=emoji)
    if obj.exists():
        obj.delete()
        action = "removed"
    else:
        MessageReaction.objects.create(message=msg, user=request.user, emoji=emoji)
        action = "added"

    # zwróć aktualne liczniki reakcji
    counts_qs = (MessageReaction.objects
          .filter(message=msg)
          .values("emoji")
          .annotate(c=Count("id"))
          .order_by("emoji"))
    counts_list = list(counts_qs)
    
    # broadcast do innych przez WS
    channel_layer = get_channel_layer()
    
    scope = None
    group = None
    
    if msg.channel_id:
        group = f"channel_{msg.channel_id}"
        scope = f"channel:{msg.channel_id}"
    elif msg.dm_conversation_id:
        group = f"dm_{msg.dm_conversation_id}"
        scope = f"dm:{msg.dm_conversation_id}"
    
    if group:
        async_to_sync(channel_layer.group_send)(group, {
            "type": "send_event",
            "payload": {
                "type": "reaction.update",
                "message_id": msg.id,
                "counts": counts_list,
                "scope": scope
            }
        })
    
    return JsonResponse({"ok": True, "action": action, "counts": counts_list, "message_id": msg.id})