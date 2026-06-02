from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.shortcuts import render
from django.utils import timezone

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term
from gamification.models import StudentGamification
from module.models.module import Module
from module.models.student_progress import StudentProgress
from gamification.teacher_models import (
    TeacherBadge, TeacherBadgeDefinition, TeacherChallenge,
    TeacherChallengeProgress, TeacherGamification, TeacherRating,
)
from gamification.teacher_services import RANK_THRESHOLDS, next_rank_threshold
from subject.models.subject_model import Subject
from subject.models.schedule_model import Schedule


def teacher_dashboard(request):
    user = request.user
    now = timezone.localtime(timezone.now())

    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 18:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()

    # Teacher's subjects this semester
    teacher_subjects = Subject.objects.filter(
        Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user),
    ).distinct()

    terms = Term.objects.filter(semester=semester) if semester else Term.objects.none()

    # ── Today's schedule (HIGHLIGHT on the dashboard) ─────────────
    # Pulls every Schedule whose `days_of_week` includes today's short
    # weekday code (Mon/Tue/...) for any subject the teacher is on.
    # Each item gets a status (now/upcoming/done) and a CTA URL to
    # the classroom-mode entry for that subject.
    today_short = now.strftime("%a")  # e.g. "Mon"
    schedules_today_qs = (
        Schedule.objects
        .filter(subject__in=teacher_subjects, days_of_week__icontains=today_short)
        .select_related("subject")
    )
    if semester:
        schedules_today_qs = schedules_today_qs.filter(
            Q(semester=semester) | Q(semester__isnull=True),
        )

    enrolled_per_subject = {}
    if semester:
        enrolled_per_subject = dict(
            SubjectEnrollment.objects
            .filter(semester=semester, status="enrolled", subject__in=teacher_subjects)
            .values("subject_id")
            .annotate(c=Count("student", distinct=True))
            .values_list("subject_id", "c")
        )

    schedule_today = []
    now_t = now.time()
    for sch in schedules_today_qs:
        start_t = sch.schedule_start_time
        end_t = sch.schedule_end_time
        if start_t and end_t and start_t <= now_t <= end_t:
            status = "now"
        elif start_t and start_t > now_t:
            status = "upcoming"
        else:
            status = "done"
        schedule_today.append({
            "schedule": sch,
            "subject": sch.subject,
            "start_time": start_t,
            "end_time": end_t,
            "room": sch.subject.room_number or "",
            "students": enrolled_per_subject.get(sch.subject_id, 0),
            "status": status,
        })
    # Sort: ongoing first, then upcoming by start time, then done by start time.
    status_order = {"now": 0, "upcoming": 1, "done": 2}
    schedule_today.sort(key=lambda s: (status_order[s["status"]], s["start_time"] or datetime.min.time()))

    # ── Aggregate stats ────────────────────────────────────────
    total_students = 0
    if semester:
        total_students = SubjectEnrollment.objects.filter(
            semester=semester, status="enrolled", subject__in=teacher_subjects,
        ).values("student").distinct().count()

    active_subjects = teacher_subjects.count()

    # Overall class average
    overall_avg = _calc_overall_avg(teacher_subjects, terms)

    # At-risk counts
    at_risk_high, at_risk_medium = _calc_at_risk_counts(teacher_subjects, semester)

    # Completion rate
    completion_pct, submitted_count, total_possible = _calc_completion_rate(
        teacher_subjects, terms, semester,
    )

    # Active streaks
    streak_count, streak_pct = _calc_streak_stats(teacher_subjects, semester)

    # ── Metrics ────────────────────────────────────────────────
    metrics = [
        {
            "label": "Class Average",
            "icon": "📊",
            "value": f"{overall_avg:.0f}",
            "unit": "%",
            "caption": f"across {active_subjects} subject{'s' if active_subjects != 1 else ''}",
            "caption_class": "positive" if overall_avg >= 75 else "warn",
        },
        {
            "label": "At-Risk",
            "icon": "⚠️",
            "value": str(at_risk_high + at_risk_medium),
            "unit": "",
            "caption": f"{at_risk_high} high \u00b7 {at_risk_medium} medium",
            "caption_class": "warn" if at_risk_high > 0 else "positive",
        },
        {
            "label": "Completion",
            "icon": "✅",
            "value": f"{completion_pct:.0f}",
            "unit": "%",
            "caption": f"{submitted_count}/{total_possible} submissions",
            "caption_class": "positive" if completion_pct >= 80 else "warn",
        },
        {
            "label": "Active Streaks",
            "icon": "🔥",
            "value": str(streak_count),
            "unit": "",
            "caption": f"{streak_pct:.0f}% of students",
            "caption_class": "positive" if streak_pct >= 50 else "warn",
        },
    ]

    # ── Subject cards ──────────────────────────────────────────
    subjects = []
    for subj in teacher_subjects:
        avg = _calc_subject_avg(subj, terms)
        ungraded = _calc_ungraded(subj, terms, semester)
        module_pct = _calc_module_progress(subj, semester)

        if avg >= 85 and ungraded == 0:
            card_class = "excellent"
        elif ungraded > 5 or avg < 70:
            card_class = "warn"
        else:
            card_class = ""

        subjects.append({
            "subject": subj,
            "avg": round(avg, 1),
            "ungraded": ungraded,
            "module_pct": round(module_pct),
            "card_class": card_class,
        })

    # ── Spotlight (top improvers) ──────────────────────────────
    spotlight = _calc_spotlight(teacher_subjects, terms, semester)

    # ── Needs grading (submitted but not scored, excluding Participation) ──
    needs_grading_qs = (
        StudentActivity.objects
        .filter(
            subject__in=teacher_subjects,
            retake_count__gte=1,
            total_score__isnull=True,
        )
        .exclude(activity__activity_type__name__iexact="Participation")
        .select_related("activity", "student", "subject", "activity__activity_type")
        .order_by("-end_time")
    )
    needs_grading_count = needs_grading_qs.count()
    needs_grading_items = list(needs_grading_qs[:5])

    # ── Closing soon (assessments ending in the next 7 days) ───
    week_ahead = now + timedelta(days=7)
    closing_soon = list(
        Activity.objects
        .filter(
            subject__in=teacher_subjects,
            status=True,
            end_time__gte=now,
            end_time__lte=week_ahead,
        )
        .exclude(activity_type__name__iexact="Participation")
        .select_related("subject", "activity_type")
        .order_by("end_time")[:5]
    )

    # ── Teacher Gamification ──────────────────────────────────
    teacher_gam = TeacherGamification.objects.filter(teacher=user).first()
    total_ip = teacher_gam.total_ip if teacher_gam else 0
    rank_tier = teacher_gam.rank_tier if teacher_gam else "bronze"
    rank_title = teacher_gam.rank_title if teacher_gam else "Mentor"
    current_rank = teacher_gam.current_rank if teacher_gam else "bronze_mentor"
    next_thresh = next_rank_threshold(total_ip)
    ip_progress_pct = 0
    if next_thresh:
        current_threshold = 0
        for t, _, _, rc in RANK_THRESHOLDS:
            if rc == current_rank:
                current_threshold = t
                break
        range_size = next_thresh - current_threshold
        ip_progress_pct = int((total_ip - current_threshold) / range_size * 100) if range_size > 0 else 100
    else:
        ip_progress_pct = 100

    from django.db.models import Avg as AvgAgg
    rating_stats = TeacherRating.objects.filter(teacher=user).aggregate(
        avg=AvgAgg("stars"), count=Count("id"),
    )
    star_avg = round(rating_stats["avg"], 1) if rating_stats["avg"] else 0
    star_count = rating_stats["count"] or 0

    challenges_qs = TeacherChallengeProgress.objects.filter(
        teacher=user, completed_at__isnull=True,
    ).select_related("challenge").order_by("expires_at")[:3]
    challenges = []
    for cp in challenges_qs:
        days_left = None
        if cp.expires_at:
            delta = cp.expires_at - timezone.now()
            days_left = max(0, delta.days)
        progress_pct = int(cp.current_value / cp.target_value * 100) if cp.target_value > 0 else 0
        challenges.append({
            "name": cp.challenge.name,
            "description": cp.challenge.description,
            "current": cp.current_value,
            "target": cp.target_value,
            "progress_pct": min(100, progress_pct),
            "days_left": days_left,
            "ip_reward": cp.challenge.ip_reward,
            "challenge_type": cp.challenge.challenge_type,
        })

    teacher_badges = list(
        TeacherBadge.objects.filter(teacher=user)
        .select_related("badge").order_by("-earned_at")
    )
    teacher_badges_total = TeacherBadgeDefinition.objects.filter(is_active=True).count()

    milestones = TeacherChallenge.objects.filter(is_active=True, challenge_type="milestone")
    for ms in milestones:
        if not TeacherChallengeProgress.objects.filter(teacher=user, challenge=ms).exists():
            target = ms.criteria_json.get("threshold", ms.criteria_json.get("count", 1))
            TeacherChallengeProgress.objects.create(
                teacher=user, challenge=ms, current_value=0, target_value=target,
            )

    return render(request, "teacher/gamification/teacher_dashboard.html", {
        "greeting": greeting,
        "user_name": user.first_name or user.username,
        "total_students": total_students,
        "active_subjects": active_subjects,
        "overall_avg": round(overall_avg, 1),
        "metrics": metrics,
        "subjects": subjects,
        "spotlight": spotlight,
        "semester": semester,
        "total_ip": total_ip,
        "rank_tier": rank_tier,
        "rank_title": rank_title,
        "current_rank": current_rank,
        "next_threshold": next_thresh,
        "ip_progress_pct": ip_progress_pct,
        "star_avg": star_avg,
        "star_count": star_count,
        "challenges": challenges,
        "teacher_badges": teacher_badges,
        "teacher_badges_total": teacher_badges_total,
        "schedule_today": schedule_today,
        "needs_grading_count": needs_grading_count,
        "needs_grading_items": needs_grading_items,
        "closing_soon": closing_soon,
        "now_dt": now,
    })


