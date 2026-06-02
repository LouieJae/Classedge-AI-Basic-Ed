from gamification.teacher_models import (
    IPTransaction, TeacherBadge, TeacherBadgeDefinition,
    TeacherGamification, TeacherRecognition,
)
from gamification.models import StudentBadge


def evaluate_teacher_badges(teacher):
    """Check all active teacher badges the teacher hasn't earned yet."""
    earned_badge_ids = set(
        TeacherBadge.objects.filter(teacher=teacher).values_list("badge_id", flat=True)
    )
    candidates = TeacherBadgeDefinition.objects.filter(
        is_active=True,
    ).exclude(pk__in=earned_badge_ids)

    gam = TeacherGamification.objects.filter(teacher=teacher).first()
    if not gam:
        return

    for badge in candidates:
        criteria = badge.criteria_json
        if not criteria or "type" not in criteria:
            continue
        evaluator = TEACHER_EVALUATORS.get(criteria["type"])
        if evaluator and evaluator(teacher, gam, criteria):
            TeacherBadge.objects.create(teacher=teacher, badge=badge)


def _eval_teacher_ip_total(teacher, gam, criteria):
    return gam.total_ip >= criteria["threshold"]


def _eval_teacher_grading_count(teacher, gam, criteria):
    count = IPTransaction.objects.filter(
        teacher=teacher, source_type__in=["grading_ontime", "grading_late"],
    ).count()
    return count >= criteria["threshold"]


def _eval_teacher_recognition_count(teacher, gam, criteria):
    count = TeacherRecognition.objects.filter(teacher=teacher).count()
    return count >= criteria["threshold"]


def _eval_teacher_class_avg(teacher, gam, criteria):
    from subject.models.subject_model import Subject
    from activity.models.student_activity_model import StudentActivity
    from course.models.term_model import Term
    from course.models.semester_model import Semester
    from django.db.models import Q
    from django.utils import timezone

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()
    if not semester:
        return False

    terms = Term.objects.filter(semester=semester)
    teacher_subjects = Subject.objects.filter(
        Q(assign_teacher=teacher) | Q(substitute_teacher=teacher) | Q(collaborators=teacher),
    ).distinct()

    count_above = 0
    for subj in teacher_subjects:
        scores = StudentActivity.objects.filter(
            subject=subj, term__in=terms,
            activity__is_graded=True, activity__max_score__gt=0,
        ).select_related("activity")
        if not scores.exists():
            continue
        total_earned = sum(sa.total_score for sa in scores)
        total_possible = sum(sa.activity.max_score for sa in scores)
        avg = (total_earned / total_possible * 100) if total_possible > 0 else 0
        if avg >= criteria["threshold"]:
            count_above += 1

    return count_above >= criteria["count"]


def _eval_teacher_manual_awards(teacher, gam, criteria):
    count = StudentBadge.objects.filter(awarded_by=teacher).count()
    return count >= criteria["threshold"]


def _eval_teacher_star_avg(teacher, gam, criteria):
    from django.db.models import Avg, Count
    from gamification.teacher_models import TeacherRating

    stats = TeacherRating.objects.filter(teacher=teacher).aggregate(
        avg=Avg("stars"), count=Count("id"),
    )
    if not stats["count"] or stats["count"] < criteria["min_ratings"]:
        return False
    return stats["avg"] >= criteria["min_avg"]


def _eval_teacher_rank(teacher, gam, criteria):
    return gam.current_rank == criteria["rank"]


TEACHER_EVALUATORS = {
    "teacher_ip_total": _eval_teacher_ip_total,
    "teacher_grading_count": _eval_teacher_grading_count,
    "teacher_recognition_count": _eval_teacher_recognition_count,
    "teacher_class_avg": _eval_teacher_class_avg,
    "teacher_manual_awards": _eval_teacher_manual_awards,
    "teacher_star_avg": _eval_teacher_star_avg,
    "teacher_rank": _eval_teacher_rank,
}


# --- Progress Computers (0-100) ---

def _progress_teacher_ip_total(teacher, gam, criteria):
    return min(100, int(gam.total_ip / criteria["threshold"] * 100))


def _progress_teacher_grading_count(teacher, gam, criteria):
    count = IPTransaction.objects.filter(
        teacher=teacher, source_type__in=["grading_ontime", "grading_late"],
    ).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_recognition_count(teacher, gam, criteria):
    count = TeacherRecognition.objects.filter(teacher=teacher).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_class_avg(teacher, gam, criteria):
    return 0  # Requires live data, return 0 when no semester


def _progress_teacher_manual_awards(teacher, gam, criteria):
    count = StudentBadge.objects.filter(awarded_by=teacher).count()
    return min(100, int(count / criteria["threshold"] * 100))


def _progress_teacher_star_avg(teacher, gam, criteria):
    from django.db.models import Count
    from gamification.teacher_models import TeacherRating

    count = TeacherRating.objects.filter(teacher=teacher).count()
    return min(100, int(count / criteria["min_ratings"] * 100))


def _progress_teacher_rank(teacher, gam, criteria):
    from gamification.teacher_services import RANK_THRESHOLDS
    target_ip = 0
    for threshold, _, _, rank_code in RANK_THRESHOLDS:
        if rank_code == criteria["rank"]:
            target_ip = threshold
            break
    if target_ip == 0:
        return 100 if gam.current_rank == criteria["rank"] else 0
    return min(100, int(gam.total_ip / target_ip * 100))


TEACHER_PROGRESS_COMPUTERS = {
    "teacher_ip_total": _progress_teacher_ip_total,
    "teacher_grading_count": _progress_teacher_grading_count,
    "teacher_recognition_count": _progress_teacher_recognition_count,
    "teacher_class_avg": _progress_teacher_class_avg,
    "teacher_manual_awards": _progress_teacher_manual_awards,
    "teacher_star_avg": _progress_teacher_star_avg,
    "teacher_rank": _progress_teacher_rank,
}


def compute_teacher_badge_progress(teacher, badge):
    """Compute progress (0-100) for a badge the teacher hasn't earned yet."""
    criteria = badge.criteria_json
    if not criteria or "type" not in criteria:
        return 0
    computer = TEACHER_PROGRESS_COMPUTERS.get(criteria["type"])
    if not computer:
        return 0
    gam = TeacherGamification.objects.filter(teacher=teacher).first()
    if not gam:
        return 0
    return computer(teacher, gam, criteria)
