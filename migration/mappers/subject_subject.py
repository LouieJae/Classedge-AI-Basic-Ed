from migration.models import IDMap

from ._files import download_media
from .base import MapperResult, register_mapper


@register_mapper("subject", "Subject")
def map_subject(payload: dict) -> MapperResult:
    """Subject has two nullable FKs to CustomUser (teacher / substitute).
    Both soft-resolved — missing IDMap entry sets the FK to NULL, the subject
    row still migrates so it's visible in the new LMS.

    subject_photo (ImageField) is skipped — image file migration is a separate
    pipeline. The path string from sim wouldn't point to a real file on the new
    side anyway.

    sim's subject_type ("Lec"/"Lab") is not present on the new side — skipped.
    """
    teacher_old = payload.get("assign_teacher")
    substitute_old = payload.get("substitute_teacher")
    return MapperResult(
        fields={
            "subject_name": payload["subject_name"],
            "subject_descriptive_title": payload.get("subject_descriptive_title"),
            "subject_short_name": payload.get("subject_short_name"),
            "subject_code": payload.get("subject_code"),
            "subject_description": payload.get("subject_description"),
            "subject_sync_id": payload.get("subject_sync_id"),
            "room_number": payload.get("room_number"),
            "duration": payload.get("duration"),
            "industry_partners": payload.get("industry_partners"),
            "highlight": payload.get("highlight"),
            "country": payload.get("country"),
            "issued_by": payload.get("issued_by"),
            "issued_on": payload.get("issued_on"),
            "issued_under": payload.get("issued_under"),
            "allow_substitute_teacher": payload.get("allow_substitute_teacher", False),
            "self_attendance_enabled": payload.get("self_attendance_enabled", False),
            "unit": payload.get("unit", 3),
            "max_number_of_enrollees": payload.get("max_number_of_enrollees"),
            "number_of_enrollees": payload.get("number_of_enrollees", 0),
            "is_coil": payload.get("is_coil", False),
            "is_cte": payload.get("is_cte", False),
            "is_hali": payload.get("is_hali", False),
            "status": payload.get("status"),
            "subject_photo": download_media(payload.get("subject_photo")) or "",
            "assign_teacher_id": IDMap.resolve("accounts", "CustomUser", teacher_old) if teacher_old else None,
            "substitute_teacher_id": IDMap.resolve("accounts", "CustomUser", substitute_old) if substitute_old else None,
        },
    )