# ── Helper functions ───────────────────────────────────────────


def _calc_overall_avg(teacher_subjects, terms):
    if not terms.exists():
        return 0.0
    scores = StudentActivity.objects.filter(
        subject__in=teacher_subjects, term__in=terms,
        activity__is_graded=True, activity__max_score__gt=0,
    ).select_related("activity")
    if not scores.exists():
        return 0.0
    total_earned = sum(sa.total_score for sa in scores)
    total_possible = sum(sa.activity.max_score for sa in scores)
    return (total_earned / total_possible * 100) if total_possible > 0 else 0.0


def _calc_at_risk_counts(teacher_subjects, semester):
    if not semester:
        return 0, 0
    high_threshold = getattr(settings, "AT_RISK_HIGH_THRESHOLD", 40)
    medium_threshold = getattr(settings, "AT_RISK_MEDIUM_THRESHOLD", 65)
    high = 0
    medium = 0
    try:
        from at_risk.calculator import calculate_risk_scores
        for subj in teacher_subjects:
            results = calculate_risk_scores(subj, semester)
            for r in results:
                if r["risk_level"] == "high":
                    high += 1
                elif r["risk_level"] == "medium":
                    medium += 1
    except Exception:
        pass
    return high, medium


def _calc_completion_rate(teacher_subjects, terms, semester):
    if not semester or not terms.exists():
        return 0.0, 0, 0
    graded_activities = Activity.objects.filter(
        subject__in=teacher_subjects, term__in=terms, is_graded=True,
    )
    total_activities = graded_activities.count()
    if total_activities == 0:
        return 0.0, 0, 0

    enrolled_count = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject__in=teacher_subjects,
    ).values("student").distinct().count()

    total_possible = total_activities * enrolled_count
    if total_possible == 0:
        return 0.0, 0, 0

    submitted = StudentActivity.objects.filter(
        activity__in=graded_activities,
    ).count()

    return (submitted / total_possible * 100), submitted, total_possible


