from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("activity", "Rubrics")
def map_rubrics(payload: dict) -> MapperResult:
    """Rubric definitions per teacher per subject. Both FKs soft-resolved."""
    return MapperResult(
        fields={
            "rubric_name": payload.get("rubric_name"),
            "description": payload.get("description"),
            "teacher_id": IDMap.resolve("accounts", "CustomUser", payload.get("teacher")) if payload.get("teacher") else None,
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
        },
    )


@register_mapper("activity", "RubricsItem")
def map_rubrics_item(payload: dict) -> MapperResult:
    """Individual rubric criterion attached to a question + parent rubric.

    Per the assessment addendum: rubrics must migrate before any StudentActivity
    that references rubric-based grading. Both FKs soft-resolved so a partial
    migration doesn't block — but a StudentQuestion later expecting a real
    rubric item will fail if its parent is missing.
    """
    return MapperResult(
        fields={
            "point": payload.get("point", 0),
            "activity_question_id": IDMap.resolve("activity", "ActivityQuestion", payload.get("activity_question")) if payload.get("activity_question") else None,
            "rubric_id": IDMap.resolve("activity", "Rubrics", payload.get("rubric")) if payload.get("rubric") else None,
        },
    )
