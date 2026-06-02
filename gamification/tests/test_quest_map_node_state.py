from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt

User = get_user_model()


class QuestMapNodeStateTests(TestCase):
    def setUp(self):
        self.s = User.objects.create_user("s", password="x", email="s@example.com")
        self.subj = Subject.objects.create(subject_name="S")
        self.m1 = Module.objects.create(file_name="L1", subject=self.subj)
        self.m2 = Module.objects.create(file_name="L2", subject=self.subj)
        q = Quest.objects.create(module=self.m1, order=1, kind="quiz", title="t",
                                 body="b", status="published",
                                 payload={"options": ["a", "b", "c", "d"], "correct_index": 0})
        QuestAttempt.objects.create(quest=q, student=self.s, is_correct=True, score=1.0)
        Quest.objects.create(module=self.m2, order=1, kind="quiz", title="u",
                             body="b", status="published",
                             payload={"options": ["a", "b", "c", "d"], "correct_index": 0})

    def test_state_reflects_quest_completion(self):
        c = Client(); c.force_login(self.s)
        r = c.get(reverse("quest_map", args=[self.subj.id]))
        ctx_nodes = r.context["nodes"]
        states = {n["name"]: n["state"] for n in ctx_nodes}
        self.assertEqual(states["L1"], "done")
        self.assertIn(states["L2"], ("active", "locked"))
