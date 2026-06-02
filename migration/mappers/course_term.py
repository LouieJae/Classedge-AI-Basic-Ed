from migration.models import IDMap

from .base import MapperResult, register_mapper


@register_mapper("course", "Term")
def map_term(payload: dict) -> MapperResult:
    """Term has two nullable FKs:
    - semester  → course.Semester
    - created_by → accounts.CustomUser

    Resolved softly: if the sim row references a target that hasn't been
    migrated yet (no IDMap entry), the FK is set to NULL rather than blocking
    the whole row. The Term itself still imports.
    """
    semester_old = payload.get("semester")
    created_by_old = payload.get("created_by")
    return MapperResult(
        fields={
            "term_name": payload["term_name"],
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "semester_id": IDMap.resolve("course", "Semester", semester_old) if semester_old else None,
            "created_by_id": IDMap.resolve("accounts", "CustomUser", created_by_old) if created_by_old else None,
        },
    )
