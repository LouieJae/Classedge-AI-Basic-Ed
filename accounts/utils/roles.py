"""Shared helpers for resolving a user's role.

Prefer the boolean properties on the user model (``user.is_student``,
``user.is_teacher``, ``user.is_admin``, ``user.is_program_head``,
``user.is_dean``, ``user.is_time_keeper``, ``user.is_parent``) for simple
branches. The helpers here exist for the few spots that need the raw role
slug — e.g. when picking a template based on role or returning a value
through a template context.
"""

from django.contrib.auth.models import AnonymousUser


ADMIN_LIKE_ROLES = frozenset({'admin', 'program head', 'dean'})


def get_role_name(user):
    """Return the lowercased role name for ``user`` or '' if none."""
    if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
        return ''
    return getattr(user, 'role_name', '') or ''


def viewer_role(request):
    """Convenience wrapper for ``get_role_name(request.user)``."""
    return get_role_name(getattr(request, 'user', None))


def is_admin_like(user):
    """True for admin / program head / dean — the common admin gating bucket."""
    return get_role_name(user) in ADMIN_LIKE_ROLES
