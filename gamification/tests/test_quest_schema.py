from django.test import TestCase
from gamification.quest_schema import validate_quest_set, QuestSchemaError, validate_single_quest


VALID_QUIZ = {
    "kind": "quiz", "title": "Q1", "body": "what?",
    "payload": {"options": ["a", "b", "c", "d"], "correct_index": 0},
    "source_chunk": "..."
}


class QuestSchemaTests(TestCase):
    def test_valid_passes(self):
        validate_quest_set({"quests": [VALID_QUIZ]}, expected_n=1)

    def test_wrong_n_fails(self):
        with self.assertRaises(QuestSchemaError):
            validate_quest_set({"quests": [VALID_QUIZ]}, expected_n=2)

    def test_duplicate_titles_fail(self):
        with self.assertRaises(QuestSchemaError):
            validate_quest_set({"quests": [VALID_QUIZ, dict(VALID_QUIZ)]}, expected_n=2)

    def test_quiz_missing_correct_index_fails(self):
        bad = {**VALID_QUIZ, "payload": {"options": ["a", "b", "c", "d"]}}
        with self.assertRaises(QuestSchemaError):
            validate_single_quest(bad)

    def test_unknown_kind_fails(self):
        bad = {**VALID_QUIZ, "kind": "weird"}
        with self.assertRaises(QuestSchemaError):
            validate_single_quest(bad)
