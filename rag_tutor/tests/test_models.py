from datetime import date

from django.db import connection
from django.test import TestCase

from rag_tutor.models import ContentChunk, ChatMessage
from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester


class ContentChunkModelTests(TestCase):
    def setUp(self):
        self.subject = _create_subject()

    def test_create_chunk(self):
        chunk = ContentChunk.objects.create(
            subject=self.subject,
            source_type=ContentChunk.SourceType.MODULE,
            source_id=1,
            source_title="Algebra Basics",
            chunk_index=0,
            text="Variables are symbols that represent values.",
            embedding=[0.1] * 1536,
        )
        self.assertEqual(chunk.source_type, "module")
        self.assertEqual(chunk.chunk_index, 0)
        self.assertEqual(len(chunk.text), 44)

    def test_unique_constraint(self):
        ContentChunk.objects.create(
            subject=self.subject,
            source_type="module",
            source_id=1,
            source_title="Test",
            chunk_index=0,
            text="First",
            embedding=[0.1] * 1536,
        )
        with self.assertRaises(Exception):
            ContentChunk.objects.create(
                subject=self.subject,
                source_type="module",
                source_id=1,
                source_title="Test",
                chunk_index=0,
                text="Duplicate",
                embedding=[0.2] * 1536,
            )

    def test_cascade_delete_with_subject(self):
        ContentChunk.objects.create(
            subject=self.subject,
            source_type="module",
            source_id=1,
            source_title="Test",
            chunk_index=0,
            text="Text",
            embedding=[0.1] * 1536,
        )
        self.assertEqual(ContentChunk.objects.count(), 1)
        self.subject.delete()
        self.assertEqual(ContentChunk.objects.count(), 0)


class ChatMessageModelTests(TestCase):
    def setUp(self):
        self.subject = _create_subject()
        self.user = _create_test_user(username="student_chat")

    def test_create_message(self):
        msg = ChatMessage.objects.create(
            subject=self.subject,
            student=self.user,
            question="What is algebra?",
            answer="Algebra is the study of mathematical symbols.",
            sources=[{"source_type": "module", "source_id": 1, "title": "Module 1", "chunk_index": 0}],
            had_relevant_chunks=True,
        )
        self.assertEqual(msg.question, "What is algebra?")
        self.assertTrue(msg.had_relevant_chunks)
        self.assertEqual(len(msg.sources), 1)

    def test_cascade_delete_with_subject(self):
        ChatMessage.objects.create(
            subject=self.subject,
            student=self.user,
            question="Test",
            answer="Test",
        )
        self.assertEqual(ChatMessage.objects.count(), 1)
        self.subject.delete()
        self.assertEqual(ChatMessage.objects.count(), 0)
