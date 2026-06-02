from migration.mappers._files import download_media
from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("activity", "Activity")
def map_activity(payload: dict) -> MapperResult:
    """Activity is the teacher-authored assessment shell. Three nullable FKs
    soft-resolved via IDMap. New-side-only fields default safely. Sim's
    max_score (PositiveIntegerField) coerces cleanly into new-side
    FloatField. activity_file_instruction (FileField) is skipped — file
    migration is a separate pipeline.

    M2M `additional_modules` is not migrated yet (Module not in scope yet).
    """
    return MapperResult(
        fields={
            "activity_name": payload["activity_name"],
            "start_time": payload.get("start_time"),
            "end_time": payload.get("end_time"),
            "show_score": payload.get("show_score", True),
            "remedial": payload.get("remedial", False),
            "max_retake": payload.get("max_retake", 0),
            "time_duration": payload.get("time_duration", 0),
            "max_score": payload.get("max_score"),
            "status": payload.get("status", True),
            "passing_score": payload.get("passing_score", 75.0),
            "passing_score_type": payload.get("passing_score_type", ""),
            "retake_method": payload.get("retake_method", ""),
            "activity_instruction": payload.get("activity_instruction"),
            "classroom_mode": payload.get("classroom_mode", False),
            "is_graded": payload.get("is_graded", True),
            "shuffle_questions": payload.get("shuffle_questions", False),
            "activity_file_instruction": download_media(payload.get("activity_file_instruction")) or "",
            "local_id": payload.get("local_id") or "",
            # New-side-only — safe defaults
            "allow_late_submission": False,
            "late_submission_days": 0,
            "late_submission_penalty_percent": 0,
            "allow_late": False,
            "central_source_id": None,
            # FKs
            "activity_type_id": IDMap.resolve("activity", "ActivityType", payload.get("activity_type")) if payload.get("activity_type") else None,
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
            "term_id": IDMap.resolve("course", "Term", payload.get("term")) if payload.get("term") else None,
        },
    )
