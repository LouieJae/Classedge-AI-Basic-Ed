from datetime import date, timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from activity.utils.grade_calculation_utils import get_student_activity_summary
from course.models.attendance_model import Attendance, TeacherAttendancePoints
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term
from subject.models.schedule_model import Schedule


_DAY_TO_WEEKDAY = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
    "Fri": 4, "Sat": 5, "Sun": 6,
}


def _count_scheduled_meetings(subject, semester):
    """Total class meetings expected from this subject's Schedule between
    semester.start_date and today (capped at semester.end_date). Used as
    the denominator for attendance-based risk scoring so a student
    measured against "10 of 20 sessions" matches the real schedule.
    """
    schedules = Schedule.objects.filter(subject=subject, semester=semester)
    if not schedules.exists():
        return 0

    weekdays = set()
    for sched in schedules:
        for day in (sched.days_of_week or []):
            wd = _DAY_TO_WEEKDAY.get(day)
            if wd is not None:
                weekdays.add(wd)
    if not weekdays:
        return 0

    today = date.today()
    end = min(today, semester.end_date) if semester.end_date else today
    if end < semester.start_date:
        return 0

    total = 0
    current = semester.start_date
    while current <= end:
        if current.weekday() in weekdays:
            total += 1
        current += timedelta(days=1)
    return total


def count_at_risk_students(semester, student_ids=None):
    """Count students whose **overall attendance across all enrolled
    subjects** this semester is below the medium threshold (65%).

    This is the dashboard-scale counterpart to :func:`calculate_risk_scores`.
    Both apply the same definition of attendance (Present + Online + Late
    divided by scheduled class meetings so far); this version aggregates
    across every subject the student is enrolled in so a single number can
    be shown on Program Head / Academic Director dashboards.

    Args:
        semester: the active :class:`Semester` to scope against. Pass
            ``None`` to short-circuit to ``0`` when no semester is active.
        student_ids: optional iterable of ``CustomUser.pk`` to restrict
            the count (e.g. students of a single program). Omit for an
            institution-wide count.
    """
    if not semester:
        return 0

    threshold = settings.AT_RISK_MEDIUM_THRESHOLD

    enrollments_qs = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled",
    )
    if student_ids is not None:
        enrollments_qs = enrollments_qs.filter(student_id__in=list(student_ids))
    if not enrollments_qs.exists():
        return 0

    # Cache scheduled-meeting counts per subject so we don't recompute
    # them per enrollment.
    from subject.models.subject_model import Subject  # noqa: WPS433 — local import to avoid app-load cycles
    subject_ids = list(enrollments_qs.values_list("subject_id", flat=True).distinct())
    subjects = Subject.objects.filter(pk__in=subject_ids)
    scheduled_per_subject = {
        s.pk: _count_scheduled_meetings(s, semester) for s in subjects
    }

    by_student = {}  # student_id -> [scheduled_total, present_total]
    for stu_id, subj_id in enrollments_qs.values_list("student_id", "subject_id"):
        scheduled = scheduled_per_subject.get(subj_id, 0)
        if not scheduled:
            continue
        bucket = by_student.setdefault(stu_id, [0, 0])
        bucket[0] += scheduled

    if not by_student:
        return 0

    earned_map = _sum_attendance_points(
        list(by_student.keys()), subject_ids, semester,
    )
    for stu_id, earned in earned_map.items():
        if stu_id in by_student:
            by_student[stu_id][1] = earned

    at_risk = 0
    for scheduled, earned in by_student.values():
        if scheduled <= 0:
            continue
        pct = (earned / scheduled) * 100
        if pct < threshold:
            at_risk += 1
    return at_risk


def calculate_risk_scores(subject, semester, request_user=None):
    weights = settings.AT_RISK_WEIGHTS
    high_threshold = settings.AT_RISK_HIGH_THRESHOLD
    medium_threshold = settings.AT_RISK_MEDIUM_THRESHOLD

    enrollments = SubjectEnrollment.objects.filter(
        subject=subject,
        semester=semester,
        status="enrolled",
    ).select_related("student")

    if not enrollments.exists():
        return []

    terms = Term.objects.filter(semester=semester)
    passing_grade = semester.passing_grade or 75

    graded_activities = Activity.objects.filter(
        subject=subject,
        term__in=terms,
        is_graded=True,
    )
    total_activities = graded_activities.count()

    total_scheduled_meetings = _count_scheduled_meetings(subject, semester)

    # Canonical gradebook final grade per student — same computation the
    # teacher gradebook + the student "My Grades" page use. We key by
    # student_id so risk scoring matches what teachers actually see.
    final_grade_by_student = _build_final_grade_map(
        subject, semester, terms, request_user
    )

    results = []
    for enrollment in enrollments:
        student = enrollment.student

        grade_score = _calc_grade_score(
            student, final_grade_by_student, passing_grade,
        )
        completion_score = _calc_completion_score(student, graded_activities, total_activities)
        attendance_score = _calc_attendance_score(student, subject, semester, total_scheduled_meetings)

        risk_score = (
            grade_score * weights["grade"]
            + completion_score * weights["completion"]
            + attendance_score * weights["attendance"]
        )

        if risk_score < high_threshold:
            risk_level = "high"
        elif risk_score < medium_threshold:
            risk_level = "medium"
        else:
            risk_level = "low"

        results.append({
            "student_id": student.pk,
            "student_name": student.get_full_name() or student.username,
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "grade_score": round(grade_score, 1),
            "completion_score": round(completion_score, 1),
            "attendance_score": round(attendance_score, 1),
        })

    results.sort(key=lambda r: r["risk_score"])
    return results


