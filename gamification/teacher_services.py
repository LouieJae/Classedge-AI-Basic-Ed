from django.db.models import F
from gamification.teacher_models import IPTransaction, TeacherGamification

RANK_THRESHOLDS = [
    (3500, "platinum", "Legend", "platinum_legend"),
    (2000, "gold", "Visionary", "gold_visionary"),
    (1200, "gold", "Luminary", "gold_luminary"),
    (600, "silver", "Architect", "silver_architect"),
    (300, "silver", "Catalyst", "silver_catalyst"),
    (100, "bronze", "Guide", "bronze_guide"),
    (0, "bronze", "Mentor", "bronze_mentor"),
]


def award_ip(teacher, amount, reason, source_type, source_id=None):
    """Award IP to a teacher. Returns IPTransaction or None if duplicate."""
    if source_id is not None:
        duplicate = IPTransaction.objects.filter(
            teacher=teacher, source_type=source_type, source_id=source_id,
        ).exists()
        if duplicate:
            return None

    tx = IPTransaction.objects.create(
        teacher=teacher, amount=amount, reason=reason,
        source_type=source_type, source_id=source_id,
    )

    gam, _ = TeacherGamification.objects.get_or_create(teacher=teacher)
    TeacherGamification.objects.filter(pk=gam.pk).update(total_ip=F("total_ip") + amount)
    gam.refresh_from_db()
    recalculate_rank(gam)

    from gamification.teacher_badges import evaluate_teacher_badges
    evaluate_teacher_badges(teacher)

    evaluate_teacher_challenges(teacher)

    return tx


def recalculate_rank(teacher_gam):
    """Map total_ip to rank tier + title using RANK_THRESHOLDS."""
    for threshold, tier, title, rank_code in RANK_THRESHOLDS:
        if teacher_gam.total_ip >= threshold:
            teacher_gam.current_rank = rank_code
            teacher_gam.rank_tier = tier
            teacher_gam.rank_title = title
            teacher_gam.save(update_fields=["current_rank", "rank_tier", "rank_title"])
            return


def next_rank_threshold(total_ip):
    """Return the IP needed for the next rank, or None if at max."""
    for threshold, _, _, _ in RANK_THRESHOLDS:
        if total_ip < threshold:
            return threshold
    return None


def evaluate_teacher_challenges(teacher):
    """Check all active challenges for the teacher. Complete any that hit target."""
    from gamification.teacher_models import TeacherChallengeProgress
    from django.utils import timezone as tz
    now = tz.now()

    active = TeacherChallengeProgress.objects.filter(
        teacher=teacher, completed_at__isnull=True,
    ).select_related("challenge")

    for progress in active:
        if progress.expires_at and progress.expires_at < now:
            continue
        if progress.current_value >= progress.target_value:
            progress.completed_at = now
            progress.save(update_fields=["completed_at"])
            IPTransaction.objects.create(
                teacher=teacher, amount=progress.challenge.ip_reward,
                reason=f"Challenge complete: {progress.challenge.name}",
                source_type="challenge_reward",
                source_id=progress.pk,
            )
            gam = TeacherGamification.objects.get(teacher=teacher)
            TeacherGamification.objects.filter(pk=gam.pk).update(
                total_ip=F("total_ip") + progress.challenge.ip_reward,
            )
            gam.refresh_from_db()
            recalculate_rank(gam)
