# In decorators.py

from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """[Classedge LMS] Phase 1: gate strictly on is_superuser.

    Role-name match removed; IT Admin role implies is_superuser via the
    accounts.signals.sync_it_admin_superuser post_save signal.

    Kept as a decorator (not @permission_required) because IT Admin is the
    sole superuser-bypass role; expressing it as a permission would falsely
    imply the gate is delegable to other roles. Used by roles/views.py for
    role-CRUD endpoints.
    """
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped_view_func