def _build_final_grade_map(subject, semester, terms, request_user):
    """Run the canonical weighted-gradebook helper once per subject and
    return ``{student_id: final_grade}``. The summary helper requires a
    non-student ``request_user`` to return data for the whole class; if a
    student object slips in, it would filter the queryset down to one row.
    """
    if not terms.exists():
        return {}
    activities_qs = StudentActivity.objects.select_related(
        "activity", "activity__activity_type", "activity__subject", "term", "student__profile",
    ).filter(
        term__semester=semester,
        activity__subject=subject,
        activity__status=True,
    )
    attendance_qs = Attendance.objects.select_related("subject", "student").filter(
        subject=subject,
        graded=True,
        date__range=(semester.start_date, semester.end_date),
    )
    try:
        summary = get_student_activity_summary(
            semester, subject, list(terms), activities_qs, attendance_qs, request_user,
        )
    except Exception:
        # Defensive: if the gradebook helper raises for any reason (no
        # questions yet, malformed term breakdown, etc.) we don't want the
        # entire panel to 500 — fall back to an empty map so the rest of
        # the risk scoring still runs on completion/attendance.
        return {}

    result = {}
    for entry in summary.values():
        sid = entry.get("student_id")
        final = entry.get("final_grade")
        if sid is not None and final is not None:
            try:
                result[sid] = float(final)
            except (TypeError, ValueError):
                continue
    return result


def _calc_grade_score(student, final_grade_by_student, passing_grade):
    """Map the student's actual gradebook final grade to a 0-100 risk
    score. Passing the threshold lands at 100; below it scales linearly
    toward 0.
    """
    final_grade = final_grade_by_student.get(student.pk)
    if final_grade is None:
        return 50.0
    if final_grade >= passing_grade:
        return 100.0
    return max(0.0, (final_grade / passing_grade) * 100)


def _calc_completion_score(student, graded_activities, total_activities):
    if total_activities == 0:
        return 50.0

    submitted = StudentActivity.objects.filter(
        student=student,
        activity__in=graded_activities,
    ).count()

    return (submitted / total_activities) * 100


def _calc_attendance_score(student, subject, semester, total_scheduled_meetings):
    """Attendance points earned ÷ total scheduled class meetings, as a
    percentage.

    Uses each teacher's configured :class:`TeacherAttendancePoints` scale
    so that Present / Late / Absent / Excused each contribute their
    weighted share (typical config: Present 1.0, Late 0.5, Absent 0.0,
    Excused 1.0). ``total_scheduled_meetings`` is the denominator (max
    points per session is treated as 1.0, matching the default scale).
    Only ``graded=True`` attendance records count.
    """
    if total_scheduled_meetings <= 0:
        # No schedule defined, or semester hasn't started — can't fairly
        # score attendance yet. Neutral default keeps the student off the
        # at-risk list until there's something to measure.
        return 50.0

    earned = _sum_attendance_points([student.pk], [subject.pk], semester).get(student.pk, 0.0)
    pct = (earned / total_scheduled_meetings) * 100
    return max(0.0, min(pct, 100.0))


def _sum_attendance_points(student_ids, subject_ids, semester):
    """Sum attendance points per student across the given subjects within
    the semester. Returns ``{student_id: float_points}``.

    Pulls only the (teacher, status) pairs actually present in the
    attendance rows, so the :class:`TeacherAttendancePoints` lookup is a
    single bounded query regardless of how many records are involved.
    """
    if not student_ids or not subject_ids:
        return {}

    rows = list(
        Attendance.objects.filter(
            student_id__in=list(student_ids),
            subject_id__in=list(subject_ids),
            date__gte=semester.start_date,
            date__lte=semester.end_date,
            graded=True,
            status__isnull=False,
            teacher__isnull=False,
        ).values_list("student_id", "teacher_id", "status_id")
    )
    if not rows:
        return {}

    teacher_ids = {r[1] for r in rows}
    status_ids = {r[2] for r in rows}
    points_map = {
        (tp.teacher_id, tp.status_id): float(tp.points)
        for tp in TeacherAttendancePoints.objects.filter(
            teacher_id__in=teacher_ids, status_id__in=status_ids,
        )
    }

    earned = {}
    for stu_id, teacher_id, status_id in rows:
        pts = points_map.get((teacher_id, status_id), 0.0)
        earned[stu_id] = earned.get(stu_id, 0.0) + pts
    return earned
