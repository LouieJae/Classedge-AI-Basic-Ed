import math
from django.db.models import F
from gamification.badges import evaluate_badges
from gamification.models import StudentGamification, XPTransaction


def award_xp(student, amount, reason, source_type, source_id=None):
    """Award XP to a student. Returns the XPTransaction or None if duplicate."""
    if source_id is not None:
        duplicate = XPTransaction.objects.filter(
            student=student, source_type=source_type, source_id=source_id,
        ).exists()
        if duplicate:
            return None

    tx = XPTransaction.objects.create(
        student=student, amount=amount, reason=reason,
        source_type=source_type, source_id=source_id,
    )

    gam, _ = StudentGamification.objects.get_or_create(student=student)
    StudentGamification.objects.filter(pk=gam.pk).update(total_xp=F("total_xp") + amount)
    gam.refresh_from_db()
    gam.current_level = max(1, math.floor(math.sqrt(gam.total_xp / 100)))
    gam.save(update_fields=["current_level"])

    evaluate_badges(student)

    return tx
