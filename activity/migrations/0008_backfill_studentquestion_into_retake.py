"""Backfill legacy StudentQuestion rows into RetakeRecord(retake_number=1) +
RetakeRecordDetail. Idempotent: re-runs do nothing if a retake row already
exists for the (student, activity) pair.

Rules (mirrors plan 2026-05-18, section 'Backfill strategy'):
1. Group StudentQuestion by (student, activity).
2. Find or create StudentActivity for the pair (orphan SQ tolerated).
3. Find or create RetakeRecord(retake_number=1) for that StudentActivity.
   If a RetakeRecord already exists from the mobile flow, reuse it.
4. For each SQ row, upsert a RetakeRecordDetail keyed on
   (retake_record, activity_question). On conflict (mobile already wrote one),
   later submission_time wins.
5. Skip rows whose activity_question is null (legacy participation entries)
   and rows where activity_question.activity_id is missing.
6. After all rows ingested, recompute retake_record.score and
   student_activity.total_score using the canonical helpers.
"""
import logging

from django.db import migrations


logger = logging.getLogger(__name__)


def _recompute_record(rr, RetakeRecordDetail):
    rr.score = sum(
        d.score or 0
        for d in RetakeRecordDetail.objects.filter(retake_record=rr)
    )
    rr.save(update_fields=["score"])


def _recompute_sa(sa, RetakeRecord):
    method = getattr(sa.activity, "retake_method", "latest") if sa.activity_id else "latest"
    records = RetakeRecord.objects.filter(student_activity=sa)
    if not records.exists():
        return
    if method == "highest":
        chosen = records.order_by("-score", "-retake_time").first()
    elif method == "first":
        chosen = records.order_by("retake_time").first()
    elif method == "average":
        total = sum(r.score or 0 for r in records)
        sa.total_score = total / records.count() if records.count() else 0
        sa.save(update_fields=["total_score"])
        return
    else:
        chosen = records.order_by("-retake_time").first()
    sa.total_score = chosen.score or 0
    sa.save(update_fields=["total_score"])


def forwards(apps, schema_editor):
    StudentQuestion = apps.get_model("activity", "StudentQuestion")
    StudentActivity = apps.get_model("activity", "StudentActivity")
    RetakeRecord = apps.get_model("activity", "RetakeRecord")
    RetakeRecordDetail = apps.get_model("activity", "RetakeRecordDetail")

    if not StudentQuestion.objects.exists():
        return

    pairs = (
        StudentQuestion.objects
        .exclude(activity__isnull=True)
        .values_list("student_id", "activity_id")
        .distinct()
    )

    skipped = 0
    for student_id, activity_id in pairs:
        sq_rows = list(
            StudentQuestion.objects.filter(
                student_id=student_id,
                activity_id=activity_id,
                activity_question__isnull=False,
            ).order_by("submission_time", "id")
        )
        if not sq_rows:
            continue

        sa, _ = StudentActivity.objects.get_or_create(
            student_id=student_id,
            activity_id=activity_id,
        )

        rr = (
            RetakeRecord.objects
            .filter(student_activity=sa, retake_number=1)
            .first()
        )
        if rr is None:
            latest_submission = max(
                (sq.submission_time for sq in sq_rows if sq.submission_time),
                default=None,
            )
            rr = RetakeRecord.objects.create(
                student_activity=sa,
                student_id=student_id,
                activity_id=activity_id,
                retake_number=1,
                status="submitted",
                retake_time=latest_submission or None,
            )

        for sq in sq_rows:
            if not sq.activity_question_id:
                skipped += 1
                continue
            existing = RetakeRecordDetail.objects.filter(
                retake_record=rr,
                activity_question_id=sq.activity_question_id,
            ).first()
            if existing:
                if (sq.submission_time and existing.submission_time
                        and sq.submission_time > existing.submission_time):
                    existing.student_answer = sq.student_answer
                    existing.uploaded_file = sq.uploaded_file
                    existing.score = sq.score or 0
                    existing.submission_time = sq.submission_time
                    existing.save(update_fields=[
                        "student_answer", "uploaded_file", "score", "submission_time"
                    ])
                continue
            RetakeRecordDetail.objects.create(
                retake_record=rr,
                student_id=student_id,
                activity_question_id=sq.activity_question_id,
                student_answer=sq.student_answer,
                uploaded_file=sq.uploaded_file or None,
                score=sq.score or 0,
                submission_time=sq.submission_time,
            )

        _recompute_record(rr, RetakeRecordDetail)
        _recompute_sa(sa, RetakeRecord)

    if skipped:
        logger.warning(
            "Backfill skipped %s StudentQuestion rows with NULL activity_question "
            "(legacy participation entries; covered by future participation port).",
            skipped,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("activity", "0007_swap_retake_pk"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=migrations.RunPython.noop),
    ]
