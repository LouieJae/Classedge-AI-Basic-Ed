from migration.mappers.base import MapperResult, register_mapper


@register_mapper("logs", "UserActivityLog")
def map_user_activity_log(payload: dict) -> MapperResult:
    """The new LMS dropped logs.UserActivityLog. We archive the raw sim row
    into migration.LegacyAuditLog so the audit history is preserved without
    re-introducing the dropped table.

    No FK resolution — payload is stored verbatim as JSON. The source PK keys
    IDMap so re-runs stay idempotent.
    """
    return MapperResult(
        fields={
            "source_app": "logs",
            "source_model": "UserActivityLog",
            "source_pk": str(payload.get("id", "")),
            "occurred_at": payload.get("created_at"),
            "payload": payload,
        },
        target_app="migration",
        target_model="LegacyAuditLog",
    )
