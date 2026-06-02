"""[Classedge LMS] Validate AI/uploaded quest JSON against a strict schema."""
from jsonschema import validate, ValidationError


class QuestSchemaError(Exception):
    pass


_QUIZ_PAYLOAD = {
    "type": "object",
    "required": ["options", "correct_index"],
    "properties": {
        "options": {"type": "array", "minItems": 2, "maxItems": 6, "items": {"type": "string"}},
        "correct_index": {"type": "integer", "minimum": 0},
    },
}
_READING_PAYLOAD = {
    "type": "object",
    "required": ["reading", "question", "expected_keywords"],
    "properties": {
        "reading": {"type": "string"},
        "question": {"type": "string"},
        "expected_keywords": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    },
}
_TASK_PAYLOAD = {
    "type": "object",
    "required": ["rubric", "self_check"],
    "properties": {"rubric": {"type": "string"}, "self_check": {"type": "boolean"}},
}

_QUEST = {
    "type": "object",
    "required": ["kind", "title", "body", "payload"],
    "properties": {
        "kind": {"enum": ["quiz", "reading_check", "task"]},
        "title": {"type": "string", "maxLength": 200, "minLength": 1},
        "body": {"type": "string", "minLength": 1},
        "payload": {"type": "object"},
        "source_chunk": {"type": "string"},
        "counts_toward_grade": {"type": "boolean"},
    },
}


def validate_single_quest(q: dict) -> None:
    try:
        validate(q, _QUEST)
        if q["kind"] == "quiz":
            validate(q["payload"], _QUIZ_PAYLOAD)
            opts = q["payload"]["options"]
            if q["payload"]["correct_index"] >= len(opts):
                raise QuestSchemaError("quiz.correct_index out of range")
        elif q["kind"] == "reading_check":
            validate(q["payload"], _READING_PAYLOAD)
        elif q["kind"] == "task":
            validate(q["payload"], _TASK_PAYLOAD)
    except ValidationError as e:
        raise QuestSchemaError(str(e))


def validate_quest_set(data: dict, expected_n: int) -> None:
    if not isinstance(data, dict) or "quests" not in data:
        raise QuestSchemaError("Top-level must be {'quests': [...]}.")
    quests = data["quests"]
    if not isinstance(quests, list):
        raise QuestSchemaError("'quests' must be a list.")
    if len(quests) != expected_n:
        raise QuestSchemaError(f"Expected {expected_n} quests, got {len(quests)}.")
    titles = set()
    for q in quests:
        validate_single_quest(q)
        if q["title"] in titles:
            raise QuestSchemaError(f"Duplicate title: {q['title']}")
        titles.add(q["title"])
