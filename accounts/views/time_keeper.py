"""[Classedge LMS] Time Keeper Operations dashboard.

The school's Time Keeper tracks teacher class sessions — who started which
class when, who's actively teaching right now, total hours, and which
scheduled sessions never got recorded. This dashboard is scoped to that
job: live teacher activity, today's roster, weekly hours, and on-time rate.
Holidays/term context stay as a small sidebar since they still shape the
academic calendar the Time Keeper manages.
"""
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum, Count, ExpressionWrapper, DurationField, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day, user_role_name as _user_role_name
from calendars.models import Holiday
from classroom.models import Teacher_Attendance
from course.models.semester_model import Semester
from subject.models.schedule_model import Schedule


def _is_time_keeper(user):
    return user.is_authenticated and user.role_name == "time keeper"


# ── Helpers ────────────────────────────────────────────────────────────

def _fmt_duration(td):
    """Return '2h 15m' / '45m' from a timedelta-or-seconds value."""
    if td is None:
        return "—"
    secs = td.total_seconds() if hasattr(td, "total_seconds") else float(td)
    if secs < 60:
        return f"{int(secs)}s"
    hours, rem = divmod(int(secs), 3600)
    minutes = rem // 60
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def _week_bounds(today):
    """ISO week — Monday start, Sunday end."""
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def _term_progress(semester, today):
    if not semester:
        return None
    total = max(1, (semester.end_date - semester.start_date).days)
    elapsed = max(0, min(total, (today - semester.start_date).days))
    pct = round(elapsed / total * 100)
    return {
        "name": semester.semester_name,
        "academic_year": semester.get_academic_year(),
        "start": semester.start_date,
        "end": semester.end_date,
        "pct": pct,
        "elapsed_days": elapsed,
        "total_days": total,
        "days_left": max(0, (semester.end_date - today).days),
    }


def _expected_sessions_today(today):
    """How many scheduled sessions should run today (per active semester)."""
    abbr = today.strftime("%a")
    qs = Schedule.objects.filter(is_active_semester=True, days_of_week__contains=abbr)
    return qs.count()


