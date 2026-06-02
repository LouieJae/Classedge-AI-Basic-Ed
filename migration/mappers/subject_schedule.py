from migration.mappers.base import MapperResult, MissingFKError, register_mapper, require_fk
from migration.models import IDMap


@register_mapper("subject", "Schedule")
def map_schedule(payload: dict) -> MapperResult:
    """Schedule has two FKs:
    - subject  → subject.Subject  (REQUIRED, CASCADE — hard fail if missing)
    - semester → course.Semester  (nullable, CASCADE — soft NULL if missing)

    days_of_week comes as a list from the sim's serializer; MultiSelectField on
    the new side accepts either a list or a comma-joined string. We pass through
    as a comma-joined string for maximum compatibility.
    """
    subject_old = payload.get("subject")
    if not subject_old:
        raise MissingFKError("subject", "Subject", "(none)", field_name="subject")
    subject_new = require_fk("subject", "Subject", subject_old, field_name="subject")

    semester_old = payload.get("semester")

    days = payload.get("days_of_week") or []
    if isinstance(days, list):
        days_str = ",".join(days)
    else:
        days_str = str(days)

    return MapperResult(
        fields={
            "schedule_type": payload.get("schedule_type"),
            "sync_id": payload.get("sync_id"),
            "schedule_start_time": payload.get("schedule_start_time"),
            "schedule_end_time": payload.get("schedule_end_time"),
            "days_of_week": days_str,
            "is_active_semester": payload.get("is_active_semester", True),
            "subject_id": subject_new,
            "semester_id": IDMap.resolve("course", "Semester", semester_old) if semester_old else None,
        },
    )
