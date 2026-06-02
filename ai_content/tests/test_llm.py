import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from ai_content.llm import call_school_content_generator

_LLM_SETTINGS = {
    "AI_CONTENT_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "AI_CONTENT_DEFAULT_MODEL": "haiku",
}

_BOTH_RESPONSE = json.dumps({
    "lesson_description": "This lesson covers algebra basics including variables, constants, and expressions.",
    "quiz_questions": "1. What is a variable?\nA) A fixed number\nB) A symbol representing a value\nC) An equation\nD) A constant\nAnswer: B",
})

_MODULE_RESPONSE = json.dumps({
    "lesson_description": "This lesson covers algebra basics.",
})

_QUIZ_RESPONSE = json.dumps({
    "quiz_questions": "1. What is a variable?\nA) A fixed number\nB) A symbol\nAnswer: B",
})


def _mock_anthropic_response(text_content):
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@override_settings(**_LLM_SETTINGS)
class CallSchoolContentGeneratorTests(TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_both_content_type(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_BOTH_RESPONSE)

        result = call_school_content_generator(
            topic="Algebra Basics",
            objectives="Learn variables and expressions",
            content_type="both",
            reference_text="",
            model_key="haiku",
        )
        self.assertIn("lesson_description", result)
        self.assertIn("quiz_questions", result)
        self.assertGreater(len(result["lesson_description"]), 0)
        self.assertGreater(len(result["quiz_questions"]), 0)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_module_only(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_MODULE_RESPONSE)

        result = call_school_content_generator(
            topic="Algebra Basics",
            objectives="Learn variables",
            content_type="module",
            reference_text="",
            model_key="haiku",
        )
        self.assertIn("lesson_description", result)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_quiz_only(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_QUIZ_RESPONSE)

        result = call_school_content_generator(
            topic="Algebra Basics",
            objectives="Test understanding",
            content_type="quiz",
            reference_text="",
            model_key="haiku",
        )
        self.assertIn("quiz_questions", result)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_prompt_includes_reference_text(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_BOTH_RESPONSE)

        call_school_content_generator(
            topic="Algebra Basics",
            objectives="Learn variables",
            content_type="both",
            reference_text="Algebra is the study of mathematical symbols.",
            model_key="haiku",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("mathematical symbols", prompt_text)
        self.assertIn("Algebra Basics", prompt_text)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_invalid_json_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("not json")

        with self.assertRaises(ValueError):
            call_school_content_generator(
                topic="Test", objectives="Test",
                content_type="both", reference_text="", model_key="haiku",
            )
