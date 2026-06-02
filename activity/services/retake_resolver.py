"""Selects the canonical RetakeRecordDetail set for a StudentActivity.

Used by exports, gradebook readers, and any read path that needs per-question
answers (not per-attempt). The choice of which attempt is canonical follows
the activity's `retake_method`:

  * highest  -> details of the highest-scoring attempt (ties broken by latest)
  * latest   -> details of the most recent attempt
  * first    -> details of the earliest attempt
  * average  -> details of the latest attempt (with WARNING; per-detail averaging
                is not meaningful for answer text/files)

Mirrors the attempt-selection logic in
`activity.services.auto_grader.recompute_student_activity_total` so reads and
score rollups stay consistent.
"""
import logging

from activity.models import RetakeRecordDetail

logger = logging.getLogger(__name__)


def select_canonical_details(student_activity):
    method = student_activity.activity.retake_method
    records = student_activity.retake_records.all()
    if not records.exists():
        return RetakeRecordDetail.objects.none()

    if method == "highest":
        chosen = records.order_by("-score", "-retake_time").first()
    elif method == "first":
        chosen = records.order_by("retake_time").first()
    elif method == "average":
        logger.warning(
            "select_canonical_details called with retake_method='average' "
            "for student_activity=%s; per-detail averaging is undefined, "
            "returning latest attempt's details",
            student_activity.pk,
        )
        chosen = records.order_by("-retake_time").first()
    else:
        chosen = records.order_by("-retake_time").first()

    return chosen.retake_record_details.select_related("activity_question")
