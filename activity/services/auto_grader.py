"""Server-side auto-grading for a single RetakeRecordDetail.

Mirrors the per-question grading logic in
`activity/views/answer_views.py:submit_answers` so that mobile-submitted
answers are scored consistently with web-submitted ones. Essay and Document
question types are returned as 0 because they require manual grading.
"""
import re

from django.db.models import Sum


def _normalize_text(text):
    if text is None:
        return ""
    return re.sub(r"\W+", "", str(text)).lower()


def grade_answer(question, student_answer):
    """Return the score (float) for a student's answer to one ActivityQuestion.

    Returns 0 for Essay/Document (manual grading), unanswered, or any
    parsing/validation problem.
    """
    if student_answer is None or student_answer == "":
        return 0

    qtype = question.quiz_type.name if question.quiz_type_id else ""

    if qtype in ("Essay", "Document"):
        return 0

    if qtype == "Multiple Choice":
        try:
            correct_index = int(question.correct_answer)
            choices = list(question.choices.order_by("id"))
            if 0 <= correct_index < len(choices):
                correct_choice_id = choices[correct_index].id
                if int(student_answer) == correct_choice_id:
                    return question.score
        except (ValueError, TypeError, AttributeError):
            return 0
        return 0

    if qtype == "Matching Type":
        try:
            correct_pairs = []
            for pair in (question.correct_answer or "").split(", "):
                if "->" in pair:
                    left, right = pair.split(" -> ")
                    correct_pairs.append(
                        (_normalize_text(left), _normalize_text(right))
                    )
            submitted = eval(student_answer) if isinstance(student_answer, str) else student_answer
            normalized = [
                (_normalize_text(l), _normalize_text(r)) for l, r in submitted
            ]
            return question.score if normalized == correct_pairs else 0
        except Exception:
            return 0

    if _normalize_text(student_answer) == _normalize_text(question.correct_answer):
        return question.score
    return 0


def grade_detail(detail):
    """Grade a RetakeRecordDetail in place and save its score.
    Returns the assigned score.
    """
    if detail.activity_question_id is None:
        return detail.score

    score = grade_answer(detail.activity_question, detail.student_answer)
    if detail.score != score:
        detail.score = score
        detail.save(update_fields=["score"])
    return score


def recompute_retake_record_score(retake_record):
    """Sum all RetakeRecordDetail.score for this record, apply any persisted
    late-submission penalty, then save. Reapplying the penalty here keeps it
    in sync when a teacher later edits per-question scores."""
    raw_total = (
        retake_record.retake_record_details.aggregate(v=Sum("score"))["v"] or 0
    )
    # Pull the latest persisted penalty so a stale in-memory object can't read 0.
    persisted_penalty = (
        type(retake_record).objects.filter(pk=retake_record.pk)
        .values_list("late_penalty_percent", flat=True)
        .first()
    )
    penalty = max(0, min(int(persisted_penalty or 0), 100))
    total = raw_total * (100 - penalty) / 100.0 if penalty else raw_total
    if retake_record.score != total:
        retake_record.score = total
        retake_record.save(update_fields=["score"])
    return total


def recompute_student_activity_total(student_activity):
    """Recompute StudentActivity.total_score per the activity's retake_method."""
    from django.db.models import Avg, Max

    method = student_activity.activity.retake_method
    qs = student_activity.retake_records.all()
    if not qs.exists():
        new_total = 0
    elif method == "highest":
        new_total = qs.aggregate(v=Max("score"))["v"] or 0
    elif method == "average":
        new_total = qs.aggregate(v=Avg("score"))["v"] or 0
    elif method == "first":
        first = qs.order_by("retake_time").first()
        new_total = first.score if first else 0
    else:
        latest = qs.order_by("-retake_time").first()
        new_total = latest.score if latest else 0

    submitted_count = qs.filter(status="submitted").count()

    update_fields = []
    if student_activity.total_score != new_total:
        student_activity.total_score = new_total
        update_fields.append("total_score")
    if student_activity.retake_count != submitted_count:
        student_activity.retake_count = submitted_count
        update_fields.append("retake_count")
    if update_fields:
        student_activity.save(update_fields=update_fields)
    return new_total
