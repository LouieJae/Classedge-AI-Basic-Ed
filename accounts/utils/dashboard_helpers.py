"""Small shared helpers for role-specific dashboard views.

These were previously copy-pasted across academic_director.py, program_head.py,
coil_admin.py, it_admin.py, super_admin.py, and registrar.py.
"""

from django.utils import timezone


def time_of_day():
    """Return 'morning' | 'afternoon' | 'evening' based on local time."""
    h = timezone.localtime().hour
    if h < 12:
        return "morning"
    if h < 18:
        return "afternoon"
    return "evening"


def user_role_name(user):
    """Return a human-friendly title-cased role label for the given user.

    Used by role-specific dashboards for the welcome chip / role tag. Returns
    an empty string when the user has no role, so call sites can fall back
    to a hard-coded default with `or "..."`.
    """
    raw = getattr(user, "role_name", "") or ""
    return raw.title()
