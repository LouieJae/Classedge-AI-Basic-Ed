# Per-week Content Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate CentralModule + CentralActivity rows for each week of an approved CurriculumPlan, using LLM + parsed chapter text.

**Architecture:** A `ContentGenerationJob` model tracks progress. A Celery task iterates over plan weeks sequentially, parsing chapters on-demand if needed, calling the LLM for lesson + quiz content, and creating draft Module/Activity rows. The plan detail page gets a "Generate Content" button and a job status page with HTMX polling.

**Tech Stack:** Django 5, Celery, Anthropic Python SDK, HTMX + Tailwind (CDN), PostgreSQL (test DB: `test_neondb` with `--keepdb`)

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `central_content/models/content_generation_job.py` | ContentGenerationJob model |
| `central_content/content_tasks.py` | Celery tasks for content generation (separate from `tasks.py` which handles PDF parsing) |
| `central_content/views/generation.py` | Views: trigger generation, job status page, HTMX status badge |
| `central_content/templates/central_content/generation/status.html` | Job status page with per-week progress |
| `central_content/templates/central_content/generation/status_badge.html` | HTMX-pollable status badge |
| `central_content/tests/test_content_generation_model.py` | Model tests |
| `central_content/tests/test_content_llm.py` | Tests for the content generation LLM function |
| `central_content/tests/test_content_tasks.py` | Celery task tests |
| `central_content/tests/test_generation_views.py` | View tests |

### Modified files

| File | Change |
|------|--------|
| `central_content/models/__init__.py` | Export ContentGenerationJob |
| `central_content/llm.py` | Add `call_content_generator()` function |
| `central_content/urls.py` | Add generation URL routes |
| `central_content/templates/central_content/plans/detail.html` | Add "Generate Content" button + job list |
| `central_content/tests/factories.py` | Add `make_content_generation_job` helper |

---

## Task 1: ContentGenerationJob Model

**Files:**
- Create: `central_content/models/content_generation_job.py`
- Create: `central_content/tests/test_content_generation_model.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/factories.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_content_generation_model.py`:

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from central_content.models import ContentGenerationJob, CurriculumPlan
from central_content.tests.factories import (
    make_editor, make_publisher, make_subject, make_textbook,
    make_curriculum_plan,
)


class ContentGenerationJobModelTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
        )

    def test_create_job(self):
        job = ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=[
                {"week": 1, "status": "pending"},
                {"week": 2, "status": "pending"},
            ],
            triggered_by=self.publisher,
        )
        self.assertEqual(job.status, ContentGenerationJob.Status.PENDING)
        self.assertEqual(job.completed_weeks, 0)
        self.assertEqual(job.failed_weeks, 0)
        self.assertEqual(job.total_weeks, 2)
        self.assertEqual(len(job.week_results), 2)

    def test_cascade_delete_with_plan(self):
        ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=[],
            triggered_by=self.publisher,
        )
        self.assertEqual(ContentGenerationJob.objects.count(), 1)
        self.plan.delete()
        self.assertEqual(ContentGenerationJob.objects.count(), 0)

    def test_multiple_jobs_per_plan(self):
        for key in ["haiku", "sonnet"]:
            ContentGenerationJob.objects.create(
                curriculum_plan=self.plan,
                model_key=key,
                total_weeks=2,
                week_results=[],
                triggered_by=self.publisher,
            )
        self.assertEqual(self.plan.generation_jobs.count(), 2)

    def test_week_results_stores_and_retrieves(self):
        results = [
            {"week": 1, "status": "done", "module_id": 10, "activity_id": 20},
            {"week": 2, "status": "failed", "error": "parse failed"},
        ]
        job = ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=results,
            triggered_by=self.publisher,
        )
        job.refresh_from_db()
        self.assertEqual(job.week_results[0]["module_id"], 10)
        self.assertEqual(job.week_results[1]["error"], "parse failed")

    def test_status_choices(self):
        job = ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=[],
            triggered_by=self.publisher,
        )
        for status_val in ["pending", "running", "complete", "failed"]:
            job.status = status_val
            job.save(update_fields=["status"])
            job.refresh_from_db()
            self.assertEqual(job.status, status_val)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_content_generation_model --keepdb -v2 2>&1 | tail -20`
Expected: ImportError (ContentGenerationJob doesn't exist)

- [ ] **Step 3: Create the ContentGenerationJob model**

Create `central_content/models/content_generation_job.py`:

```python
from django.db import models


class ContentGenerationJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    curriculum_plan = models.ForeignKey(
        "central_content.CurriculumPlan",
        on_delete=models.CASCADE,
        related_name="generation_jobs",
    )
    model_key = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    total_weeks = models.PositiveIntegerField()
    completed_weeks = models.PositiveIntegerField(default=0)
    failed_weeks = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    week_results = models.JSONField(default=list)
    triggered_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="content_generation_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_generation_job"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Generation job for {self.curriculum_plan} ({self.status})"
```

- [ ] **Step 4: Export from `__init__.py`**

In `central_content/models/__init__.py`, add:

```python
from .content_generation_job import ContentGenerationJob
```

And add `"ContentGenerationJob"` to `__all__`.

- [ ] **Step 5: Create and run migration**

Run: `cd ~/classedge && env/bin/python manage.py makemigrations central_content --name content_generation_job -v0 && env/bin/python manage.py migrate --run-syncdb --keepdb -v0`

- [ ] **Step 6: Add factory helper**

Append to `central_content/tests/factories.py`:

```python
def make_content_generation_job(curriculum_plan=None, triggered_by=None, **kw):
    from central_content.models import ContentGenerationJob
    if triggered_by is None:
        triggered_by = make_publisher()
    if curriculum_plan is None:
        curriculum_plan = make_curriculum_plan()
    defaults = {
        "curriculum_plan": curriculum_plan,
        "model_key": "haiku",
        "total_weeks": len(curriculum_plan.plan_data),
        "week_results": [
            {"week": entry["week"], "status": "pending"}
            for entry in curriculum_plan.plan_data
        ],
        "triggered_by": triggered_by,
    }
    defaults.update(kw)
    return ContentGenerationJob.objects.create(**defaults)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_content_generation_model --keepdb -v2 2>&1 | tail -20`
Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
cd ~/classedge && git add central_content/models/content_generation_job.py central_content/models/__init__.py central_content/tests/test_content_generation_model.py central_content/tests/factories.py central_content/migrations/
git commit -m "feat(4c): add ContentGenerationJob model"
```

---

## Task 2: LLM Content Generator Function

**Files:**
- Create: `central_content/tests/test_content_llm.py`
- Modify: `central_content/llm.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_content_llm.py`:

```python
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.llm import call_content_generator

_LLM_SETTINGS = {
    "CURRICULUM_PLANNER_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "CURRICULUM_PLANNER_DEFAULT_MODEL": "haiku",
}

_VALID_RESPONSE = json.dumps({
    "lesson_description": "This week covers the foundations of real numbers and integers. Students will learn about number classification, the number line, and basic properties of integers.\n\nLearning objectives:\n- Classify numbers as natural, whole, integer, rational\n- Plot integers on a number line\n- Compare and order integers",
    "quiz_questions": "1. Which of the following is NOT an integer?\nA) -3\nB) 0\nC) 2.5\nD) 7\nAnswer: C\n\n2. Arrange these numbers from least to greatest: 5, -2, 0, -7, 3\nAnswer: -7, -2, 0, 3, 5",
})

_CHAPTER_TEXTS = [
    {"number": 1, "title": "Real Numbers", "text": "Real numbers include all rational and irrational numbers..."},
    {"number": 2, "title": "Integers", "text": "Integers are whole numbers and their negatives..."},
]


def _mock_anthropic_response(text_content):
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@override_settings(**_LLM_SETTINGS)
class CallContentGeneratorTests(TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_valid_response_parsed(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        result = call_content_generator(
            chapter_texts=_CHAPTER_TEXTS,
            week_title="Foundations",
            week_description="Introduction to number systems",
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )
        self.assertIn("lesson_description", result)
        self.assertIn("quiz_questions", result)
        self.assertGreater(len(result["lesson_description"]), 0)
        self.assertGreater(len(result["quiz_questions"]), 0)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_prompt_includes_chapter_text(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        call_content_generator(
            chapter_texts=_CHAPTER_TEXTS,
            week_title="Foundations",
            week_description="Introduction",
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("Real Numbers", prompt_text)
        self.assertIn("rational and irrational", prompt_text)
        self.assertIn("Foundations", prompt_text)
        self.assertIn("30", prompt_text)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_invalid_json_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("not json")

        with self.assertRaises(ValueError):
            call_content_generator(
                chapter_texts=_CHAPTER_TEXTS,
                week_title="Foundations",
                week_description="Intro",
                session_count=30,
                minutes_per_session=90,
                model_key="haiku",
            )

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_missing_keys_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        bad_response = json.dumps({"lesson_description": "lesson only"})
        mock_client.messages.create.return_value = _mock_anthropic_response(bad_response)

        with self.assertRaises(ValueError):
            call_content_generator(
                chapter_texts=_CHAPTER_TEXTS,
                week_title="Foundations",
                week_description="Intro",
                session_count=30,
                minutes_per_session=90,
                model_key="haiku",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_content_llm --keepdb -v2 2>&1 | tail -20`
