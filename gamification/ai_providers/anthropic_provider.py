import json
import os
import anthropic
from django.conf import settings
from gamification.ai_providers.base import SYSTEM_PROMPT, user_prompt


class AnthropicProvider:
    def generate(self, text: str, n: int) -> dict:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=getattr(settings, "RAG_TUTOR_LLM_MODEL", "claude-sonnet-4-6"),
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt(text, n)}],
        )
        raw = resp.content[0].text
        return json.loads(self._strip_codefence(raw))

    @staticmethod
    def _strip_codefence(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return raw
