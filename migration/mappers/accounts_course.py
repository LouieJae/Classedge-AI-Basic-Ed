from .base import MapperResult, register_mapper


@register_mapper("accounts", "Course")
def map_course(payload: dict) -> MapperResult:
    """Sim Course has only (name, short_name); new side adds an optional
    department FK. Sim doesn't track department-per-course so we leave it NULL.
    """
    return MapperResult(
        fields={
            "name": payload.get("name"),
            "short_name": payload.get("short_name"),
        },
    )