Expected: ImportError (`call_content_generator` doesn't exist)

- [ ] **Step 3: Add `call_content_generator` to `central_content/llm.py`**

Append this function to the end of `central_content/llm.py` (after the existing `call_curriculum_planner` function):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_content_llm --keepdb -v2 2>&1 | tail -20`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add central_content/llm.py central_content/tests/test_content_llm.py
git commit -m "feat(4c): add call_content_generator LLM function"
```

---

## Task 3: Content Generation Celery Tasks

**Files:**
- Create: `central_content/content_tasks.py`
- Create: `central_content/tests/test_content_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_content_tasks.py`:

```python
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.models import (
    CentralModule, CentralActivity, ContentGenerationJob, ParsedChapter,
)
from central_content.tests.factories import (
    make_editor, make_publisher, make_subject, make_textbook,
    make_curriculum_plan, make_content_generation_job,
)

_LLM_SETTINGS = {
    "CURRICULUM_PLANNER_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "CURRICULUM_PLANNER_DEFAULT_MODEL": "haiku",
}

_LLM_RESULT = {
    "lesson_description": "This week covers foundations of algebra.",
    "quiz_questions": "1. What is a variable?\nA) A number\nB) A letter\nC) A symbol representing a value\nD) An equation\nAnswer: C",
}


@override_settings(**_LLM_SETTINGS)
class GenerateWeekContentTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        # Set chapters to COMPLETE with parsed_data
        for ch in self.textbook.chapters.all():
            ch.status = ParsedChapter.Status.COMPLETE
            ch.parsed_data = {"text": f"Content for chapter {ch.chapter_number}..."}
            ch.save(update_fields=["status", "parsed_data"])

        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
        )
        self.job = make_content_generation_job(
            curriculum_plan=self.plan,
            triggered_by=self.publisher,
        )

    @patch("central_content.content_tasks.call_content_generator")
    def test_success_creates_module_and_activity(self, mock_llm):
        from activity.models.activity_model import ActivityType
        ActivityType.objects.get_or_create(name="Quiz")
        mock_llm.return_value = _LLM_RESULT

        from central_content.content_tasks import generate_week_content
        generate_week_content(self.job.pk, 0)

        self.assertEqual(CentralModule.objects.filter(central_subject=self.subject).count(), 1)
        self.assertEqual(CentralActivity.objects.filter(central_subject=self.subject).count(), 1)

        module = CentralModule.objects.get(central_subject=self.subject)
        self.assertEqual(module.state, CentralModule.State.DRAFT)
        self.assertIn("Week 1", module.file_name)
        self.assertEqual(module.description, _LLM_RESULT["lesson_description"])
        self.assertEqual(module.created_by, self.publisher)

        activity = CentralActivity.objects.get(central_subject=self.subject)
        self.assertEqual(activity.state, CentralActivity.State.DRAFT)
        self.assertIn("Week 1", activity.activity_name)
        self.assertEqual(activity.activity_instruction, _LLM_RESULT["quiz_questions"])
        self.assertEqual(activity.max_score, 100)
        self.assertEqual(activity.time_duration, 30)
        self.assertTrue(activity.related_modules.filter(pk=module.pk).exists())

        self.job.refresh_from_db()
        self.assertEqual(self.job.week_results[0]["status"], "done")
        self.assertEqual(self.job.week_results[0]["module_id"], module.pk)

    @patch("central_content.content_tasks.call_content_generator")
    def test_unparsed_chapter_triggers_parsing(self, mock_llm):
        from activity.models.activity_model import ActivityType
        ActivityType.objects.get_or_create(name="Quiz")
        mock_llm.return_value = _LLM_RESULT

        # Reset first chapter to pending
        ch = self.textbook.chapters.first()
        ch.status = ParsedChapter.Status.PENDING
        ch.parsed_data = None
        ch.save(update_fields=["status", "parsed_data"])

        with patch("central_content.content_tasks.parse_single_chapter") as mock_parse:
            def side_effect(chapter_id):
                c = ParsedChapter.objects.get(pk=chapter_id)
                c.status = ParsedChapter.Status.COMPLETE
                c.parsed_data = {"text": "Parsed content"}
                c.save(update_fields=["status", "parsed_data"])
                return {"status": "success"}
            mock_parse.apply = MagicMock(side_effect=lambda args: side_effect(args[0]))

            from central_content.content_tasks import generate_week_content
            generate_week_content(self.job.pk, 0)

        mock_parse.apply.assert_called()
        self.assertEqual(CentralModule.objects.filter(central_subject=self.subject).count(), 1)

    @patch("central_content.content_tasks.call_content_generator")
    def test_chapter_parse_failure_marks_week_failed(self, mock_llm):
        # Reset first chapter to pending, it won't get parsed_data
        ch = self.textbook.chapters.first()
        ch.status = ParsedChapter.Status.PENDING
        ch.parsed_data = None
        ch.save(update_fields=["status", "parsed_data"])

        with patch("central_content.content_tasks.parse_single_chapter") as mock_parse:
            def side_effect(chapter_id):
                c = ParsedChapter.objects.get(pk=chapter_id)
                c.status = ParsedChapter.Status.FAILED
                c.error_message = "MinerU error"
                c.save(update_fields=["status", "error_message"])
                return {"status": "error"}
            mock_parse.apply = MagicMock(side_effect=lambda args: side_effect(args[0]))

            from central_content.content_tasks import generate_week_content
            generate_week_content(self.job.pk, 0)

        self.job.refresh_from_db()
        self.assertEqual(self.job.week_results[0]["status"], "failed")
        self.assertIn("parse", self.job.week_results[0]["error"].lower())
        self.assertEqual(self.job.failed_weeks, 1)
        mock_llm.assert_not_called()

    @patch("central_content.content_tasks.call_content_generator")
    def test_llm_failure_marks_week_failed(self, mock_llm):
        from activity.models.activity_model import ActivityType
        ActivityType.objects.get_or_create(name="Quiz")
        mock_llm.side_effect = ValueError("LLM returned invalid JSON")

        from central_content.content_tasks import generate_week_content
        generate_week_content(self.job.pk, 0)

        self.job.refresh_from_db()
        self.assertEqual(self.job.week_results[0]["status"], "failed")
        self.assertEqual(self.job.failed_weeks, 1)
        self.assertEqual(CentralModule.objects.filter(central_subject=self.subject).count(), 0)


@override_settings(**_LLM_SETTINGS)
class RunContentGenerationTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        for ch in self.textbook.chapters.all():
            ch.status = ParsedChapter.Status.COMPLETE
            ch.parsed_data = {"text": f"Content for chapter {ch.chapter_number}"}
            ch.save(update_fields=["status", "parsed_data"])

        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
        )
        self.job = make_content_generation_job(
            curriculum_plan=self.plan,
            triggered_by=self.publisher,
        )

    @patch("central_content.content_tasks.generate_week_content")
    def test_runs_all_weeks_and_completes(self, mock_gen):
        from central_content.content_tasks import run_content_generation
        run_content_generation(self.job.pk)

        self.assertEqual(mock_gen.call_count, len(self.plan.plan_data))
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, ContentGenerationJob.Status.COMPLETE)

    @patch("central_content.content_tasks.generate_week_content")
    def test_sets_running_status(self, mock_gen):
        statuses = []
        def capture_status(job_id, week_idx):
            job = ContentGenerationJob.objects.get(pk=job_id)
            statuses.append(job.status)
        mock_gen.side_effect = capture_status

        from central_content.content_tasks import run_content_generation
        run_content_generation(self.job.pk)

        self.assertIn(ContentGenerationJob.Status.RUNNING, statuses)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_content_tasks --keepdb -v2 2>&1 | tail -20`
Expected: ImportError (content_tasks module doesn't exist)

- [ ] **Step 3: Create `central_content/content_tasks.py`**

```python
from celery import shared_task
from django.db import transaction

from central_content.llm import call_content_generator
from central_content.tasks import parse_single_chapter


_MAX_CHAPTER_TEXT_LENGTH = 4000


def _extract_chapter_text(parsed_data):
    if not parsed_data:
        return ""
    if isinstance(parsed_data, dict):
        return str(parsed_data.get("text", ""))[:_MAX_CHAPTER_TEXT_LENGTH]
    return str(parsed_data)[:_MAX_CHAPTER_TEXT_LENGTH]


@shared_task
def generate_week_content(job_id, week_index):
    from activity.models.activity_model import ActivityType
    from central_content.models import (
        CentralActivity, CentralModule, ContentGenerationJob, ParsedChapter,
    )

    job = ContentGenerationJob.objects.select_related(
        "curriculum_plan__textbook__central_subject",
        "triggered_by",
    ).get(pk=job_id)

    plan = job.curriculum_plan
    textbook = plan.textbook
    subject = textbook.central_subject
    week_entry = plan.plan_data[week_index]
    week_num = week_entry["week"]
    week_title = week_entry.get("title", f"Week {week_num}")
    week_desc = week_entry.get("description", "")

    chapter_texts = []
    for ch_num in week_entry["chapters"]:
        try:
            chapter = textbook.chapters.get(chapter_number=ch_num)
        except ParsedChapter.DoesNotExist:
            _mark_week_failed(job, week_index, f"Chapter {ch_num} not found")
            return

        if chapter.parsed_data is None and chapter.status == ParsedChapter.Status.PENDING:
            parse_single_chapter.apply(args=[chapter.pk])
            chapter.refresh_from_db()

        if chapter.parsed_data is None:
            _mark_week_failed(
                job, week_index,
                f"Chapter {ch_num} parse failed (status: {chapter.status})",
            )
            return

        chapter_texts.append({
            "number": chapter.chapter_number,
            "title": chapter.title,
            "text": _extract_chapter_text(chapter.parsed_data),
        })

    try:
        result = call_content_generator(
            chapter_texts=chapter_texts,
            week_title=week_title,
            week_description=week_desc,
            session_count=plan.session_count,
            minutes_per_session=plan.minutes_per_session,
            model_key=job.model_key,
        )
    except (ValueError, Exception) as exc:
        _mark_week_failed(job, week_index, f"LLM error: {exc}")
        return

    quiz_type = ActivityType.objects.filter(name="Quiz").first()
    if not quiz_type:
        _mark_week_failed(job, week_index, "ActivityType 'Quiz' not found")
        return

    with transaction.atomic():
        module = CentralModule.objects.create(
            central_subject=subject,
            file_name=f"Week {week_num}: {week_title}",
            description=result["lesson_description"],
            order=week_num,
            state=CentralModule.State.DRAFT,
            created_by=job.triggered_by,
        )
        activity = CentralActivity.objects.create(
            central_subject=subject,
            activity_name=f"Week {week_num} Quiz: {week_title}",
            activity_instruction=result["quiz_questions"],
            activity_type=quiz_type,
            max_score=100,
            time_duration=30,
            passing_score=75,
            passing_score_type=CentralActivity.PassingScoreType.PERCENTAGE,
            max_retake=1,
            retake_method=CentralActivity.RetakeMethod.HIGHEST,
            shuffle_questions=True,
            is_graded=True,
            state=CentralActivity.State.DRAFT,
            created_by=job.triggered_by,
        )
        activity.related_modules.add(module)

    job.refresh_from_db()
    job.week_results[week_index] = {
        "week": week_num,
        "status": "done",
        "module_id": module.pk,
        "activity_id": activity.pk,
    }
    job.completed_weeks += 1
    job.save(update_fields=["week_results", "completed_weeks", "updated_at"])


def _mark_week_failed(job, week_index, error_msg):
    job.refresh_from_db()
    week_num = job.curriculum_plan.plan_data[week_index]["week"]
    job.week_results[week_index] = {
        "week": week_num,
        "status": "failed",
        "error": error_msg,
    }
    job.failed_weeks += 1
    job.save(update_fields=["week_results", "failed_weeks", "updated_at"])


@shared_task
def run_content_generation(job_id):
    from central_content.models import ContentGenerationJob

    job = ContentGenerationJob.objects.get(pk=job_id)
    job.status = ContentGenerationJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])

    for week_index in range(job.total_weeks):
        generate_week_content(job_id, week_index)

    job.refresh_from_db()
    if job.failed_weeks == job.total_weeks:
        job.status = ContentGenerationJob.Status.FAILED
    else:
        job.status = ContentGenerationJob.Status.COMPLETE
    job.save(update_fields=["status", "updated_at"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_content_tasks --keepdb -v2 2>&1 | tail -30`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add central_content/content_tasks.py central_content/tests/test_content_tasks.py
git commit -m "feat(4c): add content generation Celery tasks"
```

---

## Task 4: Generation Views + Templates + URLs

**Files:**
- Create: `central_content/views/generation.py`
- Create: `central_content/templates/central_content/generation/status.html`
- Create: `central_content/templates/central_content/generation/status_badge.html`
- Create: `central_content/tests/test_generation_views.py`
- Modify: `central_content/urls.py`
- Modify: `central_content/templates/central_content/plans/detail.html`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_generation_views.py`:

```python
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.models import ContentGenerationJob, CurriculumPlan
from central_content.tests.factories import (
    make_editor, make_publisher, make_reviewer, make_subject,
    make_textbook, make_curriculum_plan, make_content_generation_job,
)

_SAFE_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

_OVERRIDES = dict(
    ROOT_URLCONF="central_content.urls",
    AUTHENTICATION_BACKENDS=["central_content.auth_backends.CentralStaffAuthBackend"],
    TEMPLATES=_SAFE_TEMPLATES,
    CURRICULUM_PLANNER_MODELS={
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    CURRICULUM_PLANNER_DEFAULT_MODEL="haiku",
)


@override_settings(**_OVERRIDES)
class TriggerGenerationViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
            status=CurriculumPlan.Status.APPROVED,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    @patch("central_content.views.generation.run_content_generation.delay")
    def test_post_triggers_task_and_redirects(self, mock_delay):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/generate-content",
            {"model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContentGenerationJob.objects.count(), 1)
        job = ContentGenerationJob.objects.first()
        self.assertEqual(job.model_key, "haiku")
        self.assertEqual(job.total_weeks, len(self.plan.plan_data))
        mock_delay.assert_called_once_with(job.pk)

    def test_cannot_generate_from_draft_plan(self):
        self._login("pub@example.com")
        self.plan.status = CurriculumPlan.Status.DRAFT
        self.plan.save(update_fields=["status"])
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/generate-content",
            {"model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_editor_cannot_trigger(self):
        self._login("ed@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/generate-content",
            {"model_key": "haiku"},
        )
        self.assertIn(resp.status_code, [302, 403])


@override_settings(**_OVERRIDES)
class JobStatusViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
            status=CurriculumPlan.Status.APPROVED,
        )
        self.job = make_content_generation_job(
            curriculum_plan=self.plan,
            triggered_by=self.publisher,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_status_page_renders(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/jobs/{self.job.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "pending")

    def test_status_page_shows_completed_week(self):
        self._login("pub@example.com")
        self.job.week_results = [
            {"week": 1, "status": "done", "module_id": 1, "activity_id": 2},
            {"week": 2, "status": "pending"},
        ]
        self.job.completed_weeks = 1
        self.job.save(update_fields=["week_results", "completed_weeks"])
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/jobs/{self.job.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "done")

    def test_status_badge_endpoint(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/jobs/{self.job.pk}/status"
        )
        self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_generation_views --keepdb -v2 2>&1 | tail -20`
Expected: ImportError or 404

- [ ] **Step 3: Create the generation views**

Create `central_content/views/generation.py`:

```python
from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from central_content.models import ContentGenerationJob, CurriculumPlan
from central_content.content_tasks import run_content_generation
from central_content.permissions import central_role_required


@central_role_required("publisher")
@require_POST
def trigger_generation(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan.objects.select_related("textbook"),
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.APPROVED:
        return HttpResponseBadRequest("Only approved plans can generate content.")

    model_key = request.POST.get(
        "model_key", settings.CURRICULUM_PLANNER_DEFAULT_MODEL,
    )

    job = ContentGenerationJob.objects.create(
        curriculum_plan=plan,
        model_key=model_key,
        total_weeks=len(plan.plan_data),
        week_results=[
            {"week": entry["week"], "status": "pending"}
            for entry in plan.plan_data
        ],
        triggered_by=request.user,
    )

    run_content_generation.delay(job.pk)

    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/jobs/{job.pk}/"
    )


@central_role_required("publisher", "reviewer", "editor")
def job_status(request, subject_id, textbook_id, plan_id, job_id):
    job = get_object_or_404(
        ContentGenerationJob.objects.select_related(
            "curriculum_plan__textbook__central_subject",
            "triggered_by",
        ),
        pk=job_id,
        curriculum_plan_id=plan_id,
        curriculum_plan__textbook_id=textbook_id,
        curriculum_plan__textbook__central_subject_id=subject_id,
    )
    return render(
        request,
        "central_content/generation/status.html",
        {
            "job": job,
            "plan": job.curriculum_plan,
            "textbook": job.curriculum_plan.textbook,
            "subject": job.curriculum_plan.textbook.central_subject,
        },
    )


@central_role_required("publisher", "reviewer", "editor")
def job_status_badge(request, subject_id, textbook_id, plan_id, job_id):
    job = get_object_or_404(
        ContentGenerationJob,
        pk=job_id,
        curriculum_plan_id=plan_id,
    )
    return render(
        request,
        "central_content/generation/status_badge.html",
        {"job": job},
    )
```

- [ ] **Step 4: Register URL patterns**

In `central_content/urls.py`, add the import:

```python
from central_content.views import generation as generation_views
```

Add these URL patterns (after the plan patterns, before the staff patterns):

```python
    # Content generation
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/generate-content", generation_views.trigger_generation, name="trigger_generation"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/jobs/<int:job_id>/", generation_views.job_status, name="job_status"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/jobs/<int:job_id>/status", generation_views.job_status_badge, name="job_status_badge"),
```

- [ ] **Step 5: Create templates**

Create `central_content/templates/central_content/generation/status.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Generation Job — {{ textbook.title }}{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-4">
    <div>
        <h1 class="text-2xl font-semibold">Content Generation</h1>
        <p class="text-gray-600">{{ textbook.title }} · {{ job.model_key }} · {{ plan.session_count }} sessions</p>
    </div>
    <div hx-get="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/jobs/{{ job.id }}/status"
         hx-trigger="every 5s"
         hx-swap="innerHTML">
        {% include "central_content/generation/status_badge.html" %}
    </div>
</div>

<div class="bg-white rounded shadow overflow-hidden mb-6">
    <div class="p-4 border-b bg-gray-50">
        <div class="flex justify-between text-sm text-gray-600">
            <span>Progress: {{ job.completed_weeks }}/{{ job.total_weeks }} weeks</span>
            {% if job.failed_weeks > 0 %}
            <span class="text-red-600">{{ job.failed_weeks }} failed</span>
            {% endif %}
        </div>
        {% if job.total_weeks > 0 %}
        <div class="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div class="bg-blue-600 h-2 rounded-full" style="width: {% widthratio job.completed_weeks job.total_weeks 100 %}%"></div>
        </div>
        {% endif %}
    </div>
    <table class="w-full text-sm">
        <thead>
            <tr class="text-left text-gray-500 border-b">
                <th class="py-2 px-4 w-16">Week</th>
                <th class="py-2 px-4">Status</th>
                <th class="py-2 px-4">Result</th>
            </tr>
        </thead>
        <tbody>
        {% for week in job.week_results %}
            <tr class="border-t">
                <td class="py-2 px-4 font-medium">{{ week.week }}</td>
                <td class="py-2 px-4">
                    {% if week.status == "done" %}
                    <span class="text-green-700">Done</span>
                    {% elif week.status == "failed" %}
                    <span class="text-red-700">Failed</span>
                    {% elif week.status == "generating" %}
                    <span class="text-amber-700">Generating...</span>
                    {% else %}
                    <span class="text-gray-500">Pending</span>
                    {% endif %}
                </td>
                <td class="py-2 px-4">
                    {% if week.status == "done" %}
                    <a href="/subjects/{{ subject.id }}/modules/{{ week.module_id }}/" class="text-blue-700">Module</a>
                    ·
                    <a href="/subjects/{{ subject.id }}/activities/{{ week.activity_id }}/" class="text-blue-700">Activity</a>
                    {% elif week.status == "failed" %}
                    <span class="text-red-600 text-xs">{{ week.error }}</span>
                    {% endif %}
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>

<div class="text-sm text-gray-500 mb-4">
    Triggered by {{ job.triggered_by.full_name }} · {{ job.created_at|date:"M d, Y H:i" }}
</div>

<a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/" class="text-blue-700">&larr; Back to plan</a>
{% endblock %}
```

Create `central_content/templates/central_content/generation/status_badge.html`:

```html
<span class="px-3 py-1 rounded text-sm
    {% if job.status == 'complete' %}bg-green-100 text-green-800
    {% elif job.status == 'failed' %}bg-red-100 text-red-800
    {% elif job.status == 'running' %}bg-amber-100 text-amber-800
    {% else %}bg-gray-100 text-gray-800{% endif %}">
    {{ job.get_status_display }}
    {% if job.status == 'running' %}({{ job.completed_weeks }}/{{ job.total_weeks }}){% endif %}
</span>
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_generation_views --keepdb -v2 2>&1 | tail -30`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add central_content/views/generation.py central_content/tests/test_generation_views.py central_content/urls.py central_content/templates/central_content/generation/
git commit -m "feat(4c): add content generation views, templates, and URLs"
```

---

## Task 5: Update Plan Detail Template

**Files:**
- Modify: `central_content/templates/central_content/plans/detail.html`
- Modify: `central_content/views/plans.py`

- [ ] **Step 1: Update plan detail view to pass generation jobs and model keys**

In `central_content/views/plans.py`, update the `plan_detail` function. Add to the context:

```python
@central_role_required("publisher", "reviewer", "editor")
def plan_detail(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan.objects.select_related("textbook", "generated_by"),
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    chapters = {
        ch.chapter_number: ch.title
        for ch in plan.textbook.chapters.all()
    }
    for week in plan.plan_data:
        week["chapter_titles"] = [
            chapters.get(num, f"Chapter {num}") for num in week["chapters"]
        ]

    generation_jobs = plan.generation_jobs.select_related("triggered_by").all()
    model_keys = list(settings.CURRICULUM_PLANNER_MODELS.keys())

    return render(
        request,
        "central_content/plans/detail.html",
        {
            "subject": plan.textbook.central_subject,
            "textbook": plan.textbook,
            "plan": plan,
            "generation_jobs": generation_jobs,
            "model_keys": model_keys,
        },
    )
```

- [ ] **Step 2: Update the plan detail template**

Add a "Generate Content" section after the approve/reject buttons. In the `detail.html` template, after the `{% endif %}` that closes the draft block (after the edit details section), and before the "Generated by" line, add:

```html
{% if plan.status == "approved" %}
<div class="bg-white p-4 rounded shadow mb-6">
    <h2 class="font-semibold mb-3">Generate Content</h2>
    <form method="post" action="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/generate-content" class="flex gap-3 items-end mb-4">
        {% csrf_token %}
        <div>
            <label class="block text-xs text-gray-500 mb-1">LLM Model</label>
            <select name="model_key" class="border rounded px-3 py-1.5 text-sm">
                {% for key in model_keys %}
                <option value="{{ key }}">{{ key }}</option>
                {% endfor %}
            </select>
        </div>
        <button type="submit" class="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700">Generate Content</button>
    </form>

    {% if generation_jobs %}
    <h3 class="text-sm font-medium text-gray-600 mb-2">Generation Jobs</h3>
    <ul>
    {% for gj in generation_jobs %}
        <li class="border-t py-2 flex justify-between items-center">
            <a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/jobs/{{ gj.id }}/" class="text-blue-700">
                {{ gj.model_key }} · {{ gj.created_at|date:"M d, Y H:i" }}
            </a>
            <span class="text-xs px-2 py-0.5 rounded {% if gj.status == 'complete' %}bg-green-100 text-green-800{% elif gj.status == 'failed' %}bg-red-100 text-red-800{% elif gj.status == 'running' %}bg-amber-100 text-amber-800{% else %}bg-gray-100 text-gray-800{% endif %}">
                {{ gj.get_status_display }}
            </span>
        </li>
    {% endfor %}
    </ul>
    {% endif %}
</div>
{% endif %}
```

- [ ] **Step 3: Run existing plan view tests to ensure nothing broke**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_plan_views --keepdb -v2 2>&1 | tail -20`
Expected: All 12 tests still PASS

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && git add central_content/views/plans.py central_content/templates/central_content/plans/detail.html
git commit -m "feat(4c): add generate content button and job list to plan detail"
```

---

## Task 6: Full Integration Test Run

- [ ] **Step 1: Run the complete test suite**

Run: `cd ~/classedge && env/bin/python manage.py test central_content received_central_content --keepdb -v2 2>&1 | tail -40`
Expected: All tests PASS

- [ ] **Step 2: Run Django system check**

Run: `cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central env/bin/python manage.py check 2>&1`
Expected: `System check identified no issues.`

- [ ] **Step 3: Verify migration state**

Run: `cd ~/classedge && env/bin/python manage.py showmigrations central_content 2>&1 | tail -15`
Expected: All migrations applied (with `[X]`)

- [ ] **Step 4: Final commit if any fixes needed**

If any fixes were needed, commit them:
```bash
cd ~/classedge && git add -A && git commit -m "fix(4c): address integration test findings"
```

---

## Summary

| Task | What it builds | Tests added |
|------|---------------|-------------|
| 1 | ContentGenerationJob model + factory | 5 tests |
| 2 | LLM content generator function | 4 tests |
| 3 | Celery tasks (generate_week_content + run_content_generation) | 6 tests |
| 4 | Generation views + templates + URLs | 6 tests |
| 5 | Updated plan detail with generate button + job list | (covered by existing) |
| 6 | Full integration verification | — |

**Total new tests: ~21**
