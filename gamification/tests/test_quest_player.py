from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from module.models.module import Module
from module.models.student_progress import StudentProgress
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt

User = get_user_model()


class QuestPlayerTests(TestCase):
    def setUp(self):
        self.s = User.objects.create_user("s", password="x", email="s@example.com")
        self.subject = Subject.objects.create(subject_name="S")
        self.module = Module.objects.create(file_name="L", subject=self.subject)
        self.q = Quest.objects.create(module=self.module, order=1, kind="quiz",
                                      title="t", body="2+2?", status="published",
                                      payload={"options": ["3", "4", "5", "6"], "correct_index": 1})
        self.c = Client(); self.c.force_login(self.s)

    def test_submit_correct_quiz(self):
        r = self.c.post(reverse("quest_play_submit", args=[self.q.id]), {"answer": "1"})
        self.assertEqual(r.status_code, 302)
        a = QuestAttempt.objects.get(quest=self.q, student=self.s)
        self.assertTrue(a.is_correct)
        self.assertEqual(a.score, 1.0)

    def test_completing_all_marks_module_complete(self):
        self.c.post(reverse("quest_play_submit", args=[self.q.id]), {"answer": "1"})
        sp = StudentProgress.objects.get(student=self.s, module=self.module)
        self.assertTrue(sp.completed)
