from unittest.mock import patch, MagicMock
from datetime import date

from django.db import connection
from django.db.models.signals import post_save
from django.test import TestCase, override_settings

from rag_tutor.models import ContentChunk
from ai_content.tests.test_models import _create_subject

_RAG_SETTINGS = {
    "RAG_TUTOR_EMBEDDING_MODEL": "text-embedding-3-small",
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
}


@override_settings(**_RAG_SETTINGS)
class IndexContentTaskTests(TestCase):
    def setUp(self):
        # Disconnect auto-index signals so test helpers don't trigger Celery
        from rag_tutor.signals import index_module_on_save, index_activity_on_save
        from module.models.module import Module
        from activity.models.activity_model import Activity
        post_save.disconnect(index_module_on_save, sender=Module)
        post_save.disconnect(index_activity_on_save, sender=Activity)
        self.subject = _create_subject()

    def tearDown(self):
        # Reconnect signals after each test
        from rag_tutor.signals import index_module_on_save, index_activity_on_save
        from module.models.module import Module
        from activity.models.activity_model import Activity
        post_save.connect(index_module_on_save, sender=Module)
        post_save.connect(index_activity_on_save, sender=Activity)

    @patch("rag_tutor.tasks.embed_texts")
    def test_index_module_creates_chunks(self, mock_embed):
        from module.models.module import Module
        module = Module.objects.create(
            file_name="Algebra Basics",
            description="Variables are symbols. They represent unknown values. Expressions combine variables and numbers.",
            subject=self.subject,
        )
        mock_embed.return_value = [[0.1] * 1536]

        from rag_tutor.tasks import index_content
        index_content("module", module.pk)

        chunks = ContentChunk.objects.filter(source_type="module", source_id=module.pk)
        self.assertGreater(chunks.count(), 0)
        self.assertEqual(chunks.first().subject, self.subject)
        self.assertEqual(chunks.first().source_title, "Algebra Basics")
        mock_embed.assert_called_once()

    @patch("rag_tutor.tasks.embed_texts")
    def test_reindex_replaces_old_chunks(self, mock_embed):
        from module.models.module import Module
        module = Module.objects.create(
            file_name="Test Module",
            description="Original content about algebra and its foundational concepts.",
            subject=self.subject,
        )
        mock_embed.return_value = [[0.1] * 1536]

        from rag_tutor.tasks import index_content
        index_content("module", module.pk)
        self.assertEqual(ContentChunk.objects.filter(source_id=module.pk).count(), 1)

        module.description = "Updated content about geometry. This is different."
        module.save()
        mock_embed.return_value = [[0.2] * 1536]
        index_content("module", module.pk)

        chunks = ContentChunk.objects.filter(source_type="module", source_id=module.pk)
        self.assertEqual(chunks.count(), 1)
        self.assertIn("geometry", chunks.first().text)

    @patch("rag_tutor.tasks.embed_texts")
    def test_skip_empty_content(self, mock_embed):
        from module.models.module import Module
        module = Module.objects.create(
            file_name="Empty Module",
            description="",
            subject=self.subject,
        )

        from rag_tutor.tasks import index_content
        index_content("module", module.pk)

        self.assertEqual(ContentChunk.objects.count(), 0)
        mock_embed.assert_not_called()

    @patch("rag_tutor.tasks.embed_texts")
    def test_index_activity(self, mock_embed):
        from activity.models.activity_model import Activity, ActivityType
        quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")
        activity = Activity.objects.create(
            activity_name="Week 1 Quiz",
            activity_instruction="Question 1: What is a variable? A symbol that represents a value.",
            activity_type=quiz_type,
            subject=self.subject,
        )
        mock_embed.return_value = [[0.1] * 1536]

        from rag_tutor.tasks import index_content
        index_content("activity", activity.pk)

        chunks = ContentChunk.objects.filter(source_type="activity", source_id=activity.pk)
        self.assertGreater(chunks.count(), 0)
        self.assertEqual(chunks.first().source_title, "Week 1 Quiz")
