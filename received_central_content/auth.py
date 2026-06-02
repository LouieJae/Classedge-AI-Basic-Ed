from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def require_central_token(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        server_token = getattr(settings, "CENTRAL_INGEST_TOKEN", "") or ""
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not server_token:
            return JsonResponse({"error": "unauthorized"}, status=401)
        if not header.startswith("Bearer "):
            return JsonResponse({"error": "unauthorized"}, status=401)
        supplied = header[len("Bearer "):].strip()
        if supplied != server_token:
            return JsonResponse({"error": "unauthorized"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped
