"""[Classedge LMS] Academic Director Operations Mode dashboard view."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day, user_role_name as _user_role_name

from accounts.models import Profile
from accounts.models.course_models import Course
from accounts.models.department_models import Department
from central_content.models.curriculum_plan import CurriculumPlan
from gamification.models import StudentGamification
from module.models.module import Module
from subject.models.subject_model import Subject


SHARED_ACADEMIC_ROLES = {"academic director", "program head"}


def _is_shared_academic_role(user):
    """[Classedge LMS] Allow Academic Director and Program Head to share the dashboard.

    Time Keepers have their own calendar-first dashboard
    (accounts/views/time_keeper.py); they're no longer routed through here.
    """
    return user.is_authenticated and user.role_name in SHARED_ACADEMIC_ROLES




def _at_risk_count():
    """[Classedge LMS] Institution-wide at-risk count based on attendance
    across all current-semester subjects. Matches the formula used by the
    teacher subject analytics panel (attendance vs scheduled meetings).
    """
    from at_risk.calculator import count_at_risk_students
    from course.models.semester_model import Semester

    today = timezone.localdate()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()
    return count_at_risk_students(semester)


def _curriculum_counts():
    """[Classedge LMS] Approved / Pending curriculum plan counts plus coverage %."""
    total = CurriculumPlan.objects.count()
    if not total:
        return {"approved": 0, "pending": 0, "rejected": 0, "total": 0, "coverage_pct": None}
    approved = CurriculumPlan.objects.filter(status__iexact="approved").count()
    rejected = CurriculumPlan.objects.filter(status__iexact="rejected").count()
    pending = total - approved - rejected
    return {
        "approved": approved,
        "pending": pending,
        "rejected": rejected,
        "total": total,
        "coverage_pct": round(approved / total * 100, 1),
    }


def _faculty_count():
    return Profile.objects.filter(role__name__iexact="Teacher").count()


def _student_counts():
    qs = Profile.objects.filter(role__name__iexact="Student")
    return {
        "total": qs.count(),
        "active": qs.filter(status=True).count(),
    }


def _program_rows():
    """[Classedge LMS] Per-program roster + current-semester engagement.

    "Engagement %" = students in the program who have logged in on or
    after the current semester's start date, divided by the total number
    of students assigned to the program. Replaces the older
    ``Profile.status`` flag which only reflected static activation, not
    actual LMS usage.
    """
    from course.models.semester_model import Semester
    from django.contrib.auth import get_user_model

    User = get_user_model()

    today = timezone.localdate()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()

    rows = []
    courses = Course.objects.all().order_by("short_name", "name")
    for c in courses:
        program_student_ids = list(
            Profile.objects.filter(role__name__iexact="Student", course=c)
            .values_list("user_id", flat=True)
        )
        student_total = len(program_student_ids)

        if semester and program_student_ids:
            active = (
                User.objects.filter(
                    pk__in=program_student_ids,
                    last_login__date__gte=semester.start_date,
                ).count()
            )
        else:
            active = 0

        rows.append({
            "name": c.name or "—",
            "short": c.short_name or "",
            "students": student_total,
            "active": active,
            "active_pct": round(active / student_total * 100) if student_total else 0,
        })
    return rows


def _department_rows():
    """[Classedge LMS] Per-department snapshot — semesters + faculty/student attached."""
    rows = []
    for d in Department.objects.all().order_by("name").annotate(
        sem_count=Count("semesters", distinct=True),
    ):
        teachers = Profile.objects.filter(role__name__iexact="Teacher", department_fields=d).count()
        students = Profile.objects.filter(role__name__iexact="Student", department_fields=d).count()
        rows.append({
            "id": d.id,
            "name": d.name,
            "semesters": d.sem_count,
            "teachers": teachers,
            "students": students,
        })
    return rows


def _content_gap_subjects(limit=5):
    """[Classedge LMS] Surface subjects whose teachers haven't loaded
    anything yet.

    Primary: subjects that have **no Activity rows AND no Module rows**
    in the active semester — completely empty courses.

    Fallback: when every current-semester subject has at least some
    content, return the lowest ``limit`` subjects ranked by total
    Activity + Module count so the AD can still see who's lagging.

    Each row carries the teacher name + counts so the AD can chase the
    right person from a single glance.
    """
    from django.db.models import Count
    from activity.models.activity_model import Activity
    from course.models.semester_model import Semester
    from course.models.subject_enrollment_model import SubjectEnrollment
    from module.models.module import Module
    from subject.models.subject_model import Subject

    today = timezone.localdate()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()
    if not semester:
        return {"items": [], "is_fallback": False}

    # Scope to subjects with current-semester enrollment, excluding
    # Orbit Program courses (COIL/HALI/CTE) which run on their own track.
    active_subject_ids = (
        SubjectEnrollment.objects.filter(semester=semester, status="enrolled")
        .values_list("subject_id", flat=True)
        .distinct()
    )
    subjects = (
        Subject.objects.filter(pk__in=active_subject_ids)
        .exclude(is_coil=True).exclude(is_hali=True).exclude(is_cte=True)
        .select_related("assign_teacher")
    )

    counts = []
    for subj in subjects:
        activity_count = Activity.objects.filter(subject=subj).count()
        module_count = Module.objects.filter(subject=subj).count()
        teacher = subj.assign_teacher
        teacher_name = (
            (teacher.get_full_name() or teacher.username) if teacher else "Unassigned"
        )
        counts.append({
            "subject_id": subj.pk,
            "subject_name": subj.subject_name or "—",
            "subject_code": subj.subject_code or "",
            "teacher_name": teacher_name,
            "activity_count": activity_count,
            "module_count": module_count,
            "total": activity_count + module_count,
        })

    empty_rows = [c for c in counts if c["total"] == 0]
    if empty_rows:
        return {"items": empty_rows[:limit], "is_fallback": False}

    counts.sort(key=lambda c: (c["total"], c["subject_name"]))
    return {"items": counts[:limit], "is_fallback": True}


def _top_rated_teachers(limit=6, min_ratings=3):
    """[Classedge LMS] Top teachers by student star rating in the active
    semester. ``min_ratings`` filters out single-vote outliers; only
    teachers with at least that many ratings this semester appear.
    """
    from django.db.models import Avg, Count
    from gamification.teacher_models import TeacherRating

    today = timezone.localdate()
    from course.models.semester_model import Semester
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()

    qs = TeacherRating.objects.all()
    if semester:
        qs = qs.filter(semester=semester)

    aggregated = (
        qs.values("teacher_id", "teacher__first_name", "teacher__last_name")
        .annotate(avg_stars=Avg("stars"), rating_count=Count("id"))
        .filter(rating_count__gte=min_ratings)
        .order_by("-avg_stars", "-rating_count")[:limit]
    )

    rows = []
    for r in aggregated:
        first = (r.get("teacher__first_name") or "").strip()
        last = (r.get("teacher__last_name") or "").strip()
        full = (first + " " + last).strip() or "Unnamed teacher"
        avg = float(r["avg_stars"]) if r["avg_stars"] is not None else 0.0
        rows.append({
            "teacher_id": r["teacher_id"],
            "name": full,
            "avg_stars": round(avg, 2),
            "avg_pct": round(avg / 5 * 100),
            "rating_count": r["rating_count"],
        })
    return rows


def _pending_curriculum_decisions():
    """[Classedge LMS] Recent CurriculumPlan submissions still awaiting review."""
    qs = (
        CurriculumPlan.objects
        .filter(status__iexact="draft")
        .select_related("textbook", "generated_by")
        .order_by("-created_at")[:6]
    )
    rows = []
    today = timezone.localdate()
    for p in qs:
        age = (today - p.created_at.date()).days
        rows.append({
            "title": getattr(p.textbook, "title", "(unknown textbook)"),
            "model": p.model_key,
            "submitted": p.created_at.strftime("%b %d, %Y"),
            "age_days": age,
            "weeks": p.session_count,
            "minutes": p.minutes_per_session,
        })
    return rows


def _content_health():
    """[Classedge LMS] Subject + Module health snapshot."""
    return {
        "subjects": Subject.objects.count(),
        "modules": Module.objects.count(),
        "ongoing_subjects": Subject.objects.filter(status="Ongoing").count(),
    }


@login_required
@user_passes_test(_is_shared_academic_role)
def academic_director_dashboard(request):
    """[Classedge LMS] Academic Director / Program Head / Time Keeper dashboard."""
    # `_user_role_name` was referenced but never defined/imported. Use the
     # role accessor the rest of the codebase relies on; fall back to the
     # account's `role_name` attribute and finally to a sane default.
    role_name = (
        getattr(getattr(request.user, "profile", None), "role", None)
        and getattr(request.user.profile.role, "name", None)
    ) or getattr(request.user, "role_name", None) or "Academic Director"
    role_name = role_name.title() if isinstance(role_name, str) else "Academic Director"
    curriculum = _curriculum_counts()
    students = _student_counts()
    at_risk = _at_risk_count()
    pending_decisions = _pending_curriculum_decisions()
    top_teachers = _top_rated_teachers()
    content_gap = _content_gap_subjects()
    program_rows = _program_rows()

    # Paginate the program-performance table so the dashboard stays
    # compact in schools with many programs. Keep the full list around
    # for the "Needs your attention" recap (low-engagement scan).
    try:
        program_page_number = int(request.GET.get("program_page", "1"))
    except (TypeError, ValueError):
        program_page_number = 1
    program_paginator = Paginator(program_rows, 8)
    program_page = program_paginator.get_page(program_page_number)

    kpis = [
        {"label": "Programs", "value": Course.objects.count(), "icon": "fa-book-open", "tone": ""},
        {"label": "Faculty", "value": _faculty_count(), "icon": "fa-chalkboard-user", "tone": ""},
        {"label": "Active students", "value": students["active"], "icon": "fa-user-graduate", "tone": ""},
        {
            "label": "At-risk students",
            "value": at_risk,
            "icon": "fa-triangle-exclamation",
            "tone": "danger" if at_risk else "ok",
        },
    ]

    # ── Drive the "Needs your attention" highlight ──────────────
    # The AD's job-to-be-done from this page is "what decisions am I
    # late on, and which students need outreach?" Surface those — plus
    # any programs with low engagement — as actionable items.
    stale_pending_count = sum(1 for d in pending_decisions if d["age_days"] >= 14)
    low_engagement_programs = [p for p in program_rows if p["students"] and p["active_pct"] < 50]

    attention_items = []
    # Only flag content gap when there are subjects with *zero* content.
    # The "least content" fallback can otherwise misrepresent a healthy
    # subject as needing attention simply because it ranks lowest.
    if content_gap["items"] and not content_gap["is_fallback"]:
        gap_rows = content_gap["items"]
        attention_items.append({
            "kind": "content_gap",
            "label": f"{len(gap_rows)} course{'s' if len(gap_rows) != 1 else ''} with no assessment or materials",
            "detail": "Teachers haven't loaded anything yet. Follow up before students fall behind.",
            "icon": "fa-folder-open",
            "url": "",
            "rows": gap_rows,
            "is_fallback": False,
        })
    if at_risk:
        attention_items.append({
            "kind": "atrisk",
            "label": f"{at_risk} at-risk student{'s' if at_risk != 1 else ''}",
            "detail": "Coordinate intervention with their teachers.",
            "icon": "fa-triangle-exclamation",
            "url": "",
        })
    if low_engagement_programs:
        attention_items.append({
            "kind": "engagement",
            "label": f"{len(low_engagement_programs)} program{'s' if len(low_engagement_programs) != 1 else ''} under 50% active",
            "detail": "Review staffing, schedules, or content health.",
            "icon": "fa-chart-line",
            "url": "",
        })
    attention_status = "warn" if attention_items else "ok"

    context = {
        "role_tag": role_name,
        "time_of_day": time_of_day(),
        "as_of": timezone.localtime().strftime("%b %d · %I:%M %p"),
        "kpis": kpis,
        "curriculum": curriculum,
        "students": students,
        "program_rows": program_rows,
        "program_page": program_page,
        "pending_decisions": pending_decisions,
        "top_teachers": top_teachers,
        "content_gap": content_gap,
        "attention_items": attention_items,
        "attention_status": attention_status,
        "stale_pending_count": stale_pending_count,
    }
    return render(request, "operations/academic_director_dashboard.html", context)
