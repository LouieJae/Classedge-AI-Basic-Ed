from migration.mappers.base import MapperResult, MissingFKError, register_mapper, require_fk
from migration.models import IDMap


@register_mapper("gradebookcomponent", "TransmutationRule")
def map_transmutation_rule(payload: dict) -> MapperResult:
    """No FKs — pure config row. Straight passthrough."""
    return MapperResult(
        fields={
            "transmutation_table_name": payload.get("transmutation_table_name", ""),
            "min_grade": payload.get("min_grade", 0),
            "max_grade": payload.get("max_grade", 0),
            "transmuted_value": payload.get("transmuted_value", ""),
        },
    )


@register_mapper("gradebookcomponent", "GradeBookComponents")
def map_gradebook_components(payload: dict) -> MapperResult:
    """Top-level gradebook config row. All 4 FKs nullable → soft-resolved."""
    return MapperResult(
        fields={
            "gradebook_name": payload.get("gradebook_name"),
            "gradebook_category": payload.get("gradebook_category", ""),
            "percentage": payload.get("percentage", 0),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "teacher_id": IDMap.resolve("accounts", "CustomUser", payload.get("teacher")) if payload.get("teacher") else None,
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
            "activity_type_id": IDMap.resolve("activity", "ActivityType", payload.get("activity_type")) if payload.get("activity_type") else None,
            "term_id": IDMap.resolve("course", "Term", payload.get("term")) if payload.get("term") else None,
        },
    )


@register_mapper("gradebookcomponent", "ActivityTypePercentage")
def map_activity_type_percentage(payload: dict) -> MapperResult:
    """Child of GradeBookComponents. Both FKs REQUIRED (non-nullable on new
    side) — use require_fk so misses surface as missing_fk, not db_error.
    """
    gbc_old = payload.get("gradebook_component")
    at_old = payload.get("activity_type")
    if not gbc_old:
        raise MissingFKError("gradebookcomponent", "GradeBookComponents", "(none)", field_name="gradebook_component")
    if not at_old:
        raise MissingFKError("activity", "ActivityType", "(none)", field_name="activity_type")
    return MapperResult(
        fields={
            "percentage": payload.get("percentage", 0),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "gradebook_component_id": require_fk("gradebookcomponent", "GradeBookComponents", gbc_old, field_name="gradebook_component"),
            "activity_type_id": require_fk("activity", "ActivityType", at_old, field_name="activity_type"),
        },
    )


@register_mapper("gradebookcomponent", "TermGradeBookComponents")
def map_term_gradebook_components(payload: dict) -> MapperResult:
    """Term-scoped gradebook weighting. teacher nullable, term REQUIRED."""
    term_old = payload.get("term")
    if not term_old:
        raise MissingFKError("course", "Term", "(none)", field_name="term")
    return MapperResult(
        fields={
            "percentage": payload.get("percentage", 0),
            "base_grade": payload.get("base_grade", 0),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "teacher_id": IDMap.resolve("accounts", "CustomUser", payload.get("teacher")) if payload.get("teacher") else None,
            "term_id": require_fk("course", "Term", term_old, field_name="term"),
        },
    )


@register_mapper("gradebookcomponent", "GradeVisibilitySettings")
def map_grade_visibility_settings(payload: dict) -> MapperResult:
    """Per teacher × subject × term visibility flag. teacher + subject REQUIRED,
    term nullable.
    """
    teacher_old = payload.get("teacher")
    subject_old = payload.get("subject")
    if not teacher_old:
        raise MissingFKError("accounts", "CustomUser", "(none)", field_name="teacher")
    if not subject_old:
        raise MissingFKError("subject", "Subject", "(none)", field_name="subject")
    return MapperResult(
        fields={
            "is_visible": payload.get("is_visible", False),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "teacher_id": require_fk("accounts", "CustomUser", teacher_old, field_name="teacher"),
            "subject_id": require_fk("subject", "Subject", subject_old, field_name="subject"),
            "term_id": IDMap.resolve("course", "Term", payload.get("term")) if payload.get("term") else None,
        },
    )
