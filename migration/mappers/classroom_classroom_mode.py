from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("classroom", "Classroom_mode")
def map_classroom_mode(payload: dict) -> MapperResult:
    """Classroom_mode is a OneToOne with Subject (nullable). Soft-resolve.

    Note: the OneToOne uniqueness means re-running on an existing row migrates
    via IDMap match → updates the same row. If the IDMap is wiped, the writer
    creates a new row, but the unique constraint on subject_id will fail with
    db_error if a Classroom_mode already exists for that subject.
    """
    subject_old = payload.get("subject")
    return MapperResult(
        fields={
            "is_classroom_mode": payload.get("is_classroom_mode", False),
            "subject_id": IDMap.resolve("subject", "Subject", subject_old) if subject_old else None,
        },
    )
