"""[Classedge LMS] IT Admin dashboard — operational view for users with the
"IT Admin" or "Admin" role (NOT Django superusers; superusers land on the
Super Admin dashboard). Focused on system health, security signals, and the
flow of accounts through the LMS.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.sessions.models import Session
from django.db.models import Count, F
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


STALE_INACTIVE_DAYS = 90
RECENT_ACTIVITY_DAYS = 7


def _is_it_admin(user):
    """[Classedge LMS] Allow users whose role name is "IT Admin" OR the legacy
    "Admin" role (case-insensitive), plus Django superusers as a safety net."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return (user.profile.role.name or "").lower() in ("it admin", "admin")
    except (AttributeError, Profile.DoesNotExist):
        return False


def _non_system_users():
    """[Classedge LMS] Frontend accounts only — hide is_superuser/is_staff."""
    return CustomUser.objects.filter(is_superuser=False, is_staff=False)


def _live_session_users(limit=8):
    """[Classedge LMS] Currently-signed-in users via non-expired Session rows."""
    now = timezone.now()
    user_ids = set()
    for session in Session.objects.filter(expire_date__gte=now).only("session_data"):
        try:
            data = session.get_decoded()
        except Exception:
            continue
        uid = data.get("_auth_user_id")
        if uid:
            try:
                user_ids.add(int(uid))
            except (TypeError, ValueError):
                pass
    return (
        _non_system_users()
        .filter(id__in=user_ids)
        .select_related("profile", "profile__role")
        .order_by("-last_login")[:limit]
    )


@login_required
@user_passes_test(_is_it_admin)
def it_admin_dashboard(request):
    """[Classedge LMS] IT Admin operational dashboard."""
    now = timezone.localtime()
    week_ago = now - timedelta(days=RECENT_ACTIVITY_DAYS)
    stale_cutoff = now - timedelta(days=STALE_INACTIVE_DAYS)

    base_users = _non_system_users()
    active_users = base_users.filter(is_active=True).count()
    inactive_users = base_users.filter(is_active=False).count()
    active_in_7d = base_users.filter(last_login__gte=week_ago).count()
    new_today = base_users.filter(date_joined__date=now.date()).count()
    locked_out = base_users.filter(failed_login_count__gte=3).count()
    no_role_count = base_users.filter(profile__role__isnull=True).count()
    stale_inactive_count = base_users.filter(
        is_active=True,
        last_login__isnull=False,
        last_login__lt=stale_cutoff,
    ).count()
    never_logged_in = base_users.filter(is_active=True, last_login__isnull=True).count()

    live_users = list(_live_session_users())
    online_count = len(live_users)

    # ── Users-by-role breakdown for the right panel ──────────────
    user_breakdown = list(
        Profile.objects
        .filter(
            user__is_active=True,
            user__is_superuser=False,
            user__is_staff=False,
            role__isnull=False,
        )
        .values(role_name=F("role__name"))
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    breakdown_total = sum(r["count"] for r in user_breakdown) or 1
    for r in user_breakdown:
        r["pct"] = round(r["count"] / breakdown_total * 100)

    # ── Recent signups + Latest sign-ins (feeds) ─────────────────
    recent_signups = list(
        base_users.select_related("profile", "profile__role")
        .order_by("-date_joined")[:6]
    )
    recent_logins = list(
        base_users.filter(last_login__isnull=False)
        .select_related("profile", "profile__role")
        .order_by("-last_login")[:6]
    )

    # ── "Needs your attention" highlight ─────────────────────────
    attention_items = []
    if locked_out:
        attention_items.append({
            "label": f"{locked_out} account{'s' if locked_out != 1 else ''} locked",
            "detail": "3+ failed logins — review and unlock.",
            "icon": "fa-lock",
        })
    if no_role_count:
        attention_items.append({
            "label": f"{no_role_count} account{'s' if no_role_count != 1 else ''} without a role",
            "detail": "They can sign in but see nothing — assign a role.",
            "icon": "fa-user-shield",
        })
    if stale_inactive_count:
        attention_items.append({
            "label": f"{stale_inactive_count} dormant account{'s' if stale_inactive_count != 1 else ''} ({STALE_INACTIVE_DAYS}d+)",
            "detail": "Haven't logged in in 3+ months — consider disabling.",
            "icon": "fa-hourglass-half",
        })
    if never_logged_in:
        attention_items.append({
            "label": f"{never_logged_in} account{'s' if never_logged_in != 1 else ''} never signed in",
            "detail": "Activated but unused — onboarding follow-up.",
            "icon": "fa-user-clock",
        })
    attention_status = "warn" if attention_items else "ok"

    kpis = [
        {"label": "Active accounts", "value": active_users, "icon": "fa-users",
         "hint": f"{inactive_users} disabled", "tone": ""},
        {"label": "Online now", "value": online_count, "icon": "fa-bolt",
         "hint": "active sessions", "tone": "ok" if online_count else ""},
        {"label": "Active in 7d", "value": active_in_7d, "icon": "fa-arrow-trend-up",
         "hint": "distinct sign-ins", "tone": ""},
        {"label": "Locked / Suspicious", "value": locked_out, "icon": "fa-lock",
         "hint": "review and unlock", "tone": "danger" if locked_out else "ok"},
    ]

    context = {
        "role_tag": "IT Admin",
        "time_of_day": time_of_day(),
        "as_of": now.strftime("%b %d · %I:%M %p"),
        "kpis": kpis,
        "live_users": live_users,
        "user_breakdown": user_breakdown,
        "breakdown_total": breakdown_total,
        "recent_signups": recent_signups,
        "recent_logins": recent_logins,
        "attention_items": attention_items,
        "attention_status": attention_status,
        "new_today": new_today,
    }
    return render(request, "operations/it_admin_dashboard.html", context)
