from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import UserReport, UserBan

User = get_user_model()

@login_required
def report_user(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    if UserBan.objects.filter(user=request.user, is_active=True).exists():
        return HttpResponseForbidden("Banned")

    uid = int(request.POST.get("user_id", "0"))
    reason = (request.POST.get("reason") or "").strip()[:300]
    if not uid or not reason:
        return JsonResponse({"ok": False}, status=400)

    target = get_object_or_404(User, pk=uid)
    if target == request.user:
        return JsonResponse({"ok": False, "error": "self"}, status=400)

    UserReport.objects.create(reporter=request.user, reported=target, reason=reason)
    return JsonResponse({"ok": True})