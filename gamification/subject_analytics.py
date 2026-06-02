from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404

from django.utils import timezone

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from at_risk.calculator import calculate_risk_scores
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term
from gamification.models import StudentGamification, StudentBadge
from module.models.module import Module
from module.models.student_progress import StudentProgress
from subject.models.subject_model import Subject


def _authorize_subject(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    user = request.user
    if not (subject.assign_teacher == user or user in subject.collaborators.all()):
        raise PermissionDenied
    return subject


def _active_semester():
    now = timezone.now()
    return Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()


@permission_required('gamification.view_studentgamification', raise_exception=True)
def subject_panel_view(request, subject_id):
    try:
        subject = _authorize_subject(request, subject_id)
    except PermissionDenied:
        return HttpResponseForbidden()

    semester = _active_semester()
    terms = Term.objects.filter(semester=semester) if semester else Term.objects.none()

    enrolled_ids = list(
        SubjectEnrollment.objects.filter(
            subject=subject, semester=semester, status="enrolled",
        ).values_list("student_id", flat=True)
    ) if semester else []

    # -- Summary tiles --
    risk_data = calculate_risk_scores(subject, semester, request.user) if semester else []
    at_risk_count = sum(1 for r in risk_data if r["risk_level"] in ("high", "medium"))

    graded_acts = Activity.objects.filter(subject=subject, term__in=terms, is_graded=True)
    total_possible = graded_acts.count() * len(enrolled_ids)
    submitted_count = StudentActivity.objects.filter(
        student__in=enrolled_ids, activity__in=graded_acts,
    ).count()
    completion_pct = round(submitted_count / total_possible * 100) if total_possible else 0

    # Per-student avg score (as %) and avg score by activity type — single query
    RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
    student_avgs = {}
    type_scores = {}
    for sa in StudentActivity.objects.filter(
        student__in=enrolled_ids, subject=subject, activity__term__in=terms,
        end_time__isnull=False, activity__max_score__gt=0,
    ).select_related("activity", "activity__activity_type"):
        pct = sa.total_score / sa.activity.max_score * 100
        student_avgs.setdefault(sa.student_id, []).append(pct)
        atype = sa.activity.activity_type
        # Use display_name when present so "Participation" surfaces as
        # "Major Assessment" (matches the rest of the UI).
        if atype:
            type_name = atype.display_name or atype.name
        else:
            type_name = "Other"
        type_scores.setdefault(type_name, []).append(pct)
    student_avg_map = {k: round(sum(v) / len(v)) for k, v in student_avgs.items()}
    all_pcts = [p for pcts in student_avgs.values() for p in pcts]
    avg_score = round(sum(all_pcts) / len(all_pcts)) if all_pcts else 0
    type_chart = {k: round(sum(v) / len(v)) for k, v in type_scores.items()}

    # -- Student table --
    User = get_user_model()
    enrolled_students = list(User.objects.filter(pk__in=enrolled_ids))
    risk_by_id = {r["student_id"]: r for r in risk_data}
    student_rows = sorted(
        [
            {
                "student": stu,
                "avg_score": student_avg_map.get(stu.pk, 0),
                "risk_level": risk_by_id.get(stu.pk, {}).get("risk_level", "low"),
            }
            for stu in enrolled_students
        ],
        key=lambda x: (RISK_ORDER.get(x["risk_level"], 2), x["avg_score"]),
    )

    # -- Score distribution histogram (uses only students who have a graded score) --
    score_buckets = [
        {"label": "0–50",   "min": 0,  "max": 50,  "count": 0},
        {"label": "51–60",  "min": 51, "max": 60,  "count": 0},
        {"label": "61–70",  "min": 61, "max": 70,  "count": 0},
        {"label": "71–80",  "min": 71, "max": 80,  "count": 0},
        {"label": "81–90",  "min": 81, "max": 90,  "count": 0},
        {"label": "91–100", "min": 91, "max": 100, "count": 0},
    ]
    for pct in student_avg_map.values():
        for b in score_buckets:
            if b["min"] <= pct <= b["max"]:
                b["count"] += 1
                break

    # -- Risk distribution (for the donut) --
    risk_distribution = {
        "high":   sum(1 for r in student_rows if r["risk_level"] == "high"),
        "medium": sum(1 for r in student_rows if r["risk_level"] == "medium"),
        "low":    sum(1 for r in student_rows if r["risk_level"] == "low"),
    }

    return render(request, "teacher/gamification/subject_analytics_panel.html", {
        "subject": subject,
        "avg_score": avg_score,
        "at_risk_count": at_risk_count,
        "completion_pct": completion_pct,
        "type_chart": type_chart,
        "student_rows": student_rows,
        "score_distribution": score_buckets,
        "risk_distribution": risk_distribution,
    })


@permission_required('gamification.view_studentgamification', raise_exception=True)
def student_detail_view(request, subject_id, student_id):
    User = get_user_model()

    try:
        subject = _authorize_subject(request, subject_id)
    except PermissionDenied:
        return HttpResponseForbidden()

    student = get_object_or_404(User, pk=student_id)
    semester = _active_semester()
    terms = Term.objects.filter(semester=semester) if semester else Term.objects.none()

    # Summary tiles
    sa_qs = StudentActivity.objects.filter(
        student=student, subject=subject, activity__term__in=terms,
        end_time__isnull=False, activity__max_score__gt=0,
    ).select_related("activity")
    score_pcts = [sa.total_score / sa.activity.max_score * 100 for sa in sa_qs]
    avg_score = round(sum(score_pcts) / len(score_pcts)) if score_pcts else 0

    gam = StudentGamification.objects.filter(student=student).first()

    risk_data = calculate_risk_scores(subject, semester, request.user) if semester else []
    risk_info = next((r for r in risk_data if r["student_id"] == student.pk), {})
    risk_level = risk_info.get("risk_level", "low")

    # Section 1: Activity score history
    all_activities = Activity.objects.filter(
        subject=subject, term__in=terms, is_graded=True, max_score__gt=0,
    ).select_related("activity_type").order_by("-end_time", "-pk")
    sa_by_act = {
        sa.activity_id: sa
        for sa in StudentActivity.objects.filter(student=student, activity__in=all_activities)
    }
    activity_history = []
    for act in all_activities:
        sa = sa_by_act.get(act.pk)
        if sa and sa.total_score is not None and act.max_score:
            pct = round(sa.total_score / act.max_score * 100)
            on_time = None
            if act.end_time and sa.end_time:
                on_time = sa.end_time <= act.end_time
            activity_history.append({
                "name": act.activity_name,
                "type": act.activity_type.name if act.activity_type else "—",
                "score": sa.total_score,
                "max_score": act.max_score,
                "pct": pct,
                "submitted": sa.end_time,
                "on_time": on_time,
                "status": "graded",
            })
        else:
            activity_history.append({
                "name": act.activity_name,
                "type": act.activity_type.name if act.activity_type else "—",
                "score": None,
                "max_score": act.max_score,
                "pct": None,
                "submitted": None,
                "on_time": None,
                "status": "pending",
            })

    # Section 2: Risk breakdown
    risk_breakdown = {
        "grade_score": risk_info.get("grade_score", 0),
        "completion_score": risk_info.get("completion_score", 0),
        "attendance_score": risk_info.get("attendance_score", 0),
    }

    # Section 3: Module progress
    modules = Module.objects.filter(subject=subject).order_by("pk")
    progress_map = {
        sp.module_id: sp
        for sp in StudentProgress.objects.filter(student=student, module__in=modules)
    }
    module_progress = []
    for mod in modules:
        sp = progress_map.get(mod.pk)
        progress = float(sp.progress) if sp else 0
        if progress >= 100:
            status = "completed"
        elif progress > 0:
            status = "in_progress"
        else:
            status = "not_started"
        module_progress.append({"module": mod, "progress": progress, "status": status})

    # Section 4: XP & streak stats
    xp_stats = {
        "total_xp": gam.total_xp if gam else 0,
        "current_level": gam.current_level if gam else 1,
        "login_streak": gam.login_streak if gam else 0,
        "submission_streak": gam.submission_streak if gam else 0,
        "accuracy_streak": gam.accuracy_streak if gam else 0,
        "last_active": gam.last_active_date if gam else None,
    }

    # Section 5: Badges
    badges = StudentBadge.objects.filter(student=student).select_related("badge")

    # Section 6: Recognition history
    from gamification.teacher_models import TeacherRecognition
    recognitions = TeacherRecognition.objects.filter(
        teacher=request.user, student=student,
    ).order_by("-created_at")

    return render(request, "teacher/gamification/student_detail.html", {
        "subject": subject,
        "student": student,
        "semester": semester,
        "avg_score": avg_score,
        "total_xp": xp_stats["total_xp"],
        "login_streak": xp_stats["login_streak"],
        "risk_level": risk_level,
        "activity_history": activity_history,
        "risk_breakdown": risk_breakdown,
        "module_progress": module_progress,
        "xp_stats": xp_stats,
        "badges": badges,
        "recognitions": recognitions,
    })
