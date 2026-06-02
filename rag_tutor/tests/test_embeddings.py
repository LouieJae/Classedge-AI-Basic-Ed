from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from rag_tutor.embeddings import embed_texts

_RAG_SETTINGS = {
    "RAG_TUTOR_EMBEDDING_MODEL": "text-embedding-3-small",
}


@override_settings(**_RAG_SETTINGS)
class EmbedTextsTests(TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("rag_tutor.embeddings.openai.OpenAI")
    def test_returns_correct_number_of_vectors(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        mock_embedding_1 = MagicMock()
        mock_embedding_1.embedding = [0.1] * 1536
        mock_embedding_2 = MagicMock()
        mock_embedding_2.embedding = [0.2] * 1536

        mock_response = MagicMock()
        mock_response.data = [mock_embedding_1, mock_embedding_2]
        mock_client.embeddings.create.return_value = mock_response

        result = embed_texts(["Hello world", "Another text"])
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 1536)
        self.assertEqual(len(result[1]), 1536)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("rag_tutor.embeddings.openai.OpenAI")
    def test_calls_correct_model(self, MockOpenAI):
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client

        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1] * 1536
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]
        mock_client.embeddings.create.return_value = mock_response

        embed_texts(["Test"])

        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "text-embedding-3-small")

    def test_empty_list_returns_empty(self):
        result = embed_texts([])
        self.assertEqual(result, [])
