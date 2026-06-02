from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models.account_models import Profile
from roles.models import Role
from gamification.quest_settings_models import OrganizationQuestSettings

User = get_user_model()

class RegistrarQuestSettingsTests(TestCase):
    def setUp(self):
        self.registrar_role = Role.objects.get_or_create(name="Registrar")[0]
        self.other_role = Role.objects.get_or_create(name="Teacher")[0]
        self.registrar = User.objects.create_user("reg", email="reg@test.com", password="x")
        Profile.objects.filter(user=self.registrar).update(role=self.registrar_role)
        self.teacher = User.objects.create_user("tch", email="tch@test.com", password="x")
        Profile.objects.filter(user=self.teacher).update(role=self.other_role)

    def test_non_registrar_blocked(self):
        c = Client(); c.force_login(self.teacher)
        r = c.get(reverse("registrar_quest_settings"))
        self.assertIn(r.status_code, (302, 403))

    def test_registrar_can_view(self):
        c = Client(); c.force_login(self.registrar)
        r = c.get(reverse("registrar_quest_settings"))
        self.assertEqual(r.status_code, 200)

    def test_registrar_can_save(self):
        c = Client(); c.force_login(self.registrar)
        r = c.post(reverse("registrar_quest_settings"), {
            "ai_mode_enabled": "on",
            "manual_mode_enabled": "",
            "upload_mode_enabled": "on",
            "ai_provider": "openai",
        })
        self.assertEqual(r.status_code, 302)
        s = OrganizationQuestSettings.load()
        self.assertTrue(s.ai_mode_enabled)
        self.assertFalse(s.manual_mode_enabled)
        self.assertEqual(s.ai_provider, "openai")
        self.assertEqual(s.updated_by, self.registrar)

    def test_cannot_save_all_disabled(self):
        c = Client(); c.force_login(self.registrar)
        r = c.post(reverse("registrar_quest_settings"), {
            "ai_mode_enabled": "", "manual_mode_enabled": "", "upload_mode_enabled": "",
            "ai_provider": "anthropic",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "At least one")
