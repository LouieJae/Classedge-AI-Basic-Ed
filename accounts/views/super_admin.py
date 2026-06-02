"""[Classedge LMS] Super Admin (Django superuser) dashboard — system control
panel. Shows things only a superuser cares about: superuser roster, login
sessions to revoke, role audit, dangerous-action shortcuts, link to
/admin/.
"""
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day

from accounts.models.account_models import CustomUser, Profile
from accounts.models.department_models import Department
from roles.models import Role


def _is_super_admin(user):
    return user.is_authenticated and user.is_superuser




def _kpi(label, value, *, tone="", url=None, hint=""):
    return {"label": label, "value": value, "tone": tone, "url": url, "hint": hint}


def _live_session_users(limit=12):
    """[Classedge LMS] Currently-online users derived from the WebSocket presence
    cache populated by social_media.consumers (`user_online_<id>` keys + the
    `online_user_ids` set). Each per-user key has a 5-minute TTL, so the set is
    re-validated here to drop stale ids."""
    candidate_ids = set()
    for uid in cache.get('online_user_ids') or []:
        try:
            candidate_ids.add(int(uid))
        except (TypeError, ValueError):
            continue

    if not candidate_ids:
        return CustomUser.objects.none()

    keys = [f'user_online_{uid}' for uid in candidate_ids]
    alive = cache.get_many(keys)
    live_ids = {int(k.rsplit('_', 1)[1]) for k in alive.keys()}

    # Prune stale ids from the set so the count stays honest.
    stale = candidate_ids - live_ids
    if stale:
        remaining = list(live_ids)
        cache.set('online_user_ids', remaining, timeout=None)

    return (
        CustomUser.objects
        .filter(id__in=live_ids)
        .select_related("profile", "profile__role")
        .order_by("-last_login")[:limit]
    )


def _recent_role_changes(limit=8):
    """[Classedge LMS] Latest role assignments based on Profile.update_at if set,
    else falls back to the user's date_joined. Real audit log is a separate
    follow-up; this is a best-effort feed."""
    return (
        Profile.objects
        .filter(role__isnull=False)
        .select_related("user", "role")
        .order_by("-id")[:limit]
    )


def _failed_login_count_24h():
    cutoff = timezone.now() - timedelta(hours=24)
    return CustomUser.objects.filter(
        failed_login_count__gt=0,
        last_login__lt=cutoff,
    ).count()


def _superuser_roster():
    return CustomUser.objects.filter(is_superuser=True).order_by("username")


