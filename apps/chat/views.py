from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Channel, ChannelMembership, Message, DMConversation, UserBan
from .permissions import can_manage_channels, can_delete_any_message, can_ban_user
from django.db.models import Count
from .models import MessageReaction
from .models import VoiceChannel, VoiceMembership

User = get_user_model()

def _is_banned(user):
    return UserBan.objects.filter(user=user, is_active=True).exists()

@login_required
def home(request):
    if _is_banned(request.user):
        return render(request, "chat/banned.html")

    channel_id = request.GET.get("c")
    dm_id = request.GET.get("d")

    # sidebar data
    public_channels = Channel.objects.filter(is_public=True).order_by("name")
    my_channels = Channel.objects.filter(memberships__user=request.user).distinct().order_by("name")

    dms = DMConversation.objects.filter(Q(user1=request.user) | Q(user2=request.user)).order_by("-created_at")

    voice_channels = VoiceChannel.objects.filter(is_public=True).order_by("name")
    my_voice = VoiceChannel.objects.filter(memberships__user=request.user).distinct().order_by("name")
    active_voice_id = request.GET.get("v")
    active_voice = None
    if active_voice_id:
        active_voice = get_object_or_404(VoiceChannel, pk=active_voice_id)

    active_channel = None
    active_dm = None
    messages_qs = Message.objects.none()

    if dm_id:
        active_dm = get_object_or_404(DMConversation, pk=dm_id)
        if request.user not in active_dm.participants():
            return HttpResponseForbidden("Brak dostępu do DM")
        messages_qs = Message.objects.filter(dm_conversation=active_dm).select_related("author").order_by("created_at")
    else:
        if channel_id:
            active_channel = get_object_or_404(Channel, pk=channel_id)
        else:
            # default: first joined channel or first public
            active_channel = my_channels.first() or public_channels.first()

        if active_channel:
            # ensure membership for private channels
            if (not active_channel.is_public) and (not ChannelMembership.objects.filter(channel=active_channel, user=request.user).exists()):
                return HttpResponseForbidden("Brak dostępu do kanału")
            messages_qs = Message.objects.filter(channel=active_channel).select_related("author").order_by("created_at")

    q = request.GET.get("q", "").strip()
    search_users = []
    search_channels = []
    if q:
        search_users = User.objects.filter(username__icontains=q)[:10]
        search_channels = Channel.objects.filter(name__icontains=q)[:10]

    # --- reakcje: mapowanie message_id -> [(emoji, count), ...]
    msg_list = list(messages_qs[:200])
    msg_ids = [m.id for m in msg_list]

    reaction_map = {}
    if msg_ids:
        rows = (MessageReaction.objects
                .filter(message_id__in=msg_ids)
                .values("message_id", "emoji")
                .annotate(c=Count("id"))
                .order_by("emoji"))
        for r in rows:
            reaction_map.setdefault(r["message_id"], []).append((r["emoji"], r["c"]))

    return render(request, "chat/app.html", {
        "public_channels": public_channels,
        "my_channels": my_channels,
        "dms": dms,
        "active_channel": active_channel,
        "active_dm": active_dm,
        "voice_channels": voice_channels,
        "my_voice": my_voice,
        "active_voice": active_voice,
        "chat_messages": msg_list,  # last 200
        "reaction_map": reaction_map,
        "can_manage_channels": can_manage_channels(request.user),
        "can_delete_any_message": can_delete_any_message(request.user),
        "can_ban_user": can_ban_user(request.user),
        "q": q,
        "search_users": search_users,
        "search_channels": search_channels,
    })

@login_required
def create_channel(request):
    if not can_manage_channels(request.user):
        return HttpResponseForbidden("Brak uprawnień")
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip().lower().replace(" ", "-")
        is_public = request.POST.get("is_public") == "on"
        if not name:
            messages.error(request, "Nazwa kanału jest wymagana.")
            return redirect("chat:home")
        ch, created = Channel.objects.get_or_create(name=name, defaults={"is_public": is_public, "created_by": request.user})
        if not created:
            messages.info(request, "Kanał już istnieje.")
        ChannelMembership.objects.get_or_create(channel=ch, user=request.user)
        return redirect(f"/?c={ch.id}")
    return redirect("chat:home")

from django.contrib import messages

@login_required
def create_voice_channel(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)

    if not can_manage_channels(request.user):
        return HttpResponseForbidden("Brak uprawnień")

    name = (request.POST.get("name") or "").strip().lower().replace(" ", "-")
    is_public = request.POST.get("is_public") == "on"

    if not name:
        messages.error(request, "Podaj nazwę kanału głosowego.")
        return redirect("/")

    vc, created = VoiceChannel.objects.get_or_create(
        name=name,
        defaults={"is_public": is_public, "created_by": request.user}
    )
    if not created:
        messages.warning(request, "Kanał głosowy już istnieje.")

    return redirect(f"/?v={vc.id}")

@login_required
def join_channel(request, channel_id):
    if _is_banned(request.user):
        return render(request, "chat/banned.html")
    ch = get_object_or_404(Channel, pk=channel_id)
    if not ch.is_public and not can_manage_channels(request.user):
        return HttpResponseForbidden("Kanał prywatny")
    ChannelMembership.objects.get_or_create(channel=ch, user=request.user)
    return redirect(f"/?c={ch.id}")

@login_required
def start_dm(request, user_id):
    if _is_banned(request.user):
        return render(request, "chat/banned.html")
    other = get_object_or_404(User, pk=user_id)
    if other == request.user:
        messages.error(request, "Nie możesz rozpocząć DM z samym sobą.")
        return redirect("chat:home")
    dm = DMConversation.get_or_create_pair(request.user, other)
    return redirect(f"/?d={dm.id}")

@login_required
def ban_user(request, user_id):
    if not can_ban_user(request.user):
        return HttpResponseForbidden("Brak uprawnień")
    target = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()
        UserBan.objects.create(user=target, banned_by=request.user, reason=reason, is_active=True)
        messages.success(request, f"Użytkownik {target.username} zablokowany.")
    return redirect("chat:home")

@login_required
def unban_user(request, ban_id):
    if not can_ban_user(request.user):
        return HttpResponseForbidden("Brak uprawnień")
    ban = get_object_or_404(UserBan, pk=ban_id)
    ban.is_active = False
    ban.save(update_fields=["is_active"])
    messages.success(request, "Odblokowano użytkownika.")
    return redirect("chat:home")
