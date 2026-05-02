from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404

def media_serve(request, path: str):
    # Bezpieczne “wyjście” poza MEDIA_ROOT
    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)):
        raise Http404("Not found")

    if not target.exists() or not target.is_file():
        raise Http404("Not found")

    return FileResponse(open(target, "rb"))