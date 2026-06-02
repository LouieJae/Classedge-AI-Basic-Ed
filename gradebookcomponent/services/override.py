"""[Classedge LMS] Override service — writes ScoreChangeLog atomically."""
from django.db import transaction

from activity.models.score_log_models import ScoreChangeLog


def apply_override(student_activity, new_score, reason, changed_by):
    """[Classedge LMS] Persist a score override and an audit log row atomically."""
    with transaction.atomic():
        old = student_activity.total_score
        student_activity.total_score = new_score
        student_activity.save(update_fields=["total_score"])
        ScoreChangeLog.objects.create(
            student_activity=student_activity,
            changed_by=changed_by,
            previous_score=old,
            new_score=new_score,
            reason=reason,
        )
