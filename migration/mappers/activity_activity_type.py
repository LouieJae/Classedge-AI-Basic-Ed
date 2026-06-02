from migration.mappers.base import MapperResult, register_mapper


@register_mapper("activity", "ActivityType")
def map_activity_type(payload: dict) -> MapperResult:
    """ActivityType is a tiny lookup table (just `name`). Identical schema both sides."""
    return MapperResult(
        fields={"name": payload["name"]},
    )