def _calc_streak_stats(teacher_subjects, semester):
    if not semester:
        return 0, 0.0
    enrolled_ids = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject__in=teacher_subjects,
    ).values_list("student_id", flat=True).distinct()

    total = len(set(enrolled_ids))
    if total == 0:
        return 0, 0.0

    with_streak = StudentGamification.objects.filter(
        student_id__in=enrolled_ids, login_streak__gt=0,
    ).count()

    return with_streak, (with_streak / total * 100)


def _calc_subject_avg(subject, terms):
    if not terms.exists():
        return 0.0
    scores = StudentActivity.objects.filter(
        subject=subject, term__in=terms,
        activity__is_graded=True, activity__max_score__gt=0,
    ).select_related("activity")
    if not scores.exists():
        return 0.0
    total_earned = sum(sa.total_score for sa in scores)
    total_possible = sum(sa.activity.max_score for sa in scores)
    return (total_earned / total_possible * 100) if total_possible > 0 else 0.0


def _calc_ungraded(subject, terms, semester):
    if not semester or not terms.exists():
        return 0
    graded_activities = Activity.objects.filter(
        subject=subject, term__in=terms, is_graded=True,
    )
    enrolled_count = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject=subject,
    ).count()

    ungraded = 0
    for act in graded_activities:
        submitted = StudentActivity.objects.filter(activity=act).count()
        if submitted < enrolled_count:
            ungraded += 1
    return ungraded


