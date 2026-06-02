from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("course", "SubjectEnrollment")
def map_subject_enrollment(payload: dict) -> MapperResult:
    """Enrollment row linking student × subject × semester. All three FKs are
    nullable (PROTECT on_delete on the new side) — soft-resolve via IDMap so a
    row referencing un-migrated targets still imports with NULL FKs.

    Note: `enrollment_date` has auto_now_add=True on the new side, so the
    incoming value is ignored by Django on save. The new row gets today's date.
    The original date is preserved in `student_name` only implicitly via the
    sim's row order.
    """
    return MapperResult(
        fields={
            "can_view_grade": payload.get("can_view_grade", False),
            "status": payload.get("status", "enrolled"),
            "drop_date": payload.get("drop_date"),
            "administrative_drop_date": payload.get("administrative_drop_date"),
            "is_active_semester": payload.get("is_active_semester", True),
            "student_name": payload.get("student_name"),
            "student_id": IDMap.resolve("accounts", "CustomUser", payload.get("student")) if payload.get("student") else None,
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
            "semester_id": IDMap.resolve("course", "Semester", payload.get("semester")) if payload.get("semester") else None,
        },
    )
