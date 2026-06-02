from unittest.mock import patch, MagicMock
from django.test import TestCase
from gamification.ai_providers import get_provider
from gamification.ai_providers.anthropic_provider import AnthropicProvider
from gamification.ai_providers.openai_provider import OpenAIProvider
from gamification.quest_settings_models import OrganizationQuestSettings


class ProviderFactoryTests(TestCase):
    def test_factory_returns_anthropic_by_default(self):
        OrganizationQuestSettings.load()
        self.assertIsInstance(get_provider(), AnthropicProvider)

    def test_factory_returns_openai_when_configured(self):
        s = OrganizationQuestSettings.load()
        s.ai_provider = "openai"
        s.save()
        self.assertIsInstance(get_provider(), OpenAIProvider)


class AnthropicProviderTests(TestCase):
    @patch("gamification.ai_providers.anthropic_provider.anthropic.Anthropic")
    def test_generate_returns_dict(self, mock_cls):
        client = MagicMock()
        client.messages.create.return_value.content = [MagicMock(text='{"quests":[]}')]
        mock_cls.return_value = client
        p = AnthropicProvider()
        out = p.generate("some lesson text", n=3)
        self.assertIn("quests", out)
