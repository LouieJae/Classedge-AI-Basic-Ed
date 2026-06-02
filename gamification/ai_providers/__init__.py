from gamification.ai_providers.anthropic_provider import AnthropicProvider
from gamification.ai_providers.openai_provider import OpenAIProvider
from gamification.quest_settings_models import OrganizationQuestSettings

_REGISTRY = {"anthropic": AnthropicProvider, "openai": OpenAIProvider}


def get_provider():
    s = OrganizationQuestSettings.load()
    return _REGISTRY[s.ai_provider]()
