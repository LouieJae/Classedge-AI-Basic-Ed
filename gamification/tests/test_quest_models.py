from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt, QuestGenerationJob

User = get_user_model()


class QuestModelTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="Math")
        self.module = Module.objects.create(file_name="Lesson 1", subject=self.subject)
        self.student = User.objects.create_user("s1", password="x", email="s1@example.com")

    def test_create_quest_defaults(self):
        q = Quest.objects.create(module=self.module, order=1, kind="quiz",
                                 title="T", body="B", payload={"options": ["a"], "correct_index": 0})
        self.assertEqual(q.status, "draft")
        self.assertTrue(q.counts_toward_grade)

    def test_attempt_unique_per_student(self):
        q = Quest.objects.create(module=self.module, order=1, kind="task",
                                 title="t", body="b", payload={})
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        with self.assertRaises(IntegrityError):
            QuestAttempt.objects.create(quest=q, student=self.student, is_correct=False, score=0.0)

    def test_job_default_status(self):
        j = QuestGenerationJob.objects.create(module=self.module)
        self.assertEqual(j.status, "queued")
