from datetime import date, timedelta

from activity.models.student_activity_model import StudentActivity
from gamification.models import BadgeDefinition, CodingStats, StudentBadge, StudentGamification
from gamification.side_activity_models import SideActivity, SideActivityAttempt


def evaluate_badges(student):
    """Check all active badges the student hasn't earned yet and award any whose criteria are met."""
    earned_badge_ids = set(
        StudentBadge.objects.filter(student=student).values_list("badge_id", flat=True)
    )
    candidates = BadgeDefinition.objects.filter(
        is_active=True, target_role="student",
    ).exclude(pk__in=earned_badge_ids)

    gam = StudentGamification.objects.filter(student=student).first()
    if not gam:
        return

    for badge in candidates:
        criteria = badge.criteria_json
        if not criteria or "type" not in criteria:
            continue
        evaluator = EVALUATORS.get(criteria["type"])
        if evaluator and evaluator(student, gam, criteria):
            StudentBadge.objects.create(student=student, badge=badge)


def _eval_xp_total(student, gam, criteria):
    return gam.total_xp >= criteria["threshold"]


def _eval_streak(student, gam, criteria):
    streak_field = criteria["streak"]
    current = getattr(gam, f"{streak_field}_streak", 0)
    return current >= criteria["threshold"]


def _eval_level(student, gam, criteria):
    return gam.current_level >= criteria["threshold"]


def _eval_badges_earned(student, gam, criteria):
    count = StudentBadge.objects.filter(student=student).count()
    return count >= criteria["threshold"]


def _eval_activity_score(student, gam, criteria):
    min_pct = criteria["min_pct"] / 100.0
    count_needed = criteria["count"]
    qualifying = 0
    for sa in StudentActivity.objects.filter(
        student=student, activity__is_graded=True, activity__max_score__gt=0,
    ).select_related("activity"):
        if sa.total_score / sa.activity.max_score >= min_pct:
            qualifying += 1
            if qualifying >= count_needed:
                return True
    return False


def _eval_top_scorer(student, gam, criteria):
    """Award when the student holds the top score in ``threshold`` graded
    activities within a single subject. Ties on the top score all count.
    """
    from django.db.models import Max

    threshold = criteria.get("threshold", 5)
    qs = StudentActivity.objects.filter(
        student=student,
        activity__is_graded=True,
        activity__max_score__gt=0,
        total_score__gt=0,
    ).select_related("activity")

    per_subject = {}
    for sa in qs:
        top = StudentActivity.objects.filter(
            activity=sa.activity,
        ).aggregate(m=Max("total_score"))["m"]
        if top is None or sa.total_score < top:
            continue
        subj_id = sa.activity.subject_id
        per_subject[subj_id] = per_subject.get(subj_id, 0) + 1
        if per_subject[subj_id] >= threshold:
            return True
    return False


def _eval_side_activity_count(student, gam, criteria):
    """Count distinct completed side activities >= threshold."""
    count = (
        SideActivityAttempt.objects.filter(student=student, completed_at__isnull=False)
        .values("side_activity_id")
        .distinct()
        .count()
    )
    return count >= criteria.get("threshold", 0)


def _eval_side_activity_count_type(student, gam, criteria):
    """Count completed attempts for a specific sub_type >= threshold."""
    sub_type = criteria.get("sub_type")
    count = SideActivityAttempt.objects.filter(
        student=student,
        completed_at__isnull=False,
        side_activity__sub_type=sub_type,
    ).count()
    return count >= criteria.get("threshold", 0)


def _eval_side_activity_speed(student, gam, criteria):
    """Count completed attempts for sub_type under max_seconds >= count."""
    sub_type = criteria.get("sub_type")
    max_seconds = criteria.get("max_seconds", 0)
    count = SideActivityAttempt.objects.filter(
        student=student,
        completed_at__isnull=False,
        side_activity__sub_type=sub_type,
        time_taken_seconds__lt=max_seconds,
    ).count()
    return count >= criteria.get("count", 0)


def _eval_side_activity_typing_wpm(student, gam, criteria):
    """Check if any typing attempt has wpm >= min_wpm in details_json."""
    min_wpm = criteria.get("min_wpm", 0)
    for attempt in SideActivityAttempt.objects.filter(
        student=student,
        completed_at__isnull=False,
        side_activity__sub_type="typing_drill",
    ):
        wpm = attempt.details_json.get("wpm", 0) if isinstance(attempt.details_json, dict) else 0
        if wpm >= min_wpm:
            return True
    return False


