from migration.mappers.base import MapperResult, register_mapper


@register_mapper("activity", "QuizType")
def map_quiz_type(payload: dict) -> MapperResult:
    """QuizType is a lookup. We copy whatever non-id fields exist in the payload
    verbatim (sim and new agree). Pure straight passthrough.
    """
    fields = {k: v for k, v in payload.items() if k != "id"}
    return MapperResult(fields=fields)