@login_required
@user_passes_test(_is_super_admin)
def super_admin_dashboard(request):
    """[Classedge LMS] Render the Super Admin control-panel dashboard."""
    now = timezone.localtime()
    seven_days_ago = now - timedelta(days=7)

    live_users = list(_live_session_users())
    superuser_count = CustomUser.objects.filter(is_superuser=True).count()
    user_count = CustomUser.objects.count()
    inactive_count = CustomUser.objects.filter(is_active=False).count()
    locked_out = CustomUser.objects.filter(failed_login_count__gte=3).count()
    new_signups_7d = CustomUser.objects.filter(date_joined__gte=seven_days_ago).count()
    failed_logins_24h = _failed_login_count_24h()

    # ── Users by role (compact breakdown bar) ─────────────────
    role_breakdown = list(
        Profile.objects
        .filter(role__isnull=False)
        .values("role__name")
        .annotate(c=Count("id"))
        .order_by("-c")
    )
    role_breakdown_total = sum(r["c"] for r in role_breakdown) or 1
    for r in role_breakdown:
        r["pct"] = round(r["c"] * 100 / role_breakdown_total, 1)
    no_role_count = max(0, user_count - role_breakdown_total)

    # ── Security health status (drives the highlight card) ────
    issues = []
    if locked_out:
        issues.append({
            "label": f"{locked_out} account{'s' if locked_out != 1 else ''} locked",
            "detail": "3+ failed logins — review or unlock.",
            "url": reverse("admin-and-staff-list"),
        })
    if failed_logins_24h:
        issues.append({
            "label": f"{failed_logins_24h} failed-login user{'s' if failed_logins_24h != 1 else ''} (24h)",
            "detail": "Investigate suspicious activity.",
            "url": reverse("teacher-login-report"),
        })
    if superuser_count > 5:
        issues.append({
            "label": f"{superuser_count} active superusers",
            "detail": "Consider reducing — fewer keys is safer.",
            "url": reverse("admin-and-staff-list"),
        })
    if inactive_count and inactive_count >= max(5, user_count // 10):
        issues.append({
            "label": f"{inactive_count} disabled accounts",
            "detail": "Review whether they should be removed.",
            "url": reverse("admin-and-staff-list"),
        })
    health_status = "warn" if issues else "ok"

    # ── Audit log summary + 7×24 heatmap ──────────────────────
    from easyaudit.models import LoginEvent, CRUDEvent, RequestEvent
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    audit_summary = {
        "logins_today": LoginEvent.objects.filter(datetime__gte=today_start).count(),
        "logins_7d": LoginEvent.objects.filter(datetime__gte=week_start).count(),
        "crud_today": CRUDEvent.objects.filter(datetime__gte=today_start).count(),
        "crud_7d": CRUDEvent.objects.filter(datetime__gte=week_start).count(),
        "nav_today": RequestEvent.objects.filter(datetime__gte=today_start, method="GET").count(),
        "nav_7d": RequestEvent.objects.filter(datetime__gte=week_start, method="GET").count(),
        "failed_logins_7d": LoginEvent.objects.filter(login_type=2, datetime__gte=week_start).count(),
    }

    grid = [[0] * 24 for _ in range(7)]
    day_labels = [(week_start + timedelta(days=i)).date().strftime("%a") for i in range(7)]

    def _bucket(qs):
        for dt in qs.values_list("datetime", flat=True):
            local = timezone.localtime(dt)
            day_idx = (local.date() - week_start.date()).days
            if 0 <= day_idx < 7:
                grid[day_idx][local.hour] += 1

    _bucket(LoginEvent.objects.filter(datetime__gte=week_start))
    _bucket(CRUDEvent.objects.filter(datetime__gte=week_start))
    _bucket(RequestEvent.objects.filter(datetime__gte=week_start, method="GET"))

    max_cell = max((max(row) for row in grid), default=0)
    heatmap_rows = []
    for label, row in zip(day_labels, grid):
        cells = [
            {"hour": h, "value": v, "intensity": round((v / max_cell) if max_cell else 0, 3)}
            for h, v in enumerate(row)
        ]
        heatmap_rows.append({"label": label, "cells": cells})

    audit_heatmap = {
        "rows": heatmap_rows,
        "hours": list(range(24)),
        "max": max_cell,
        "total": sum(sum(r) for r in grid),
    }

    context = {
        "role_tag": "Super Admin",
        "time_of_day": time_of_day(),
        "as_of": now.strftime("%I:%M %p"),
        "audit_summary": audit_summary,
        "audit_heatmap": audit_heatmap,
        "kpis": [
            _kpi("Currently Online", len(live_users), tone="ok", hint="live WebSocket presence"),
            _kpi("Total Accounts", user_count, hint=f"{inactive_count} disabled"),
            _kpi("Locked / Suspicious", locked_out, tone="danger" if locked_out else "ok"),
            _kpi("New (7d)", new_signups_7d, hint="signups last week"),
        ],
        "danger_actions": [
            {"url": reverse("role_list"), "label": "Roles & Permissions", "icon": "fa-user-shield", "tone": "primary"},
            {"url": reverse("admin-and-staff-list"), "label": "Manage Accounts", "icon": "fa-user-tie"},
            {"url": reverse("department_list"), "label": "Departments", "icon": "fa-building"},
            {"url": reverse("teacher-login-report"), "label": "Login Audit", "icon": "fa-clock-rotate-left"},
            {"url": reverse("user_audit_log"), "label": "User Audit Log", "icon": "fa-clipboard-list"},
        ],
        "live_users": live_users,
        "role_breakdown": role_breakdown,
        "role_breakdown_total": role_breakdown_total,
        "no_role_count": no_role_count,
        "health_status": health_status,
        "health_issues": issues,
        "failed_logins_24h": failed_logins_24h,
        "locked_out": locked_out,
        "superuser_count": superuser_count,
    }
    return render(request, "operations/super_admin_dashboard.html", context)


@login_required
@user_passes_test(_is_super_admin)
def user_audit_log(request):
    """[Classedge LMS] Browse user audit events captured by django-easy-audit.

    Combines LoginEvent (login/logout/failed) and CRUDEvent (model changes) into
    a single paginated feed, with filters for event type, actor, and search.
    """
    from django.core.paginator import Paginator
    from easyaudit.models import LoginEvent, CRUDEvent, RequestEvent
    import re

    event_type = (request.GET.get("type") or "all").lower()
    actor = (request.GET.get("user") or "").strip()
    search = (request.GET.get("q") or "").strip()
    action_filter = (request.GET.get("action") or "").strip().lower()

    # URL → human label mapping for RequestEvent rows.
    # Order matters: the first regex that matches wins.
    # Activities/assessments/quizzes are the same surface in this app, and
    # lessons live under the materials section — so we collapse those into a
    # single label each instead of inventing duplicate categories.
    NAV_PATTERNS = [
        (r"^/course/[\w-]+/?$",                                 "Opened course"),
        (r"^/subject/[\w-]+/?$",                                "Opened course"),
        (r"^/material/list/\d+",                                "Browsed materials"),
        (r"^/material/[\w-]+/?\d*/?$",                          "Viewed material"),
        (r"^/lesson/[\w-]+/?\d*/?$",                            "Viewed material"),
        (r"^/(activity|assessment[s]?|quiz)/[\w-]+/?\d*/?$",    "Opened assessment"),
        (r"^/gradebook",                                        "Viewed gradebook"),
        (r"^/grade-finalization",                               "Viewed grade finalization"),
        (r"^/rubric",                                           "Viewed rubric"),
        (r"^/announcement",                                     "Viewed announcement"),
        (r"^/profile",                                          "Viewed profile"),
        (r"^/dashboard",                                        "Viewed dashboard"),
        (r"^/teacher/",                                         "Teacher area"),
        (r"^/student/",                                         "Student area"),
        (r"^/operations/",                                      "Operations area"),
    ]
    NAV_PATTERNS = [(re.compile(p), label) for p, label in NAV_PATTERNS]

    def _label_for_url(url):
        for rgx, label in NAV_PATTERNS:
            if rgx.match(url):
                return label
        return None  # not navigational → skip

    rows = []

    LOGIN_ACTION_MAP = {"login": 0, "logout": 1, "failed_login": 2}
    CRUD_ACTION_MAP = {"create": 1, "update": 2, "delete": 3}

    include_login = event_type in ("all", "login")
    include_crud = event_type in ("all", "crud")
    include_nav = event_type in ("all", "nav")

    if action_filter:
        # When a specific action is chosen, restrict to the matching event family.
        if action_filter in LOGIN_ACTION_MAP:
            include_crud = include_nav = False
        elif action_filter in CRUD_ACTION_MAP:
            include_login = include_nav = False
        else:
            # Anything else is treated as a navigation label substring.
            include_login = include_crud = False

    if include_login:
        login_qs = LoginEvent.objects.select_related("user").order_by("-datetime")
        if actor:
            login_qs = login_qs.filter(username__icontains=actor)
        if search:
            login_qs = login_qs.filter(remote_ip__icontains=search)
        if action_filter in LOGIN_ACTION_MAP:
            login_qs = login_qs.filter(login_type=LOGIN_ACTION_MAP[action_filter])
        for ev in login_qs[:500]:
            label = dict(LoginEvent.TYPES).get(ev.login_type, "Event")
            rows.append({
                "kind": "login",
                "label": label,
                "user": ev.user_id and (getattr(ev.user, "username", None) or ev.username) or ev.username,
                "detail": f"IP {ev.remote_ip or '—'}",
                "when": ev.datetime,
                "object": "—",
                "action": label,
            })

    if include_crud:
        crud_qs = CRUDEvent.objects.select_related("user").order_by("-datetime")
        if actor:
            crud_qs = crud_qs.filter(user_pk_as_string__icontains=actor) | crud_qs.filter(user__username__icontains=actor)
        if search:
            crud_qs = crud_qs.filter(object_repr__icontains=search) | crud_qs.filter(content_type__model__icontains=search)
        if action_filter in CRUD_ACTION_MAP:
            crud_qs = crud_qs.filter(event_type=CRUD_ACTION_MAP[action_filter])
        for ev in crud_qs[:500]:
            label = dict(CRUDEvent.TYPES).get(ev.event_type, "Change")
            rows.append({
                "kind": "crud",
                "label": label,
                "user": getattr(ev.user, "username", None) or ev.user_pk_as_string or "—",
                "detail": f"{ev.content_type.app_label}.{ev.content_type.model}" if ev.content_type_id else "—",
                "when": ev.datetime,
                "object": ev.object_repr or f"#{ev.object_id}",
                "action": label,
            })

    if include_nav:
        nav_qs = RequestEvent.objects.select_related("user").filter(method="GET").order_by("-datetime")
        if actor:
            nav_qs = nav_qs.filter(user__username__icontains=actor)
        if search:
            nav_qs = nav_qs.filter(url__icontains=search)

        nav_label_filter = None
        if action_filter and action_filter not in LOGIN_ACTION_MAP and action_filter not in CRUD_ACTION_MAP:
            nav_label_filter = action_filter

        for ev in nav_qs[:1500]:
            label = _label_for_url(ev.url or "")
            if not label:
                continue
            if nav_label_filter and nav_label_filter not in label.lower():
                continue
            rows.append({
                "kind": "nav",
                "label": label,
                "user": getattr(ev.user, "username", None) or "—",
                "detail": f"IP {ev.remote_ip or '—'}",
                "when": ev.datetime,
                "object": ev.url,
                "action": label,
            })

    rows.sort(key=lambda r: r["when"] or timezone.now(), reverse=True)

    try:
        per_page = int(request.GET.get("per_page") or 10)
    except (TypeError, ValueError):
        per_page = 10
    per_page = max(5, min(per_page, 100))

    paginator = Paginator(rows, per_page)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "role_tag": "Super Admin",
        "events": page.object_list,
        "page_obj": page,
        "paginator": paginator,
        "event_type": event_type,
        "actor": actor,
        "search": search,
        "action_filter": action_filter,
        "per_page": per_page,
        "total_login": LoginEvent.objects.count(),
        "total_crud": CRUDEvent.objects.count(),
        "total_nav": RequestEvent.objects.filter(method="GET").count(),
    }
    return render(request, "operations/user_audit_log.html", context)
