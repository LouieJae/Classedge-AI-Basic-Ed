import io
from unittest.mock import patch
from django.test import TestCase
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestGenerationJob
from gamification.quest_generation import run_generation_job


FAKE_OUTPUT = {"quests": [
    {"kind": "quiz", "title": f"Q{i}", "body": "b",
     "payload": {"options": ["a", "b", "c", "d"], "correct_index": 0},
     "source_chunk": "..."} for i in range(3)
]}


class GenerationTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="S", quest_count_per_lesson=3)
        self.module = Module.objects.create(file_name="L", subject=self.subject)

    @patch("gamification.quest_generation.extract_text", return_value="A" * 500)
    @patch("gamification.quest_generation.get_provider")
    def test_happy_path(self, mock_prov, _):
        mock_prov.return_value.generate.return_value = FAKE_OUTPUT
        job = QuestGenerationJob.objects.create(module=self.module)
        run_generation_job(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, "complete")
        self.assertEqual(Quest.objects.filter(module=self.module).count(), 3)
        self.assertTrue(all(q.status == "draft" for q in Quest.objects.all()))

    @patch("gamification.quest_generation.extract_text", side_effect=Exception("unsupported"))
    def test_extraction_failure_marks_job_failed(self, _):
        job = QuestGenerationJob.objects.create(module=self.module)
        run_generation_job(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIn("unsupported", job.error)
