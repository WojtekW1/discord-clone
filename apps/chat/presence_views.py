from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache

ONLINE_KEY = "online_users_ids"

@login_required
def presence_snapshot(request):
    ids = cache.get(ONLINE_KEY, [])
    return JsonResponse({"ok": True, "online_user_ids": ids})