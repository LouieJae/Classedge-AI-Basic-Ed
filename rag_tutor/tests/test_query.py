from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from rag_tutor.models import ContentChunk, ChatMessage
from rag_tutor.query import ask_question
from ai_content.tests.test_models import _create_test_user, _create_subject

_RAG_SETTINGS = {
    "RAG_TUTOR_EMBEDDING_MODEL": "text-embedding-3-small",
    "RAG_TUTOR_LLM_MODEL": "claude-haiku-4-5-20251001",
    "RAG_TUTOR_TOP_K": 5,
    "RAG_TUTOR_RELEVANCE_THRESHOLD": 0.8,
}


@override_settings(**_RAG_SETTINGS)
class AskQuestionTests(TestCase):
    def setUp(self):
        self.subject = _create_subject()
        self.student = _create_test_user(username="student_q")
        self.chunk = ContentChunk.objects.create(
            subject=self.subject,
            source_type="module",
            source_id=1,
            source_title="Algebra Basics",
            chunk_index=0,
            text="Variables are symbols that represent unknown values in mathematics.",
            embedding=[0.1] * 1536,
        )

    @patch("rag_tutor.query.anthropic.Anthropic")
    @patch("rag_tutor.query.embed_texts")
    def test_returns_grounded_answer(self, mock_embed, MockAnthropic):
        mock_embed.return_value = [[0.1] * 1536]

        mock_block = MagicMock()
        mock_block.text = "A variable is a symbol that represents an unknown value. (Source: Algebra Basics)"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        result = ask_question(self.subject.pk, "What is a variable?", self.student)

        self.assertIn("answer", result)
        self.assertIn("variable", result["answer"].lower())
        self.assertTrue(result["had_relevant_chunks"])
        self.assertGreater(len(result["sources"]), 0)

        self.assertEqual(ChatMessage.objects.count(), 1)
        msg = ChatMessage.objects.first()
        self.assertEqual(msg.question, "What is a variable?")
        self.assertTrue(msg.had_relevant_chunks)

    @patch("rag_tutor.query.anthropic.Anthropic")
    @patch("rag_tutor.query.embed_texts")
    def test_no_chunks_returns_fallback(self, mock_embed, MockAnthropic):
        ContentChunk.objects.all().delete()
        mock_embed.return_value = [[0.9] * 1536]

        mock_block = MagicMock()
        mock_block.text = "Your course materials don't cover this topic yet."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        result = ask_question(self.subject.pk, "What is quantum physics?", self.student)

        self.assertIn("answer", result)
        self.assertFalse(result["had_relevant_chunks"])

        msg = ChatMessage.objects.first()
        self.assertFalse(msg.had_relevant_chunks)

    @patch("rag_tutor.query.anthropic.Anthropic")
    @patch("rag_tutor.query.embed_texts")
    def test_prompt_includes_chunk_text(self, mock_embed, MockAnthropic):
        mock_embed.return_value = [[0.1] * 1536]

        mock_block = MagicMock()
        mock_block.text = "Answer"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        ask_question(self.subject.pk, "Test question", self.student)

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("Variables are symbols", prompt_text)
        self.assertIn("Algebra Basics", prompt_text)
