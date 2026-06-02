import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.llm import call_curriculum_planner

_LLM_SETTINGS = {
    "CURRICULUM_PLANNER_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
        "sonnet": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "CURRICULUM_PLANNER_DEFAULT_MODEL": "haiku",
}

_VALID_RESPONSE = json.dumps([
    {"week": 1, "chapters": [1, 2], "title": "Foundations", "description": "Intro to real numbers"},
    {"week": 2, "chapters": [3, 4], "title": "Operations", "description": "Basic operations"},
    {"week": 3, "chapters": [5], "title": "Applications", "description": "Word problems"},
])

_CHAPTERS = [
    {"number": 1, "title": "Real Numbers", "start_page": 1, "end_page": 20},
    {"number": 2, "title": "Integers", "start_page": 21, "end_page": 40},
    {"number": 3, "title": "Addition", "start_page": 41, "end_page": 60},
    {"number": 4, "title": "Subtraction", "start_page": 61, "end_page": 80},
    {"number": 5, "title": "Word Problems", "start_page": 81, "end_page": 100},
]


def _mock_anthropic_response(text_content):
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@override_settings(**_LLM_SETTINGS)
class CallCurriculumPlannerTests(TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_valid_response_parsed(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        result = call_curriculum_planner(
            chapters=_CHAPTERS,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["week"], 1)
        self.assertEqual(result[0]["chapters"], [1, 2])
        self.assertIn("title", result[0])
        self.assertIn("description", result[0])

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_prompt_includes_chapter_info(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        call_curriculum_planner(
            chapters=_CHAPTERS,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("Real Numbers", prompt_text)
        self.assertIn("30", prompt_text)
        self.assertIn("90", prompt_text)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_uses_correct_model(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        call_curriculum_planner(
            chapters=_CHAPTERS,
            session_count=30,
            minutes_per_session=90,
            model_key="sonnet",
        )

        call_args = mock_client.messages.create.call_args
        model_used = call_args.kwargs.get("model") or call_args[1].get("model")
        self.assertEqual(model_used, "claude-sonnet-4-6")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_invalid_json_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("not json at all")

        with self.assertRaises(ValueError):
            call_curriculum_planner(
                chapters=_CHAPTERS,
                session_count=30,
                minutes_per_session=90,
                model_key="haiku",
            )

    def test_unknown_model_key_raises(self):
        with self.assertRaises(KeyError):
            call_curriculum_planner(
                chapters=_CHAPTERS,
                session_count=30,
                minutes_per_session=90,
                model_key="nonexistent",
            )