# ── Main view ──────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_time_keeper)
def time_keeper_dashboard(request):
    now = timezone.localtime()
    today = now.date()
    week_start, week_end = _week_bounds(today)

    # ── Today's teacher sessions ──────────────────────────────────────
    today_qs = (
        Teacher_Attendance.objects
        .filter(time_started__date=today)
        .select_related("teacher", "subject")
        .order_by("-time_started")
    )
    sessions_today = today_qs.count()
    sessions_active_now = today_qs.filter(is_active=True, time_ended__isnull=True).count()
    sessions_completed_today = today_qs.filter(time_ended__isnull=False).count()
    expected_today = _expected_sessions_today(today)
    missed_today = max(0, expected_today - sessions_today)
    coverage_pct = (
        round((sessions_today / expected_today) * 100) if expected_today else (100 if sessions_today else 0)
    )

    # ── This week's hours ─────────────────────────────────────────────
    week_qs = (
        Teacher_Attendance.objects
        .filter(time_started__date__gte=week_start, time_started__date__lte=week_end, time_ended__isnull=False)
        .annotate(dur=ExpressionWrapper(F("time_ended") - F("time_started"), output_field=DurationField()))
    )
    total_week_seconds = sum(
        ((row.time_ended - row.time_started).total_seconds() for row in week_qs),
        0.0,
    )
    week_hours = round(total_week_seconds / 3600, 1) if total_week_seconds else 0
    unique_teachers_week = week_qs.values("teacher_id").distinct().count()

    # ── Active now: who's currently in a class ────────────────────────
    active_rows = []
    for s in today_qs.filter(is_active=True, time_ended__isnull=True)[:6]:
        started = timezone.localtime(s.time_started)
        active_rows.append({
            "id": s.id,
            "teacher_name": (s.teacher.get_full_name() if s.teacher else "—") or (s.teacher.username if s.teacher else "—"),
            "subject": s.subject.subject_name if s.subject else "—",
            "started_at": started.strftime("%I:%M %p"),
            "duration": _fmt_duration(now - started),
        })

    # ── Today's roster (most recent sessions, completed or active) ────
    roster_rows = []
    for s in today_qs[:8]:
        started = timezone.localtime(s.time_started) if s.time_started else None
        ended = timezone.localtime(s.time_ended) if s.time_ended else None
        teacher_name = (s.teacher.get_full_name() if s.teacher else "—") or (s.teacher.username if s.teacher else "—")
        if ended:
            duration = _fmt_duration(s.time_ended - s.time_started)
            status, status_tone = "Done", "ok"
        elif s.is_active:
            duration = _fmt_duration(now - started) if started else "—"
            status, status_tone = "Live", "live"
        else:
            duration = _fmt_duration((s.time_ended or now) - s.time_started) if s.time_started else "—"
            status, status_tone = "Open", "warn"
        roster_rows.append({
            "id": s.id,
            "teacher": teacher_name,
            "subject": s.subject.subject_name if s.subject else "—",
            "subject_id": s.subject.id if s.subject else None,
            "started": started.strftime("%I:%M %p") if started else "—",
            "ended": ended.strftime("%I:%M %p") if ended else None,
            "duration": duration,
            "status": status,
            "status_tone": status_tone,
        })

    # ── Top teaching hours this week ──────────────────────────────────
    teacher_hours_agg = {}
    for s in week_qs:
        secs = (s.time_ended - s.time_started).total_seconds()
        if not s.teacher_id:
            continue
        teacher_hours_agg.setdefault(s.teacher_id, {"name": None, "seconds": 0.0, "sessions": 0})
        teacher_hours_agg[s.teacher_id]["seconds"] += secs
        teacher_hours_agg[s.teacher_id]["sessions"] += 1
        if teacher_hours_agg[s.teacher_id]["name"] is None and s.teacher:
            teacher_hours_agg[s.teacher_id]["name"] = (
                s.teacher.get_full_name() or s.teacher.username or "—"
            )
    top_teachers = sorted(
        teacher_hours_agg.values(),
        key=lambda x: x["seconds"],
        reverse=True,
    )[:5]
    top_teachers_rows = []
    top_seconds = top_teachers[0]["seconds"] if top_teachers else 0
    for t in top_teachers:
        hrs = t["seconds"] / 3600
        top_teachers_rows.append({
            "name": t["name"] or "—",
            "sessions": t["sessions"],
            "hours_display": f"{hrs:.1f}h",
            "bar_pct": round((t["seconds"] / top_seconds) * 100) if top_seconds else 0,
        })

    # ── Holidays (small sidebar) ──────────────────────────────────────
    upcoming_holiday_qs = Holiday.objects.filter(date__gte=today).order_by("date")[:4]
    holiday_rows = []
    for h in upcoming_holiday_qs:
        days = (h.date - today).days
        holiday_rows.append({
            "title": h.title,
            "date": h.date,
            "holiday_type": h.holiday_type,
            "days_from_now": days,
            "label": "Today" if days == 0 else ("Tomorrow" if days == 1 else f"in {days} days"),
        })
    next_holiday = holiday_rows[0] if holiday_rows else None

    # ── KPIs ──────────────────────────────────────────────────────────
    kpis = [
        {
            "label": "Sessions today",
            "value": sessions_today,
            "icon": "fa-chalkboard-user",
            "sub": (f"of {expected_today} scheduled" if expected_today else "no schedule today"),
            "tone": "",
        },
        {
            "label": "Active now",
            "value": sessions_active_now,
            "icon": "fa-circle-dot",
            "sub": "teachers currently in class",
            "tone": "live" if sessions_active_now else "",
        },
        {
            "label": "Hours this week",
            "value": f"{week_hours}",
            "icon": "fa-clock",
            "sub": f"{unique_teachers_week} teacher{'s' if unique_teachers_week != 1 else ''} clocked in",
            "tone": "",
        },
        {
            "label": "Coverage today",
            "value": f"{coverage_pct}%",
            "icon": "fa-bullseye",
            "sub": (f"{missed_today} session{'s' if missed_today != 1 else ''} not started yet"
                    if expected_today else "no schedule to compare"),
            "tone": "warn" if expected_today and missed_today else ("ok" if expected_today else ""),
        },
    ]

    # ── "Needs your attention" items ──────────────────────────────────
    attention_items = []
    if sessions_active_now == 0 and expected_today:
        attention_items.append({
            "label": "No teachers currently in class",
            "detail": f"{expected_today} session{'s' if expected_today != 1 else ''} scheduled today — verify start times.",
            "icon": "fa-bell",
        })
    if expected_today and missed_today >= max(1, expected_today // 4):
        attention_items.append({
            "label": f"{missed_today} scheduled session{'s' if missed_today != 1 else ''} not yet recorded",
            "detail": "Check teachers haven't forgotten to start class mode.",
            "icon": "fa-triangle-exclamation",
        })
    # Stuck active sessions — running for > 3h with no end time.
    stale_cutoff = now - timedelta(hours=3)
    stuck = today_qs.filter(is_active=True, time_ended__isnull=True, time_started__lte=stale_cutoff).count()
    if stuck:
        attention_items.append({
            "label": f"{stuck} session{'s' if stuck != 1 else ''} running past 3 hours",
            "detail": "Likely the teacher forgot to end the class.",
            "icon": "fa-hourglass-half",
        })

    term_progress = _term_progress(Semester.current(), today)

    quick_actions = [
        {"url": "teacher_timesheet_report", "label": "Timesheet report",    "icon": "fa-file-invoice", "primary": True},
        {"url": "schedule",                  "label": "Schedules",           "icon": "fa-clock"},
        {"url": "calendars",                 "label": "Calendar",            "icon": "fa-calendar-days"},
    ]

    context = {
        "role_tag": _user_role_name(request.user) or "Time Keeper",
        "time_of_day": time_of_day(),
        "as_of": now.strftime("%b %d · %I:%M %p"),
        "today": today,
        "week_start": week_start,
        "week_end": week_end,
        "kpis": kpis,
        "term_progress": term_progress,
        "active_rows": active_rows,
        "roster_rows": roster_rows,
        "top_teachers_rows": top_teachers_rows,
        "holiday_rows": holiday_rows,
        "next_holiday": next_holiday,
        "attention_items": attention_items,
        "attention_status": "warn" if attention_items else "ok",
        "quick_actions": quick_actions,
        "sessions_completed_today": sessions_completed_today,
    }
    return render(request, "operations/time_keeper_dashboard.html", context)