def _eval_side_activity_all_in_subject(student, gam, criteria):
    """Check if all activities in any one subject are completed."""
    completed_ids = set(
        SideActivityAttempt.objects.filter(student=student, completed_at__isnull=False)
        .values_list("side_activity_id", flat=True)
    )
    if not completed_ids:
        return False
    # Check each subject that has side activities
    from django.db.models import Count
    subjects_with_activities = (
        SideActivity.objects.filter(is_active=True)
        .values("subject_id")
        .annotate(total=Count("id"))
    )
    for entry in subjects_with_activities:
        subject_id = entry["subject_id"]
        total = entry["total"]
        if total == 0:
            continue
        subject_activity_ids = set(
            SideActivity.objects.filter(subject_id=subject_id, is_active=True)
            .values_list("id", flat=True)
        )
        if subject_activity_ids.issubset(completed_ids):
            return True
    return False


def _eval_side_activity_streak(student, gam, criteria):
    """Count consecutive days (ending today or yesterday) with ≥1 completed side activity."""
    threshold = criteria.get("threshold", 1)
    completed_dates = set(
        SideActivityAttempt.objects.filter(
            student=student, completed_at__isnull=False,
        ).values_list("completed_at__date", flat=True)
    )
    if not completed_dates:
        return False
    streak = 0
    check = date.today()
    while check in completed_dates:
        streak += 1
        check -= timedelta(days=1)
    if streak == 0:
        # Allow streak ending yesterday
        check = date.today() - timedelta(days=1)
        while check in completed_dates:
            streak += 1
            check -= timedelta(days=1)
    return streak >= threshold


def _eval_side_activity_early(student, gam, criteria):
    """Count activities completed in under 60% of estimated time >= threshold."""
    threshold = criteria.get("threshold", 1)
    count = 0
    for attempt in SideActivityAttempt.objects.filter(
        student=student,
        completed_at__isnull=False,
        time_taken_seconds__isnull=False,
    ).select_related("side_activity"):
        limit = attempt.side_activity.estimated_minutes * 60 * 0.6
        if limit > 0 and attempt.time_taken_seconds < limit:
            count += 1
    return count >= threshold


def _eval_side_activity_daily(student, gam, criteria):
    """Count completed daily_challenge attempts >= threshold."""
    threshold = criteria.get("threshold", 1)
    count = SideActivityAttempt.objects.filter(
        student=student,
        completed_at__isnull=False,
        side_activity__sub_type="daily_challenge",
    ).count()
    return count >= threshold


def _eval_side_activity_perfect_type(student, gam, criteria):
    """Count completed attempts of a sub_type with score >= min_score >= threshold."""
    threshold = criteria.get("threshold", 1)
    sub_type = criteria.get("sub_type")
    min_score = criteria.get("min_score", 100)
    count = SideActivityAttempt.objects.filter(
        student=student,
        completed_at__isnull=False,
        side_activity__sub_type=sub_type,
        score__gte=min_score,
    ).count()
    return count >= threshold


