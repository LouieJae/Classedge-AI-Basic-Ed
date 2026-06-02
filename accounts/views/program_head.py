"""[Classedge LMS] Program Head Operations dashboard — program-scoped view."""
from collections import OrderedDict
from datetime import datetime

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.utils.dashboard_helpers import time_of_day, user_role_name as _user_role_name

from accounts.models import Profile
from accounts.models.course_models import Course
from accounts.models.department_models import Department
from course.models.attendance_model import Attendance
from course.models.semester_model import Semester
from gamification.models import StudentGamification
from subject.models.subject_model import Subject
from subject.models.schedule_model import Schedule


SHARED_PH_ROLES = {"program head", "academic director"}


def _is_program_head(user):
    return user.is_authenticated and user.role_name in SHARED_PH_ROLES




def _faculty_rows(department, limit=8):
    """[Classedge LMS] Teachers attached to the program head's department, with subject counts."""
    if department is None:
        return []
    teachers = (
        Profile.objects
        .filter(role__name__iexact="Teacher", department_fields=department)
        .select_related("user")
        .order_by("first_name", "last_name")[:limit]
    )
    rows = []
    for t in teachers:
        subj_count = Subject.objects.filter(assign_teacher=t.user).count()
        rows.append({
            "id": t.id,
            "first_name": t.first_name or "",
            "last_name": t.last_name or "",
            "email": getattr(t.user, "email", "") or getattr(t.user, "username", ""),
            "id_number": t.id_number or "",
            "subjects": subj_count,
        })
    return rows


def _subject_rows(department, limit=8):
    """[Classedge LMS] Subjects taught by any faculty in the program head's department.

    Enrollee counts are computed live from ``SubjectEnrollment`` (status =
    ``enrolled``, scoped to the current semester when one is active). The
    stored ``Subject.number_of_enrollees`` was unreliable.
    """
    from course.models.subject_enrollment_model import SubjectEnrollment

    if department is None:
        return []

    today = timezone.localdate()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()

    qs = (
        Subject.objects
        .filter(assign_teacher__profile__department_fields=department)
        .exclude(is_coil=True).exclude(is_hali=True)
        .select_related("assign_teacher")
        .distinct()
    )

    rows = []
    for s in qs:
        teacher = s.assign_teacher
        teacher_name = ""
        if teacher:
            teacher_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or teacher.username
        enrollment_qs = SubjectEnrollment.objects.filter(subject=s, status="enrolled")
        if semester:
            enrollment_qs = enrollment_qs.filter(semester=semester)
        enrollees = enrollment_qs.count()
        max_cap = s.max_number_of_enrollees or 0
        rows.append({
            "id": s.id,
            "name": s.subject_name,
            "code": s.subject_code or "",
            "teacher": teacher_name or "Unassigned",
            "enrollees": enrollees,
            "max": max_cap,
            "status": s.status or "Available",
            "fill_pct": round(enrollees / max_cap * 100) if max_cap else 0,
        })
    rows.sort(key=lambda r: (-r["enrollees"], r["name"] or ""))
    return rows[:limit]