def _calc_module_progress(subject, semester):
    if not semester:
        return 0.0
    modules = Module.objects.filter(subject=subject)
    total_modules = modules.count()
    if total_modules == 0:
        return 0.0

    enrolled_ids = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject=subject,
    ).values_list("student_id", flat=True)

    if not enrolled_ids:
        return 0.0

    completed = StudentProgress.objects.filter(
        student_id__in=enrolled_ids, module__in=modules, completed=True,
    ).count()

    total_possible = total_modules * len(set(enrolled_ids))
    return (completed / total_possible * 100) if total_possible > 0 else 0.0


def _calc_spotlight(teacher_subjects, terms, semester):
    if not semester or not terms.exists():
        return []

    enrolled_ids = SubjectEnrollment.objects.filter(
        semester=semester, status="enrolled", subject__in=teacher_subjects,
    ).values_list("student_id", flat=True).distinct()

    improvers = []
    for student_id in set(enrolled_ids):
        scores = list(
            StudentActivity.objects.filter(
                student_id=student_id,
                subject__in=teacher_subjects,
                term__in=terms,
                activity__is_graded=True,
                activity__max_score__gt=0,
            ).select_related("activity").order_by("-activity__end_time", "-pk")[:10]
        )
        if len(scores) < 4:
            continue

        mid = len(scores) // 2
        recent = scores[:mid]
        older = scores[mid:]

        def avg_pct(sa_list):
            earned = sum(s.total_score for s in sa_list)
            possible = sum(s.activity.max_score for s in sa_list)
            return (earned / possible * 100) if possible > 0 else 0

        recent_avg = avg_pct(recent)
        older_avg = avg_pct(older)
        delta = recent_avg - older_avg

        if delta > 0:
            from accounts.models import CustomUser
            student = CustomUser.objects.filter(pk=student_id).first()
            if student:
                name = student.get_full_name() or student.username
                initial = (student.first_name or student.username)[0].upper()
                improvers.append({
                    "name": name,
                    "initial": initial,
                    "old_avg": round(older_avg),
                    "new_avg": round(recent_avg),
                    "delta": round(delta),
                    "student_id": student_id,
                })

    improvers.sort(key=lambda x: -x["delta"])
    return improvers[:3]
