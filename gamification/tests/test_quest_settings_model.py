from django.core.exceptions import ValidationError
from django.test import TestCase
from gamification.quest_settings_models import OrganizationQuestSettings


class OrgQuestSettingsTests(TestCase):
    def test_load_creates_singleton_with_defaults(self):
        s = OrganizationQuestSettings.load()
        self.assertTrue(s.ai_mode_enabled)
        self.assertTrue(s.manual_mode_enabled)
        self.assertTrue(s.upload_mode_enabled)
        self.assertEqual(s.ai_provider, "anthropic")
        self.assertEqual(s.pk, 1)

    def test_load_returns_same_row(self):
        a = OrganizationQuestSettings.load()
        b = OrganizationQuestSettings.load()
        self.assertEqual(a.pk, b.pk)

    def test_cannot_disable_all_modes(self):
        s = OrganizationQuestSettings.load()
        s.ai_mode_enabled = False
        s.manual_mode_enabled = False
        s.upload_mode_enabled = False
        with self.assertRaises(ValidationError):
            s.full_clean()