def _content_gap_subjects_for_department(department, limit=5):
    """[Classedge LMS] Department-scoped mirror of the Academic Director's
    content-gap scan. Surface subjects taught by faculty in the program
    head's department that have no Activity or Module loaded for the
    current semester. Falls back to the lowest-content subjects when
    every one has at least some material.
    """
    from activity.models.activity_model import Activity
    from course.models.subject_enrollment_model import SubjectEnrollment
    from module.models.module import Module

    if department is None:
        return {"items": [], "is_fallback": False}

    today = timezone.localdate()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()
    if not semester:
        return {"items": [], "is_fallback": False}

    active_subject_ids = (
        SubjectEnrollment.objects.filter(semester=semester, status="enrolled")
        .values_list("subject_id", flat=True)
        .distinct()
    )
    subjects = (
        Subject.objects
        .filter(pk__in=active_subject_ids,
                assign_teacher__profile__department_fields=department)
        .exclude(is_coil=True).exclude(is_hali=True).exclude(is_cte=True)
        .select_related("assign_teacher")
        .distinct()
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


def _at_risk_students_in_program(students_qs):
    """[Classedge LMS] Students in the program whose overall attendance
    across this semester's enrolled subjects falls below the medium
    threshold. Matches the formula used by the teacher subject analytics
    panel.
    """
    from at_risk.calculator import count_at_risk_students
    from course.models.semester_model import Semester
    from django.utils import timezone

    user_ids = list(students_qs.values_list("user_id", flat=True))
    if not user_ids:
        return 0
    today = timezone.localdate()
    semester = Semester.objects.filter(
        start_date__lte=today, end_date__gte=today,
    ).first()
    return count_at_risk_students(semester, student_ids=user_ids)


@login_required
@user_passes_test(_is_program_head)
def program_head_dashboard(request):
    """[Classedge LMS] Render the Program Head dashboard scoped to the head's own program."""
    profile = getattr(request.user, "profile", None)
    my_department = getattr(profile, "department_fields", None) if profile else None

    students_qs = Profile.objects.filter(role__name__iexact="Student")
    if my_department is not None:
        students_qs = students_qs.filter(course__department=my_department)

    total_students = students_qs.count()
    active_students = students_qs.filter(status=True).count()
    at_risk = _at_risk_students_in_program(students_qs)

    faculty_rows = _faculty_rows(my_department)
    subject_rows = _subject_rows(my_department)

    department_faculty_total = (
        Profile.objects.filter(role__name__iexact="Teacher", department_fields=my_department).count()
        if my_department else 0
    )

    kpis = [
        {"label": "Students", "value": total_students, "icon": "fa-user-graduate", "tone": ""},
        {"label": "Active", "value": active_students, "icon": "fa-circle-check", "tone": "ok" if active_students else ""},
        {"label": "Faculty", "value": department_faculty_total, "icon": "fa-chalkboard-user", "tone": ""},
        {"label": "At-risk", "value": at_risk, "icon": "fa-triangle-exclamation",
         "tone": "danger" if at_risk else "ok"},
    ]

    # ── "Needs your attention" highlight signals ─────────────────
    # Surface things a Program Head can act on TODAY: at-risk students,
    # subjects that are over capacity, and subjects that are anaemic.
    over_capacity_subjects = [s for s in subject_rows if s["max"] and s["fill_pct"] > 100]
    low_fill_subjects = [s for s in subject_rows if s["max"] and 0 < s["fill_pct"] < 30]
    no_load_faculty = [f for f in faculty_rows if f["subjects"] == 0]

    content_gap = _content_gap_subjects_for_department(my_department)

    attention_items = []
    # Only flag content gap when there are subjects with *zero* content.
    # The "least content" fallback can otherwise misrepresent a healthy
    # subject (e.g. 29 assessments + 5 materials) as needing attention
    # simply because it ranks lowest in a fully-loaded department.
    if content_gap["items"] and not content_gap["is_fallback"]:
        gap_rows = content_gap["items"]
        attention_items.append({
            "kind": "content_gap",
            "label": f"{len(gap_rows)} subject{'s' if len(gap_rows) != 1 else ''} with no assessment or materials",
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
        })
    if over_capacity_subjects:
        attention_items.append({
            "kind": "overcap",
            "label": f"{len(over_capacity_subjects)} subject{'s' if len(over_capacity_subjects) != 1 else ''} over capacity",
            "detail": "Open another section or raise the cap.",
            "icon": "fa-people-group",
        })
    if low_fill_subjects:
        attention_items.append({
            "kind": "lowfill",
            "label": f"{len(low_fill_subjects)} subject{'s' if len(low_fill_subjects) != 1 else ''} under 30% filled",
            "detail": "Promote, merge, or hold.",
            "icon": "fa-chart-simple",
        })
    if no_load_faculty:
        attention_items.append({
            "kind": "noload",
            "label": f"{len(no_load_faculty)} faculty with no subject load",
            "detail": "Confirm assignment for this term.",
            "icon": "fa-chalkboard-user",
        })
    attention_status = "warn" if attention_items else "ok"

    # ── Term progress (current semester position) ────────────────
    now = timezone.localtime()
    today = now.date()
    semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
    term_progress = None
    if semester:
        total_days = max(1, (semester.end_date - semester.start_date).days)
        elapsed_days = max(0, (today - semester.start_date).days)
        pct = min(100, round(elapsed_days / total_days * 100))
        current_week = (elapsed_days // 7) + 1
        total_weeks = (total_days // 7) + 1
        days_left = max(0, (semester.end_date - today).days)
        term_progress = {
            "name": semester.get_semester_name_display() if hasattr(semester, "get_semester_name_display") else semester.semester_name,
            "start_date": semester.start_date,
            "end_date": semester.end_date,
            "pct": pct,
            "current_week": current_week,
            "total_weeks": total_weeks,
            "days_left": days_left,
        }

    # ── Today's class schedule (program's subjects only) ─────────
    schedule_today = []
    if subject_rows:
        program_subject_ids = [s["id"] for s in subject_rows]
        today_short = now.strftime("%a")  # Mon, Tue, ...
        sched_qs = (
            Schedule.objects
            .filter(subject_id__in=program_subject_ids, days_of_week__icontains=today_short)
            .select_related("subject", "subject__assign_teacher")
        )
        if semester:
            sched_qs = sched_qs.filter(Q(semester=semester) | Q(semester__isnull=True))
        now_t = now.time()
        for sch in sched_qs:
            start_t = sch.schedule_start_time
            end_t = sch.schedule_end_time
            if start_t and end_t and start_t <= now_t <= end_t:
                status = "now"
            elif start_t and start_t > now_t:
                status = "upcoming"
            else:
                status = "done"
            teacher = sch.subject.assign_teacher
            teacher_name = ""
            if teacher:
                teacher_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or teacher.username
            schedule_today.append({
                "subject": sch.subject,
                "start_time": start_t,
                "end_time": end_t,
                "room": sch.subject.room_number or "",
                "teacher": teacher_name,
                "status": status,
            })
        order = {"now": 0, "upcoming": 1, "done": 2}
        schedule_today.sort(key=lambda s: (order[s["status"]], s["start_time"] or datetime.min.time()))

    # ── Attendance health (top 5 lowest-attendance subjects this semester) ──
    attendance_health = []
    if semester and subject_rows:
        # Count present/late days vs total session days per subject, capped to
        # the current semester window. Surface the 5 with the worst attendance
        # so the Program Head can flag teachers/classes that need a nudge.
        for s in subject_rows[:10]:
            total_days = (
                Attendance.objects
                .filter(subject_id=s["id"],
                        date__gte=semester.start_date,
                        date__lte=semester.end_date)
                .values("date").distinct().count()
            )
            if total_days == 0:
                continue
            student_days_total = (
                Attendance.objects
                .filter(subject_id=s["id"],
                        date__gte=semester.start_date,
                        date__lte=semester.end_date)
                .count()
            )
            present_days = (
                Attendance.objects
                .filter(subject_id=s["id"],
                        date__gte=semester.start_date,
                        date__lte=semester.end_date,
                        status__status__in=["Present", "Present_Online", "Late"])
                .count()
            )
            if student_days_total == 0:
                continue
            pct = round(present_days / student_days_total * 100)
            attendance_health.append({
                "name": s["name"],
                "code": s["code"],
                "pct": pct,
                "tone": "danger" if pct < 70 else ("warn" if pct < 85 else "ok"),
            })
        attendance_health.sort(key=lambda x: x["pct"])
        attendance_health = attendance_health[:5]

    context = {
        "role_tag": _user_role_name(request.user) or "Program Head",
        "time_of_day": time_of_day(),
        "as_of": timezone.localtime().strftime("%b %d · %I:%M %p"),
        "my_department": my_department,
        "kpis": kpis,
        "faculty_rows": faculty_rows,
        "subject_rows": subject_rows,
        "totals": {
            "students": total_students,
            "active": active_students,
            "at_risk": at_risk,
            "department_faculty": department_faculty_total,
        },
        "attention_items": attention_items,
        "attention_status": attention_status,
        "content_gap": content_gap,
        "term_progress": term_progress,
        "schedule_today": schedule_today,
        "attendance_health": attendance_health,
        "now_dt": now,
    }
    return render(request, "operations/program_head_dashboard.html", context)
