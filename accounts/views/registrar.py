"""[Classedge LMS] Registrar Operations Mode dashboard view."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, F
from django.shortcuts import render
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject


NEAR_CAPACITY_THRESHOLD = 90  # %
RECENT_DAYS = 7


def _is_registrar(user):
    """[Classedge LMS] True iff the authenticated user owns the Registrar role."""
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Registrar"
    )


@login_required
@user_passes_test(_is_registrar)
def registrar_dashboard(request):
    """[Classedge LMS] Render the Registrar dashboard.

    Surfaces real enrollment data only — no placeholder columns. The
    Registrar's job-to-be-done from this page is: catch capacity
    problems, watch the term clock, and see which records moved
    yesterday/today.
    """
    now = timezone.localtime()
    today = now.date()
    week_ago = today - timedelta(days=RECENT_DAYS)

    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()

    enrolls = SubjectEnrollment.objects.all()
    if semester:
        enrolls = enrolls.filter(semester=semester)

    enrolled_count = enrolls.filter(status="enrolled").values("student_id").distinct().count()
    dropped_count = enrolls.filter(status__in=["dropped", "administrative_drop"]).values("student_id").distinct().count()
    completed_count = enrolls.filter(status="completed").values("student_id").distinct().count()
    todays_tx = enrolls.filter(enrollment_date=today).values("student_id").distinct().count()
    week_tx = enrolls.filter(enrollment_date__gte=week_ago).values("student_id").distinct().count()
    week_dropped = enrolls.filter(drop_date__gte=week_ago).values("student_id").distinct().count()

    # ── Subject capacity (real data, no hardcoded program codes) ──
    # Compute enrollee counts live from SubjectEnrollment (current semester
    # when one is active) instead of the denormalized
    # ``Subject.number_of_enrollees`` cache, which can lag enrollment commits.
    capacity_rows = []
    subj_qs = Subject.objects.exclude(max_number_of_enrollees__isnull=True).exclude(
        max_number_of_enrollees=0,
    )
    live_counts_qs = (
        enrolls.filter(status="enrolled")
        .values("subject_id")
        .annotate(c=Count("student_id", distinct=True))
    )
    live_counts = {row["subject_id"]: row["c"] for row in live_counts_qs}
    near_cap_count = 0
    over_cap_count = 0
    for s in subj_qs:
        max_e = s.max_number_of_enrollees or 0
        enrollees = live_counts.get(s.id, 0)
        pct = round(enrollees / max_e * 100) if max_e else 0
        if pct >= 100:
            tone = "danger"
            over_cap_count += 1
        elif pct >= NEAR_CAPACITY_THRESHOLD:
            tone = "warn"
            near_cap_count += 1
        else:
            tone = ""
        capacity_rows.append({
            "id": s.id,
            "code": s.subject_code or s.subject_short_name or s.subject_name[:8],
            "name": s.subject_name,
            "enrollees": enrollees,
            "max": max_e,
            "pct": pct,
            "tone": tone,
        })
    capacity_rows.sort(key=lambda r: -r["pct"])
    capacity_rows = capacity_rows[:8]

    # Overall capacity rollup (real totals across all capped subjects)
    overall_enrolled = sum(r["enrollees"] for r in capacity_rows)
    overall_max = sum(r["max"] for r in capacity_rows) or 1
    overall_pct = round(overall_enrolled / overall_max * 100)

    # ── Status mix (enrolled / dropped / completed) ──────────────
    status_mix = []
    total_status = enrolled_count + dropped_count + completed_count or 1
    for label, value, tone in [
        ("Enrolled", enrolled_count, "ok"),
        ("Dropped", dropped_count, "warn" if dropped_count else ""),
        ("Completed", completed_count, ""),
    ]:
        status_mix.append({
            "label": label,
            "value": value,
            "pct": round(value / total_status * 100),
            "tone": tone,
        })

    # ── Recent transactions (real movements in the last 7 days) ──
    recent_qs = (
        SubjectEnrollment.objects
        .filter(enrollment_date__gte=week_ago)
        .select_related("student", "subject")
        .order_by("-enrollment_date", "-id")[:8]
    )
    recent_rows = []
    for r in recent_qs:
        age = (today - r.enrollment_date).days
        recent_rows.append({
            "id": r.id,
            "student": (r.student_name or (r.student.get_full_name() if r.student else "") or
                        (r.student.username if r.student else "—")),
            "subject_name": r.subject.subject_name if r.subject else "—",
            "subject_code": r.subject.subject_code if r.subject else "",
            "date": r.enrollment_date,
            "age": age,
            "status": r.status,
        })

    # ── Term progress (semester position) ────────────────────────
    term_progress = None
    if semester:
        total_days = max(1, (semester.end_date - semester.start_date).days)
        elapsed = max(0, (today - semester.start_date).days)
        pct = min(100, round(elapsed / total_days * 100))
        term_progress = {
            "name": semester.get_semester_name_display() if hasattr(semester, "get_semester_name_display") else semester.semester_name,
            "start_date": semester.start_date,
            "end_date": semester.end_date,
            "pct": pct,
            "current_week": (elapsed // 7) + 1,
            "total_weeks": (total_days // 7) + 1,
            "days_left": max(0, (semester.end_date - today).days),
        }

    # ── "Needs your attention" highlight ─────────────────────────
    attention_items = []
    if over_cap_count:
        attention_items.append({
            "label": f"{over_cap_count} subject{'s' if over_cap_count != 1 else ''} over capacity",
            "detail": "Cap is breached — open another section or raise the cap.",
            "icon": "fa-circle-exclamation",
        })
    if near_cap_count:
        attention_items.append({
            "label": f"{near_cap_count} subject{'s' if near_cap_count != 1 else ''} near capacity (≥{NEAR_CAPACITY_THRESHOLD}%)",
            "detail": "Likely to fill this week — prep an overflow plan.",
            "icon": "fa-hourglass-half",
        })
    if week_dropped:
        attention_items.append({
            "label": f"{week_dropped} drop{'s' if week_dropped != 1 else ''} this week",
            "detail": "Confirm reason codes and update transcripts.",
            "icon": "fa-user-minus",
        })
    if term_progress and term_progress["days_left"] <= 14 and term_progress["days_left"] > 0:
        attention_items.append({
            "label": f"Term ends in {term_progress['days_left']} day{'s' if term_progress['days_left'] != 1 else ''}",
            "detail": "Lock grades and prep transcripts.",
            "icon": "fa-flag-checkered",
        })
    attention_status = "warn" if attention_items else "ok"

    kpis = [
        {"label": "Active enrollments", "value": enrolled_count, "hint": "this semester", "tone": ""},
        {"label": "New today", "value": todays_tx, "hint": "transactions filed today", "tone": ""},
        {"label": "Past 7 days", "value": week_tx, "hint": "new enrollments", "tone": ""},
        {"label": "Drops (7d)", "value": week_dropped, "hint": "review reason codes",
         "tone": "danger" if week_dropped else "ok"},
    ]

    context = {
        "role_tag": "Registrar",
        "time_of_day": time_of_day(),
        "as_of": now.strftime("%b %d · %I:%M %p"),
        "semester": semester,
        "term_progress": term_progress,
        "kpis": kpis,
        "status_mix": status_mix,
        "capacity_rows": capacity_rows,
        "overall_capacity": {
            "enrolled": overall_enrolled,
            "max": overall_max,
            "pct": min(100, overall_pct),
            "near": near_cap_count,
            "over": over_cap_count,
        },
        "recent_rows": recent_rows,
        "attention_items": attention_items,
        "attention_status": attention_status,
    }
    return render(request, "operations/registrar_dashboard.html", context)
