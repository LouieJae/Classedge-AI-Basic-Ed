from django.test import TestCase

from rag_tutor.chunking import chunk_text


class ChunkTextTests(TestCase):
    def test_short_text_single_chunk(self):
        result = chunk_text("This is a short sentence.")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "This is a short sentence.")

    def test_long_text_splits(self):
        sentences = [f"Sentence number {i} has some content. " for i in range(100)]
        text = "".join(sentences)
        result = chunk_text(text, max_tokens=100, overlap_tokens=20)
        self.assertGreater(len(result), 1)
        for chunk in result:
            self.assertLessEqual(len(chunk) / 4, 150)

    def test_overlap_between_chunks(self):
        sentences = [f"Sentence {i} is about topic {i}. " for i in range(50)]
        text = "".join(sentences)
        result = chunk_text(text, max_tokens=50, overlap_tokens=15)
        if len(result) >= 2:
            end_of_first = result[0][-50:]
            start_of_second = result[1][:50]
            self.assertTrue(
                any(word in start_of_second for word in end_of_first.split()),
                "Expected some overlap between consecutive chunks",
            )

    def test_empty_text_returns_empty_list(self):
        result = chunk_text("")
        self.assertEqual(result, [])

    def test_whitespace_only_returns_empty_list(self):
        result = chunk_text("   \n\n  ")
        self.assertEqual(result, [])