def _eval_coding_first(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return (stats.total_submissions + stats.total_katas) >= 1


def _eval_coding_perfect_count(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.perfect_submissions >= criteria["threshold"]


def _eval_coding_kata_count(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.total_katas >= criteria["threshold"]


def _eval_coding_polyglot(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return len(stats.languages_used) >= 2


def _eval_coding_fast_perfect(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.fast_perfects >= criteria["threshold"]


def _eval_coding_streak(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return stats.best_streak >= criteria["threshold"]


def _eval_coding_total(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return (stats.total_submissions + stats.total_katas) >= criteria["threshold"]


def _eval_coding_legend(student, gam, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return False
    return (
        stats.perfect_submissions >= criteria["perfect_threshold"]
        and stats.total_katas >= criteria["kata_threshold"]
    )


EVALUATORS = {
    "xp_total": _eval_xp_total,
    "streak": _eval_streak,
    "level": _eval_level,
    "badges_earned": _eval_badges_earned,
    "activity_score": _eval_activity_score,
    "top_scorer": _eval_top_scorer,
    "side_activity_count": _eval_side_activity_count,
    "side_activity_count_type": _eval_side_activity_count_type,
    "side_activity_speed": _eval_side_activity_speed,
    "side_activity_typing_wpm": _eval_side_activity_typing_wpm,
    "side_activity_all_in_subject": _eval_side_activity_all_in_subject,
    "side_activity_streak": _eval_side_activity_streak,
    "side_activity_early": _eval_side_activity_early,
    "side_activity_daily": _eval_side_activity_daily,
    "side_activity_perfect_type": _eval_side_activity_perfect_type,
    "coding_first": _eval_coding_first,
    "coding_perfect_count": _eval_coding_perfect_count,
    "coding_kata_count": _eval_coding_kata_count,
    "coding_polyglot": _eval_coding_polyglot,
    "coding_fast_perfect": _eval_coding_fast_perfect,
    "coding_streak": _eval_coding_streak,
    "coding_total": _eval_coding_total,
    "coding_legend": _eval_coding_legend,
}


# ---------------------------------------------------------------------------
# Badge Progress Computers — return 0-100 int
# ---------------------------------------------------------------------------

def _progress_coding_stat(student, field, threshold):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, int(getattr(stats, field, 0) / threshold * 100))


def _progress_coding_first(student):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return 100 if (stats.total_submissions + stats.total_katas) >= 1 else 0


def _progress_coding_total(student, threshold):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, int((stats.total_submissions + stats.total_katas) / threshold * 100))


def _progress_coding_polyglot(student):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    return min(100, len(stats.languages_used) * 50)


def _progress_coding_legend(student, criteria):
    stats = CodingStats.objects.filter(student=student).first()
    if not stats:
        return 0
    p1 = min(50, int(stats.perfect_submissions / criteria["perfect_threshold"] * 50))
    p2 = min(50, int(stats.total_katas / criteria["kata_threshold"] * 50))
    return p1 + p2


def _progress_top_scorer(student, criteria):
    from django.db.models import Max

    threshold = max(1, criteria.get("threshold", 5))
    qs = StudentActivity.objects.filter(
        student=student,
        activity__is_graded=True,
        activity__max_score__gt=0,
        total_score__gt=0,
    ).select_related("activity")

    per_subject = {}
    best = 0
    for sa in qs:
        top = StudentActivity.objects.filter(
            activity=sa.activity,
        ).aggregate(m=Max("total_score"))["m"]
        if top is None or sa.total_score < top:
            continue
        subj_id = sa.activity.subject_id
        per_subject[subj_id] = per_subject.get(subj_id, 0) + 1
        if per_subject[subj_id] > best:
            best = per_subject[subj_id]
    return min(100, int(best / threshold * 100))


def _progress_badges_earned(student, criteria):
    count = StudentBadge.objects.filter(student=student).count()
    return min(100, int(count / criteria["threshold"] * 100))


PROGRESS_COMPUTERS = {
    "xp_total": lambda s, g, c: min(100, int(g.total_xp / c["threshold"] * 100)),
    "streak": lambda s, g, c: min(100, int(getattr(g, f'{c["streak"]}_streak', 0) / c["threshold"] * 100)),
    "level": lambda s, g, c: min(100, int(g.current_level / c["threshold"] * 100)),
    "badges_earned": lambda s, g, c: _progress_badges_earned(s, c),
    "top_scorer": lambda s, g, c: _progress_top_scorer(s, c),
    "coding_first": lambda s, g, c: _progress_coding_first(s),
    "coding_perfect_count": lambda s, g, c: _progress_coding_stat(s, "perfect_submissions", c["threshold"]),
    "coding_kata_count": lambda s, g, c: _progress_coding_stat(s, "total_katas", c["threshold"]),
    "coding_polyglot": lambda s, g, c: _progress_coding_polyglot(s),
    "coding_fast_perfect": lambda s, g, c: _progress_coding_stat(s, "fast_perfects", c["threshold"]),
    "coding_streak": lambda s, g, c: _progress_coding_stat(s, "best_streak", c["threshold"]),
    "coding_total": lambda s, g, c: _progress_coding_total(s, c["threshold"]),
    "coding_legend": lambda s, g, c: _progress_coding_legend(s, c),
}


def compute_badge_progress(student, badge):
    """Compute progress (0-100) for a badge the student hasn't earned yet."""
    criteria = badge.criteria_json
    if not criteria or "type" not in criteria:
        return 0
    computer = PROGRESS_COMPUTERS.get(criteria["type"])
    if not computer:
        return 0
    gam = StudentGamification.objects.filter(student=student).first()
    if not gam:
        return 0
    return computer(student, gam, criteria)
