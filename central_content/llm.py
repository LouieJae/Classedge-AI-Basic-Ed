import json
import os
import re

import anthropic
from django.conf import settings


def call_curriculum_planner(chapters, session_count, minutes_per_session, model_key):
    models_config = settings.CURRICULUM_PLANNER_MODELS
    config = models_config[model_key]

    api_key = os.environ.get(config["api_key_env"], "")
    client = anthropic.Anthropic(api_key=api_key)

    chapter_lines = "\n".join(
        f"- Chapter {ch['number']}: {ch['title']} (pages {ch['start_page']}–{ch['end_page']})"
        for ch in chapters
    )

    prompt = (
        f"You are a curriculum planner. Given the following textbook chapters and "
        f"a school schedule, produce a week-by-week teaching plan.\n\n"
        f"TEXTBOOK CHAPTERS:\n{chapter_lines}\n\n"
        f"SCHOOL SCHEDULE:\n"
        f"- Total sessions: {session_count}\n"
        f"- Minutes per session: {minutes_per_session}\n\n"
        f"RULES:\n"
        f"1. Every chapter must be assigned to exactly one week.\n"
        f"2. Chapters must remain in sequential order (chapter 1 before chapter 2, etc.).\n"
        f"3. Weeks must be numbered sequentially starting from 1.\n"
        f"4. Each week must have at least one chapter.\n"
        f"5. Distribute chapters across weeks proportionally to their page count.\n\n"
        f"Return ONLY a JSON array with this format, no other text:\n"
        f'[{{"week": 1, "chapters": [1, 2], "title": "Week title", '
        f'"description": "Brief description of topics covered"}}]'
    )

    response = client.messages.create(
        model=config["model"],
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        text = json_match.group()

    try:
        plan_data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}\nResponse: {text[:500]}")

    if not isinstance(plan_data, list) or len(plan_data) == 0:
        raise ValueError(f"LLM returned empty or non-list response: {text[:500]}")

    return plan_data


def call_content_generator(chapter_texts, week_title, week_description, session_count, minutes_per_session, model_key):
    models_config = settings.CURRICULUM_PLANNER_MODELS
    config = models_config[model_key]

    api_key = os.environ.get(config["api_key_env"], "")
    client = anthropic.Anthropic(api_key=api_key)

    chapter_sections = "\n\n".join(
        f"### Chapter {ch['number']}: {ch['title']}\n{ch['text']}"
        for ch in chapter_texts
    )

    prompt = (
        f"You are a content creator for a school learning management system. "
        f"Given the following textbook chapter content, create a lesson outline "
        f"and a quiz for one week of teaching.\n\n"
        f"WEEK: {week_title}\n"
        f"DESCRIPTION: {week_description}\n"
        f"SCHEDULE: {session_count} total sessions, {minutes_per_session} minutes each\n\n"
        f"CHAPTER CONTENT:\n{chapter_sections}\n\n"
        f"INSTRUCTIONS:\n"
        f"1. Write a detailed lesson outline covering the chapters' key concepts, "
        f"learning objectives, and teaching notes. Make it suitable for the given "
        f"number of sessions.\n"
        f"2. Write 5-10 quiz questions — a mix of multiple choice (with 4 options "
        f"marked A-D and the correct answer indicated) and short answer questions. "
        f"Questions should test understanding of the chapter content.\n\n"
        f"Return ONLY a JSON object with this format, no other text:\n"
        f'{{"lesson_description": "Full lesson outline text...", '
        f'"quiz_questions": "Numbered quiz questions..."}}'
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

    for key in ("lesson_description", "quiz_questions"):
        if key not in result or not result[key]:
            raise ValueError(f"LLM response missing required key: {key}")

    return result
