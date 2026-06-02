from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("activity", "RetakeRecord")
def map_retake_record(payload: dict) -> MapperResult:
    """Retake attempt rolled up. 3 nullable FKs soft-resolved. retake_time is
    auto_now_add on the new side — preserved via post_save_updates so the
    original chronology is kept. choice_order is new-side-only — default [].
    """
    retake_time = payload.get("retake_time")
    return MapperResult(
        fields={
            "retake_number": payload.get("retake_number", 0),
            "score": payload.get("score", 0.0),
            "duration": payload.get("duration", 0),
            "question_order": payload.get("question_order", []),
            "choice_order": [],  # new-side-only field
            "last_index": payload.get("last_index", 0),
            "status": payload.get("status", ""),
            "started_at": payload.get("started_at"),
            "will_end_at": payload.get("will_end_at"),
            "last_heartbeat_at": payload.get("last_heartbeat_at"),
            "total_elapsed_seconds": payload.get("total_elapsed_seconds", 0),
            "local_id": payload.get("local_id") or "",
            "student_activity_id": IDMap.resolve("activity", "StudentActivity", payload.get("student_activity")) if payload.get("student_activity") else None,
            "student_id": IDMap.resolve("accounts", "CustomUser", payload.get("student")) if payload.get("student") else None,
            "activity_id": IDMap.resolve("activity", "Activity", payload.get("activity")) if payload.get("activity") else None,
        },
        post_save_updates={"retake_time": retake_time} if retake_time else {},
    )


@register_mapper("activity", "RetakeRecordDetail")
def map_retake_record_detail(payload: dict) -> MapperResult:
    """Individual question result inside a retake attempt. 3 nullable FKs
    soft-resolved. uploaded_file skipped.
    """
    return MapperResult(
        fields={
            "student_answer": payload.get("student_answer"),
            "score": payload.get("score", 0.0),
            "submission_time": payload.get("submission_time"),
            "local_id": payload.get("local_id") or "",
            "retake_record_id": IDMap.resolve("activity", "RetakeRecord", payload.get("retake_record")) if payload.get("retake_record") else None,
            "student_id": IDMap.resolve("accounts", "CustomUser", payload.get("student")) if payload.get("student") else None,
            "activity_question_id": IDMap.resolve("activity", "ActivityQuestion", payload.get("activity_question")) if payload.get("activity_question") else None,
        },
    )


@register_mapper("activity", "ScoreChangeLog")
def map_score_change_log(payload: dict) -> MapperResult:
    """Append-only audit row. change_date is auto_now_add on the new side —
    preserved via post_save_updates so the audit trail's chronology stays
    intact (addendum §5 #2). FKs are non-nullable on both sides — if
    student_activity or changed_by aren't migrated, the row will fail with
    db_error.
    """
    change_date = payload.get("change_date")
    return MapperResult(
        fields={
            "previous_score": payload.get("previous_score", 0.0),
            "new_score": payload.get("new_score", 0.0),
            "reason": "",  # new-side-only field
            "student_activity_id": IDMap.resolve("activity", "StudentActivity", payload.get("student_activity")) if payload.get("student_activity") else None,
            "changed_by_id": IDMap.resolve("accounts", "CustomUser", payload.get("changed_by")) if payload.get("changed_by") else None,
        },
        post_save_updates={"change_date": change_date} if change_date else {},
    )
