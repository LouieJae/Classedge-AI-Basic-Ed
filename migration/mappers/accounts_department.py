from .base import MapperResult, register_mapper


@register_mapper("accounts", "Department")
def map_department(payload: dict) -> MapperResult:
    """Identical schema on both sides — straight field copy."""
    return MapperResult(
        fields={
            "name": payload["name"],
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
        },
    )
