from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseForbidden
from .models import VoiceChannel, VoiceMembership, UserBan

def _is_banned(user):
    return UserBan.objects.filter(user=user, is_active=True).exists()

@login_required
def join_voice(request, voice_id: int):
    if _is_banned(request.user):
        return HttpResponseForbidden("Banned")
    vc = get_object_or_404(VoiceChannel, pk=voice_id)
    if not vc.is_public:
        return HttpResponseForbidden("Private voice not supported in UI")
    VoiceMembership.objects.get_or_create(voice_channel=vc, user=request.user)
    return redirect(f"/?v={vc.id}")

@login_required
def leave_voice(request, voice_id: int):
    vc = get_object_or_404(VoiceChannel, pk=voice_id)
    VoiceMembership.objects.filter(voice_channel=vc, user=request.user).delete()
    return redirect("/")