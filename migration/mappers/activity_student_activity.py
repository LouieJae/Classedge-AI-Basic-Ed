from migration.mappers._files import download_media
from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("activity", "StudentActivity")
def map_student_activity(payload: dict) -> MapperResult:
    """Student-side enrollment to an Activity. Holds the aggregate score for
    that student × activity attempt.

    Per the assessment addendum: total_score must equal sum of related
    StudentQuestion scores. We copy sim's total_score verbatim — we trust the
    invariant held on sim. If StudentQuestion scores later drift, the
    `recompute_student_activity_total` helper in activity/tasks.py can repair.

    All 4 FKs soft-resolved. File submissions skipped. new-side `feedback`
    defaults to empty.
    """
    return MapperResult(
        fields={
            "retake_count": payload.get("retake_count", 0),
            "start_time": payload.get("start_time"),
            "end_time": payload.get("end_time"),
            "total_score": payload.get("total_score", 0.0),
            "is_editable": payload.get("is_editable", True),
            "attendance_mode": payload.get("attendance_mode"),
            "feedback": "",  # new-side-only field, sim doesn't track
            "local_id": payload.get("local_id") or "",
            "activity_local_id": payload.get("activity_local_id"),
            "student_id": IDMap.resolve("accounts", "CustomUser", payload.get("student")) if payload.get("student") else None,
            "activity_id": IDMap.resolve("activity", "Activity", payload.get("activity")) if payload.get("activity") else None,
            "term_id": IDMap.resolve("course", "Term", payload.get("term")) if payload.get("term") else None,
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
        },
    )


@register_mapper("activity", "StudentQuestion")
def map_student_question(payload: dict) -> MapperResult:
    """Per-question student answer + score. Three soft-resolved FKs.

    CI grep guard prevents `StudentQuestion.objects.create(...)` outside an
    allowlist of production writers. The `migration/` app is intentionally
    NOT in the guard's watched paths, so this writer is the legitimate path
    for migrated rows. Uploaded files skipped.
    """
    return MapperResult(
        fields={
            "score": payload.get("score", 0.0),
            "student_answer": payload.get("student_answer"),
            "status": payload.get("status", False),
            "submission_time": payload.get("submission_time"),
            "is_participation": payload.get("is_participation", False),
            "is_graded": payload.get("is_graded"),
            "uploaded_file": download_media(payload.get("uploaded_file")) or "",
            "student_id": IDMap.resolve("accounts", "CustomUser", payload.get("student")) if payload.get("student") else None,
            "activity_question_id": IDMap.resolve("activity", "ActivityQuestion", payload.get("activity_question")) if payload.get("activity_question") else None,
            "activity_id": IDMap.resolve("activity", "Activity", payload.get("activity")) if payload.get("activity") else None,
        },
    )
