from .base import MapperResult, register_mapper


@register_mapper("course", "Semester")
def map_semester(payload: dict) -> MapperResult:
    """Sim Semester matches new side except for the new (nullable) department FK
    which sim doesn't track. Leave department=NULL.
    """
    return MapperResult(
        fields={
            "semester_name": payload["semester_name"],
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "end_semester": payload.get("end_semester", False),
            "passing_grade": payload.get("passing_grade", 75),
            "grade_calculation_method": payload.get("grade_calculation_method", "averaging"),
            "create_at": payload.get("create_at"),
        },
    )
