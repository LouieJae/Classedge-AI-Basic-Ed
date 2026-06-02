import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.llm import call_content_generator

_LLM_SETTINGS = {
    "CURRICULUM_PLANNER_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "CURRICULUM_PLANNER_DEFAULT_MODEL": "haiku",
}

_VALID_RESPONSE = json.dumps({
    "lesson_description": "This week covers the foundations of real numbers and integers. Students will learn about number classification, the number line, and basic properties of integers.\n\nLearning objectives:\n- Classify numbers as natural, whole, integer, rational\n- Plot integers on a number line\n- Compare and order integers",
    "quiz_questions": "1. Which of the following is NOT an integer?\nA) -3\nB) 0\nC) 2.5\nD) 7\nAnswer: C\n\n2. Arrange these numbers from least to greatest: 5, -2, 0, -7, 3\nAnswer: -7, -2, 0, 3, 5",
})

_CHAPTER_TEXTS = [
    {"number": 1, "title": "Real Numbers", "text": "Real numbers include all rational and irrational numbers..."},
    {"number": 2, "title": "Integers", "text": "Integers are whole numbers and their negatives..."},
]


def _mock_anthropic_response(text_content):
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@override_settings(**_LLM_SETTINGS)
class CallContentGeneratorTests(TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_valid_response_parsed(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        result = call_content_generator(
            chapter_texts=_CHAPTER_TEXTS,
            week_title="Foundations",
            week_description="Introduction to number systems",
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )
        self.assertIn("lesson_description", result)
        self.assertIn("quiz_questions", result)
        self.assertGreater(len(result["lesson_description"]), 0)
        self.assertGreater(len(result["quiz_questions"]), 0)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_prompt_includes_chapter_text(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        call_content_generator(
            chapter_texts=_CHAPTER_TEXTS,
            week_title="Foundations",
            week_description="Introduction",
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("Real Numbers", prompt_text)
        self.assertIn("rational and irrational", prompt_text)
        self.assertIn("Foundations", prompt_text)
        self.assertIn("30", prompt_text)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_invalid_json_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("not json")

        with self.assertRaises(ValueError):
            call_content_generator(
                chapter_texts=_CHAPTER_TEXTS,
                week_title="Foundations",
                week_description="Intro",
                session_count=30,
                minutes_per_session=90,
                model_key="haiku",
            )

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_missing_keys_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        bad_response = json.dumps({"lesson_description": "lesson only"})
        mock_client.messages.create.return_value = _mock_anthropic_response(bad_response)

        with self.assertRaises(ValueError):
            call_content_generator(
                chapter_texts=_CHAPTER_TEXTS,
                week_title="Foundations",
                week_description="Intro",
                session_count=30,
                minutes_per_session=90,
                model_key="haiku",
            )
