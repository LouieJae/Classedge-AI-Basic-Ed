from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("classroom", "Screenshot")
def map_screenshot(payload: dict) -> MapperResult:
    """Screenshot rows preserve the (already-skipped) image FK and timestamp.
    teacher_attendance FK soft-resolved. ImageField intentionally skipped —
    file content migration is a separate pipeline. `timestamp` is auto_now_add
    on the new side so the original sim timestamp is replaced with today.
    """
    ta_old = payload.get("teacher_attendance")
    return MapperResult(
        fields={
            "teacher_attendance_id": IDMap.resolve("classroom", "Teacher_Attendance", ta_old) if ta_old else None,
        },
    )
