import json
import os
import re

import anthropic
from django.conf import settings


def call_school_content_generator(topic, objectives, content_type, reference_text, model_key):
    models_config = settings.AI_CONTENT_MODELS
    config = models_config[model_key]

    api_key = os.environ.get(config["api_key_env"], "")
    client = anthropic.Anthropic(api_key=api_key)

    content_instructions = []
    if content_type in ("module", "both"):
        content_instructions.append(
            "1. Write a detailed lesson outline covering key concepts, learning "
            "objectives, and teaching notes."
        )
    if content_type in ("quiz", "both"):
        content_instructions.append(
            f"{'2' if content_type == 'both' else '1'}. Write 5-10 quiz questions "
            "— a mix of multiple choice (with 4 options marked A-D and the correct "
            "answer indicated) and short answer questions testing understanding of "
            "the topic."
        )

    reference_section = ""
    if reference_text:
        reference_section = (
            f"\nREFERENCE MATERIAL:\n{reference_text}\n\n"
            "Ground your content in the reference material above.\n"
        )

    required_keys = []
    if content_type in ("module", "both"):
        required_keys.append('"lesson_description": "Full lesson outline text..."')
    if content_type in ("quiz", "both"):
        required_keys.append('"quiz_questions": "Numbered quiz questions..."')

    prompt = (
        f"You are a content creator for a school learning management system. "
        f"Create educational content for the following topic.\n\n"
        f"TOPIC: {topic}\n"
        f"LEARNING OBJECTIVES: {objectives}\n"
        f"{reference_section}\n"
        f"INSTRUCTIONS:\n"
        + "\n".join(content_instructions)
        + f"\n\nReturn ONLY a JSON object with this format, no other text:\n"
        f'{{{", ".join(required_keys)}}}'
    )

    response = client.messages.create(
        model=config["model"],
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}\nResponse: {text[:500]}")

    if not isinstance(result, dict):
        raise ValueError(f"LLM returned non-dict response: {text[:500]}")

    if content_type in ("module", "both"):
        if "lesson_description" not in result or not result["lesson_description"]:
            raise ValueError("LLM response missing required key: lesson_description")
    if content_type in ("quiz", "both"):
        if "quiz_questions" not in result or not result["quiz_questions"]:
            raise ValueError("LLM response missing required key: quiz_questions")

    return result
