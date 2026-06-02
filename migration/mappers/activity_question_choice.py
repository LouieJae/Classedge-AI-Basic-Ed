from migration.mappers._files import download_media
from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("activity", "QuestionChoice")
def map_question_choice(payload: dict) -> MapperResult:
    """QuestionChoice belongs to an ActivityQuestion (FK nullable).
    Soft-resolved subject + question FKs. choice_image (ImageField) skipped.
    is_left_side preserved (used for Matching-type questions).

    Per the assessment addendum integrity rule: a choice's link to its question
    must be preserved exactly — relying on IDMap. The actual correctness check
    is done via ActivityQuestion.correct_answer text matching, not a boolean
    flag on the choice, so there's no is_correct field to round-trip.
    """
    return MapperResult(
        fields={
            "choice_text": payload.get("choice_text", ""),
            "is_left_side": payload.get("is_left_side", False),
            "choice_image": download_media(payload.get("choice_image")) or "",
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
            "question_id": IDMap.resolve("activity", "ActivityQuestion", payload.get("question")) if payload.get("question") else None,
        },
    )
