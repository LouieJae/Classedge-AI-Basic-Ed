from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("classroom", "Teacher_Attendance")
def map_teacher_attendance(payload: dict) -> MapperResult:
    """Teacher_Attendance has two nullable FKs (Subject CASCADE, CustomUser PROTECT).
    Both soft-resolved — un-migrated targets leave the FK NULL.
    """
    subject_old = payload.get("subject")
    teacher_old = payload.get("teacher")
    return MapperResult(
        fields={
            "time_started": payload.get("time_started"),
            "time_ended": payload.get("time_ended"),
            "manual_ended": payload.get("manual_ended", False),
            "is_active": payload.get("is_active", False),
            "celery_task_id": payload.get("celery_task_id"),
            "subject_id": IDMap.resolve("subject", "Subject", subject_old) if subject_old else None,
            "teacher_id": IDMap.resolve("accounts", "CustomUser", teacher_old) if teacher_old else None,
        },
    )
