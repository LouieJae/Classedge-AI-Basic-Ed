from .base import MapperResult, register_mapper


@register_mapper("roles", "Role")
def map_role(payload: dict) -> MapperResult:
    perms = [(p["app_label"], p["codename"]) for p in payload.get("permissions", [])]
    return MapperResult(
        fields={
            "name": payload["name"],
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
        },
        m2m_resolutions={"permissions": perms},
        natural_key={"name__iexact": payload["name"]},
    )
