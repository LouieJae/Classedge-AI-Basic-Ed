# central_content/permissions.py
from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from central_content.models import CentralStaff


def central_role_required(*allowed_roles):
    """Decorator restricting a view to CentralStaff users with one of the
    given roles. Anonymous users are redirected to /login. CentralStaff
    with a non-matching role get 403.
    """
    allowed = set(allowed_roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if not user or not isinstance(user, CentralStaff):
                return redirect("/login")
            if user.role not in allowed:
                return HttpResponseForbidden("Forbidden")
            return view_func(request, *args, **kwargs)
        return _wrapped

    return decorator


class IsCentralStaff:
    """DRF permission class. Allows any request whose user is a CentralStaff
    instance. Role-specific gating is layered on via central_role_required
    on top-level views, or via DRF per-action logic.
    """

    def has_permission(self, request, view):
        return isinstance(getattr(request, "user", None), CentralStaff)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
