from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest
from gamification.quest_settings_models import OrganizationQuestSettings

User = get_user_model()


class QuestViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("t", password="x", email="t@example.com")
        self.subject = Subject.objects.create(subject_name="S", quest_count_per_lesson=3)
        self.module = Module.objects.create(file_name="L", subject=self.subject)
        self.c = Client(); self.c.force_login(self.user)

    def test_mode_select_shows_enabled_modes(self):
        s = OrganizationQuestSettings.load()
        s.ai_mode_enabled = True; s.manual_mode_enabled = False; s.upload_mode_enabled = True; s.save()
        r = self.c.get(reverse("quest_mode_select", args=[self.module.id]))
        self.assertContains(r, "Generate with AI")
        self.assertNotContains(r, "Create manually")
        self.assertContains(r, "Upload from file")

    def test_generate_403_when_ai_disabled(self):
        s = OrganizationQuestSettings.load(); s.ai_mode_enabled = False; s.save()
        r = self.c.post(reverse("quest_generate", args=[self.module.id]))
        self.assertEqual(r.status_code, 403)

    def test_manual_create_makes_empty_draft_quest(self):
        s = OrganizationQuestSettings.load(); s.manual_mode_enabled = True; s.save()
        r = self.c.post(reverse("quest_manual_init", args=[self.module.id]))
        self.assertEqual(r.status_code, 302)

    def test_publish_flips_drafts(self):
        Quest.objects.create(module=self.module, order=1, kind="quiz", title="q",
                             body="b", payload={"options": ["a","b","c","d"], "correct_index": 0})
        r = self.c.post(reverse("quest_publish_all", args=[self.module.id]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Quest.objects.filter(module=self.module, status="published").count(), 1)
