import json
import os
from gamification.ai_providers.base import SYSTEM_PROMPT, user_prompt


class OpenAIProvider:
    def generate(self, text: str, n: int) -> dict:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(text, n)},
            ],
        )
        return json.loads(resp.choices[0].message.content)
