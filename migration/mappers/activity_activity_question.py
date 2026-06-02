from migration.mappers._files import download_media
from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


@register_mapper("activity", "ActivityQuestion")
def map_activity_question(payload: dict) -> MapperResult:
    """ActivityQuestion belongs to an Activity (FK nullable). Three soft-resolved FKs:
    activity, subject, quiz_type. question_instruction (FileField) skipped.
    """
    return MapperResult(
        fields={
            "question_text": payload.get("question_text", ""),
            "correct_answer": payload.get("correct_answer", ""),
            "score": payload.get("score"),
            "question_instruction": download_media(payload.get("question_instruction")) or "",
            "activity_id": IDMap.resolve("activity", "Activity", payload.get("activity")) if payload.get("activity") else None,
            "subject_id": IDMap.resolve("subject", "Subject", payload.get("subject")) if payload.get("subject") else None,
            "quiz_type_id": IDMap.resolve("activity", "QuizType", payload.get("quiz_type")) if payload.get("quiz_type") else None,
        },
        # Legacy rows occasionally have empty question_text / correct_answer
        # (e.g. drafts). The new-side model declares TextField() with no
        # blank=True, so full_clean would reject them. Allow blanks on ingest.
        clean_exclude=["question_text", "correct_answer"],
    )
