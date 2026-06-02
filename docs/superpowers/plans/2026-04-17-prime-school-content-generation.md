# Prime Per-school Content Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let school-side teachers generate AI-powered modules and activities from their subject views — providing a topic, objectives, content type, and optional PDF reference material.

**Architecture:** New Django app `ai_content/` on the school side. `GenerationRequest` model tracks each request. Celery task extracts PDF text (via PyMuPDF), calls Anthropic API for lesson/quiz content, creates school-side Module/Activity rows in draft state. "Generate with AI" button on the subject detail page opens a generation form.

**Tech Stack:** Django 5, Celery, Anthropic Python SDK, PyMuPDF (fitz), Bootstrap 5 (school-side templates), PostgreSQL (test DB: `test_neondb` with `--keepdb`)

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `ai_content/__init__.py` | App package |
| `ai_content/apps.py` | Django app config |
| `ai_content/models.py` | GenerationRequest model |
| `ai_content/llm.py` | LLM caller for school content generation |
| `ai_content/pdf_extract.py` | PDF text extraction via PyMuPDF |
| `ai_content/tasks.py` | Celery task for async generation |
| `ai_content/views.py` | Generation form view |
| `ai_content/forms.py` | GenerationRequestForm |
| `ai_content/urls.py` | URL patterns |
| `ai_content/templates/ai_content/generate.html` | Generation form page |
| `ai_content/tests/__init__.py` | Test package |
| `ai_content/tests/test_models.py` | Model tests |
| `ai_content/tests/test_pdf_extract.py` | PDF extraction tests |
| `ai_content/tests/test_llm.py` | LLM function tests |
| `ai_content/tests/test_tasks.py` | Celery task tests |
| `ai_content/tests/test_views.py` | View tests |

### Modified files

| File | Change |
|------|--------|
| `lms/settings.py` | Add `'ai_content'` to INSTALLED_APPS, add `AI_CONTENT_MODELS` config |
| `lms/urls.py` | Include `ai_content.urls` |

---

## Task 1: App Scaffold + GenerationRequest Model

**Files:**
- Create: `ai_content/__init__.py`
- Create: `ai_content/apps.py`
- Create: `ai_content/models.py`
- Create: `ai_content/tests/__init__.py`
- Create: `ai_content/tests/test_models.py`
- Modify: `lms/settings.py`

- [ ] **Step 1: Create the app package**

Create `ai_content/__init__.py` (empty file).

Create `ai_content/apps.py`:

```python
from django.apps import AppConfig


class AiContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_content"
```

Create `ai_content/tests/__init__.py` (empty file).

- [ ] **Step 2: Create the GenerationRequest model**

Create `ai_content/models.py`:

```python
import os
import uuid

from django.db import models


def _reference_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("ai_content", "references", new_name)


class GenerationRequest(models.Model):
    class ContentType(models.TextChoices):
        MODULE = "module", "Module"
        QUIZ = "quiz", "Quiz"
        BOTH = "both", "Both"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.CASCADE, related_name="generation_requests",
    )
    term = models.ForeignKey(
        "course.Term", on_delete=models.CASCADE, related_name="generation_requests",
    )
    requested_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="generation_requests",
    )
    topic = models.CharField(max_length=200)
    objectives = models.TextField()
    content_type = models.CharField(
        max_length=10, choices=ContentType.choices, default=ContentType.BOTH,
    )
    reference_file = models.FileField(
        upload_to=_reference_file_path, blank=True, null=True,
    )
    reference_text = models.TextField(blank=True)
    model_key = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)
    generated_module_id = models.PositiveIntegerField(null=True, blank=True)
    generated_activity_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.topic} ({self.status})"
```

- [ ] **Step 3: Register the app in settings**

In `lms/settings.py`, add `'ai_content'` to `INSTALLED_APPS` after `'received_central_content'`:

```python
    'central_content',
    'received_central_content',
    'ai_content',
]
```

Also add these settings at the end of `lms/settings.py`:

```python
# AI Content Generation (Prime tier)
AI_CONTENT_MODELS = {
    "haiku": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}
AI_CONTENT_DEFAULT_MODEL = "haiku"
```

- [ ] **Step 4: Create and run migration**

Run: `cd ~/classedge && env/bin/python manage.py makemigrations ai_content --name initial -v0 && env/bin/python manage.py migrate --run-syncdb --keepdb -v0`

- [ ] **Step 5: Write the model tests**

Create `ai_content/tests/test_models.py`:

```python
from django.test import TestCase

from ai_content.models import GenerationRequest
from course.models.term_model import Term
from course.models.semester_model import Semester
from accounts.models import CustomUser
from subject.models.subject_model import Subject
from datetime import date
from django.db import connection


def _create_test_user(username="teacher1", role_name="teacher"):
    from roles.models import Role
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass",
    )
    from accounts.models import Profile
    Profile.objects.filter(user=user).update(role=role)
    return user


def _create_subject(subject_name="Math 101"):
    """Create a Subject via raw SQL for compatibility with NOT-NULL orphan columns."""
    _DEFAULTS = {
        "subject_name": subject_name,
        "subject_code": "MATH101",
        "allow_substitute_teacher": False,
        "unit": 3,
        "is_coil": False,
        "is_hali": False,
        "is_cte": False,
        "number_of_enrollees": 0,
        "status": "Available",
        "self_attendance_enabled": False,
        "generation_status": "",
        "ide_languages": "[]",
        "supports_ide": False,
        "total_views": 0,
        "is_hidden": False,
        "is_archived": False,
        "is_deleted": False,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'subject_subject' AND is_nullable = 'NO' "
            "AND column_name != 'id' AND column_default IS NULL"
        )
        needed = {row[0]: row[1] for row in cursor.fetchall()}

        cols = []
        vals = []
        params = []
        for col, dtype in needed.items():
            val = _DEFAULTS.get(col)
            if val is None:
                if "int" in dtype:
                    val = 0
                elif "bool" in dtype:
                    val = False
                else:
                    val = ""
            cols.append(f'"{col}"')
            vals.append("%s")
            params.append(val)

        sql = f'INSERT INTO subject_subject ({", ".join(cols)}) VALUES ({", ".join(vals)}) RETURNING id, subject_name'
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return Subject.objects.get(pk=row[0])


class GenerationRequestModelTests(TestCase):
    def setUp(self):
        self.user = _create_test_user()
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )

    def test_create_request(self):
        req = GenerationRequest.objects.create(
            subject=self.subject,
            term=self.term,
            requested_by=self.user,
            topic="Algebra Basics",
            objectives="Students will learn variables and expressions.",
            content_type=GenerationRequest.ContentType.BOTH,
            model_key="haiku",
        )
        self.assertEqual(req.status, GenerationRequest.Status.PENDING)
        self.assertIsNone(req.generated_module_id)
        self.assertIsNone(req.generated_activity_id)
        self.assertEqual(req.reference_text, "")

    def test_cascade_delete_with_subject(self):
        GenerationRequest.objects.create(
            subject=self.subject,
            term=self.term,
            requested_by=self.user,
            topic="Test",
            objectives="Test",
            model_key="haiku",
        )
        self.assertEqual(GenerationRequest.objects.count(), 1)
        self.subject.delete()
        self.assertEqual(GenerationRequest.objects.count(), 0)

    def test_status_transitions(self):
        req = GenerationRequest.objects.create(
            subject=self.subject,
            term=self.term,
            requested_by=self.user,
            topic="Test",
            objectives="Test",
            model_key="haiku",
        )
        for status_val in ["pending", "running", "complete", "failed"]:
            req.status = status_val
            req.save(update_fields=["status"])
            req.refresh_from_db()
            self.assertEqual(req.status, status_val)

    def test_content_type_choices(self):
        for ct in ["module", "quiz", "both"]:
            req = GenerationRequest.objects.create(
                subject=self.subject,
                term=self.term,
                requested_by=self.user,
                topic=f"Test {ct}",
                objectives="Test",
                content_type=ct,
                model_key="haiku",
            )
            self.assertEqual(req.content_type, ct)
```

- [ ] **Step 6: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_models --keepdb -v2`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add ai_content/ lms/settings.py
git commit -m "feat(prime): add ai_content app with GenerationRequest model"
```

---

## Task 2: PDF Text Extraction

**Files:**
- Create: `ai_content/pdf_extract.py`
- Create: `ai_content/tests/test_pdf_extract.py`

- [ ] **Step 1: Write the failing tests**

Create `ai_content/tests/test_pdf_extract.py`:

```python
import io

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ai_content.pdf_extract import extract_text_from_pdf


def _make_test_pdf(text="Hello, this is test content for extraction."):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")


class ExtractTextFromPdfTests(TestCase):
    def test_extracts_text_from_valid_pdf(self):
        pdf_file = _make_test_pdf("Hello, this is a test.")
        result = extract_text_from_pdf(pdf_file)
        self.assertIn("Hello", result)
        self.assertIn("test", result)

    def test_returns_empty_string_for_invalid_file(self):
        bad_file = SimpleUploadedFile("bad.pdf", b"not a pdf", content_type="application/pdf")
        result = extract_text_from_pdf(bad_file)
        self.assertEqual(result, "")

    def test_truncates_long_text(self):
        long_text = "A" * 10000
        pdf_file = _make_test_pdf(long_text)
        result = extract_text_from_pdf(pdf_file)
        self.assertLessEqual(len(result), 8000)

    def test_returns_empty_string_for_none(self):
        result = extract_text_from_pdf(None)
        self.assertEqual(result, "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_pdf_extract --keepdb -v2 2>&1 | tail -20`
Expected: ImportError

- [ ] **Step 3: Create the extraction module**

Create `ai_content/pdf_extract.py`:

```python
import fitz

_MAX_TEXT_LENGTH = 8000


def extract_text_from_pdf(file_field):
    if file_field is None:
        return ""
    try:
        file_bytes = file_field.read()
        file_field.seek(0)
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        doc.close()
        full_text = "\n".join(pages_text).strip()
        return full_text[:_MAX_TEXT_LENGTH]
    except Exception:
        return ""
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_pdf_extract --keepdb -v2`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add ai_content/pdf_extract.py ai_content/tests/test_pdf_extract.py
git commit -m "feat(prime): add PDF text extraction module"
```

---

## Task 3: LLM Content Generator Function

**Files:**
- Create: `ai_content/llm.py`
- Create: `ai_content/tests/test_llm.py`

- [ ] **Step 1: Write the failing tests**

Create `ai_content/tests/test_llm.py`:

```python
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from ai_content.llm import call_school_content_generator

_LLM_SETTINGS = {
    "AI_CONTENT_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "AI_CONTENT_DEFAULT_MODEL": "haiku",
}

_BOTH_RESPONSE = json.dumps({
    "lesson_description": "This lesson covers algebra basics including variables, constants, and expressions.",
    "quiz_questions": "1. What is a variable?\nA) A fixed number\nB) A symbol representing a value\nC) An equation\nD) A constant\nAnswer: B",
})

_MODULE_RESPONSE = json.dumps({
    "lesson_description": "This lesson covers algebra basics.",
})

_QUIZ_RESPONSE = json.dumps({
    "quiz_questions": "1. What is a variable?\nA) A fixed number\nB) A symbol\nAnswer: B",
})


def _mock_anthropic_response(text_content):
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@override_settings(**_LLM_SETTINGS)
class CallSchoolContentGeneratorTests(TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_both_content_type(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_BOTH_RESPONSE)

        result = call_school_content_generator(
            topic="Algebra Basics",
            objectives="Learn variables and expressions",
            content_type="both",
            reference_text="",
            model_key="haiku",
        )
        self.assertIn("lesson_description", result)
        self.assertIn("quiz_questions", result)
        self.assertGreater(len(result["lesson_description"]), 0)
        self.assertGreater(len(result["quiz_questions"]), 0)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_module_only(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_MODULE_RESPONSE)

        result = call_school_content_generator(
            topic="Algebra Basics",
            objectives="Learn variables",
            content_type="module",
            reference_text="",
            model_key="haiku",
        )
        self.assertIn("lesson_description", result)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_quiz_only(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_QUIZ_RESPONSE)

        result = call_school_content_generator(
            topic="Algebra Basics",
            objectives="Test understanding",
            content_type="quiz",
            reference_text="",
            model_key="haiku",
        )
        self.assertIn("quiz_questions", result)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_prompt_includes_reference_text(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_BOTH_RESPONSE)

        call_school_content_generator(
            topic="Algebra Basics",
            objectives="Learn variables",
            content_type="both",
            reference_text="Algebra is the study of mathematical symbols.",
            model_key="haiku",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("mathematical symbols", prompt_text)
        self.assertIn("Algebra Basics", prompt_text)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("ai_content.llm.anthropic.Anthropic")
    def test_invalid_json_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("not json")

        with self.assertRaises(ValueError):
            call_school_content_generator(
                topic="Test", objectives="Test",
                content_type="both", reference_text="", model_key="haiku",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_llm --keepdb -v2 2>&1 | tail -20`
Expected: ImportError

- [ ] **Step 3: Create the LLM module**

Create `ai_content/llm.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_llm --keepdb -v2`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add ai_content/llm.py ai_content/tests/test_llm.py
git commit -m "feat(prime): add school content generator LLM function"
```

---

## Task 4: Celery Task

**Files:**
- Create: `ai_content/tasks.py`
- Create: `ai_content/tests/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `ai_content/tests/test_tasks.py`:

```python
from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_content.models import GenerationRequest
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from course.models.semester_model import Semester
from course.models.term_model import Term

_LLM_SETTINGS = {
    "AI_CONTENT_MODELS": {
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    "AI_CONTENT_DEFAULT_MODEL": "haiku",
}

_BOTH_RESULT = {
    "lesson_description": "This lesson covers algebra fundamentals.",
    "quiz_questions": "1. What is x?\nA) Number\nB) Variable\nAnswer: B",
}

_MODULE_RESULT = {
    "lesson_description": "Lesson outline for geometry.",
}

_QUIZ_RESULT = {
    "quiz_questions": "1. What is a triangle?\nAnswer: A 3-sided polygon",
}


@override_settings(**_LLM_SETTINGS)
class GenerateSchoolContentTaskTests(TestCase):
    def setUp(self):
        self.user = _create_test_user()
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        ActivityType.objects.get_or_create(name="Quiz")

    def _make_request(self, content_type="both", **kw):
        defaults = {
            "subject": self.subject,
            "term": self.term,
            "requested_by": self.user,
            "topic": "Algebra Basics",
            "objectives": "Learn variables",
            "content_type": content_type,
            "model_key": "haiku",
        }
        defaults.update(kw)
        return GenerationRequest.objects.create(**defaults)

    @patch("ai_content.tasks.call_school_content_generator")
    def test_both_creates_module_and_activity(self, mock_llm):
        mock_llm.return_value = _BOTH_RESULT
        req = self._make_request(content_type="both")

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.COMPLETE)
        self.assertIsNotNone(req.generated_module_id)
        self.assertIsNotNone(req.generated_activity_id)

        module = Module.objects.get(pk=req.generated_module_id)
        self.assertEqual(module.file_name, "Algebra Basics")
        self.assertEqual(module.description, _BOTH_RESULT["lesson_description"])
        self.assertEqual(module.subject, self.subject)
        self.assertEqual(module.term, self.term)

        activity = Activity.objects.get(pk=req.generated_activity_id)
        self.assertEqual(activity.activity_name, "Algebra Basics Quiz")
        self.assertEqual(activity.activity_instruction, _BOTH_RESULT["quiz_questions"])
        self.assertTrue(activity.additional_modules.filter(pk=module.pk).exists())

    @patch("ai_content.tasks.call_school_content_generator")
    def test_module_only(self, mock_llm):
        mock_llm.return_value = _MODULE_RESULT
        req = self._make_request(content_type="module")

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.COMPLETE)
        self.assertIsNotNone(req.generated_module_id)
        self.assertIsNone(req.generated_activity_id)

    @patch("ai_content.tasks.call_school_content_generator")
    def test_quiz_only(self, mock_llm):
        mock_llm.return_value = _QUIZ_RESULT
        req = self._make_request(content_type="quiz")

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.COMPLETE)
        self.assertIsNone(req.generated_module_id)
        self.assertIsNotNone(req.generated_activity_id)

    @patch("ai_content.tasks.call_school_content_generator")
    @patch("ai_content.tasks.extract_text_from_pdf")
    def test_extracts_reference_pdf(self, mock_extract, mock_llm):
        mock_extract.return_value = "Extracted PDF text"
        mock_llm.return_value = _BOTH_RESULT

        pdf = SimpleUploadedFile("ref.pdf", b"%PDF-fake", content_type="application/pdf")
        req = self._make_request(reference_file=pdf)

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        mock_extract.assert_called_once()
        req.refresh_from_db()
        self.assertEqual(req.reference_text, "Extracted PDF text")
        mock_llm.assert_called_once()
        call_kwargs = mock_llm.call_args.kwargs
        self.assertEqual(call_kwargs["reference_text"], "Extracted PDF text")

    @patch("ai_content.tasks.call_school_content_generator")
    def test_llm_failure_sets_failed(self, mock_llm):
        mock_llm.side_effect = ValueError("LLM error")
        req = self._make_request()

        from ai_content.tasks import generate_school_content
        generate_school_content(req.pk)

        req.refresh_from_db()
        self.assertEqual(req.status, GenerationRequest.Status.FAILED)
        self.assertIn("LLM error", req.error_message)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_tasks --keepdb -v2 2>&1 | tail -20`
Expected: ImportError

- [ ] **Step 3: Create the Celery task**

Create `ai_content/tasks.py`:

```python
from celery import shared_task
from django.db import transaction

from ai_content.llm import call_school_content_generator
from ai_content.pdf_extract import extract_text_from_pdf


@shared_task
def generate_school_content(request_id):
    from activity.models.activity_model import Activity, ActivityType
    from module.models.module import Module
    from ai_content.models import GenerationRequest

    try:
        req = GenerationRequest.objects.select_related(
            "subject", "term", "requested_by",
        ).get(pk=request_id)
    except GenerationRequest.DoesNotExist:
        return {"status": "error", "detail": "request_not_found"}

    req.status = GenerationRequest.Status.RUNNING
    req.save(update_fields=["status", "updated_at"])

    if req.reference_file and not req.reference_text:
        req.reference_text = extract_text_from_pdf(req.reference_file)
        req.save(update_fields=["reference_text", "updated_at"])

    try:
        result = call_school_content_generator(
            topic=req.topic,
            objectives=req.objectives,
            content_type=req.content_type,
            reference_text=req.reference_text,
            model_key=req.model_key,
        )
    except (ValueError, Exception) as exc:
        req.status = GenerationRequest.Status.FAILED
        req.error_message = str(exc)[:2000]
        req.save(update_fields=["status", "error_message", "updated_at"])
        return {"status": "error", "detail": str(exc)[:500]}

    module = None
    activity = None

    with transaction.atomic():
        if req.content_type in ("module", "both"):
            module = Module.objects.create(
                file_name=req.topic,
                description=result["lesson_description"],
                subject=req.subject,
                term=req.term,
            )

        if req.content_type in ("quiz", "both"):
            quiz_type = ActivityType.objects.filter(name="Quiz").first()
            if not quiz_type:
                req.status = GenerationRequest.Status.FAILED
                req.error_message = "ActivityType 'Quiz' not found"
                req.save(update_fields=["status", "error_message", "updated_at"])
                return {"status": "error", "detail": "quiz_type_not_found"}

            activity = Activity.objects.create(
                activity_name=f"{req.topic} Quiz",
                activity_instruction=result["quiz_questions"],
                activity_type=quiz_type,
                subject=req.subject,
                term=req.term,
                max_score=100,
                time_duration=30,
                passing_score=75,
                passing_score_type="percentage",
                max_retake=1,
                retake_method="highest",
                shuffle_questions=True,
                is_graded=True,
            )

            if module:
                activity.additional_modules.add(module)

    req.generated_module_id = module.pk if module else None
    req.generated_activity_id = activity.pk if activity else None
    req.status = GenerationRequest.Status.COMPLETE
    req.save(update_fields=[
        "generated_module_id", "generated_activity_id", "status", "updated_at",
    ])

    return {"status": "success", "request_id": req.pk}
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_tasks --keepdb -v2`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add ai_content/tasks.py ai_content/tests/test_tasks.py
git commit -m "feat(prime): add school content generation Celery task"
```

---

## Task 5: Generation Form View + Template + URLs

**Files:**
- Create: `ai_content/forms.py`
- Create: `ai_content/views.py`
- Create: `ai_content/urls.py`
- Create: `ai_content/templates/ai_content/generate.html`
- Create: `ai_content/tests/test_views.py`
- Modify: `lms/urls.py`

- [ ] **Step 1: Create the form**

Create `ai_content/forms.py`:

```python
from django import forms

from ai_content.models import GenerationRequest


class GenerationRequestForm(forms.Form):
    topic = forms.CharField(max_length=200)
    objectives = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    content_type = forms.ChoiceField(
        choices=GenerationRequest.ContentType.choices,
        initial=GenerationRequest.ContentType.BOTH,
        widget=forms.RadioSelect,
    )
    reference_file = forms.FileField(required=False)
    model_key = forms.ChoiceField(choices=[])

    def __init__(self, *args, model_keys=None, **kw):
        super().__init__(*args, **kw)
        if model_keys:
            self.fields["model_key"].choices = [(k, k) for k in model_keys]

    def clean_reference_file(self):
        f = self.cleaned_data.get("reference_file")
        if f and not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are accepted.")
        if f and f.size > 50 * 1024 * 1024:
            raise forms.ValidationError("File must be under 50MB.")
        return f
```

- [ ] **Step 2: Create the view**

Create `ai_content/views.py`:

```python
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from activity.utils.authorization import check_subject_access
from ai_content.forms import GenerationRequestForm
from ai_content.models import GenerationRequest
from ai_content.tasks import generate_school_content
from course.models.semester_model import Semester
from course.models.term_model import Term
from django.utils import timezone
from subject.models.subject_model import Subject


@login_required
def generate_content(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)

    has_access, redirect_resp = check_subject_access(
        request, subject, require_teacher=True,
    )
    if not has_access:
        return redirect_resp

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()
    terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()

    model_keys = list(settings.AI_CONTENT_MODELS.keys())

    if request.method == "POST":
        form = GenerationRequestForm(request.POST, request.FILES, model_keys=model_keys)
        if form.is_valid():
            term_id = request.POST.get("term_id")
            term = get_object_or_404(Term, pk=term_id)

            gen_request = GenerationRequest.objects.create(
                subject=subject,
                term=term,
                requested_by=request.user,
                topic=form.cleaned_data["topic"],
                objectives=form.cleaned_data["objectives"],
                content_type=form.cleaned_data["content_type"],
                reference_file=form.cleaned_data.get("reference_file"),
                model_key=form.cleaned_data["model_key"],
            )
            generate_school_content.delay(gen_request.pk)

            messages.success(
                request,
                f"Content generation started for \"{gen_request.topic}\". "
                "New content will appear in your subject shortly.",
            )
            return redirect("subjectDetail", pk=subject_id)
    else:
        form = GenerationRequestForm(model_keys=model_keys)

    return render(
        request,
        "ai_content/generate.html",
        {
            "subject": subject,
            "form": form,
            "terms": terms,
        },
    )
```

- [ ] **Step 3: Create URL patterns**

Create `ai_content/urls.py`:

```python
from django.urls import path

from ai_content import views

urlpatterns = [
    path("ai-content/generate/<int:subject_id>/", views.generate_content, name="ai_generate_content"),
]
```

- [ ] **Step 4: Register URLs in `lms/urls.py`**

Add this line in `lms/urls.py` before the closing `]` of `urlpatterns`, after the `received_central_content` include:

```python
    path('', include('ai_content.urls')),
```

- [ ] **Step 5: Create the template**

Create directory `ai_content/templates/ai_content/` then create `ai_content/templates/ai_content/generate.html`:

```html
{% extends 'base.html' %}
{% block title %}Generate with AI — {{ subject.subject_name }}{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <div class="row justify-content-center">
        <div class="col-lg-8">
            <h3 class="mb-3">Generate with AI</h3>
            <p class="text-muted mb-4">{{ subject.subject_name }}</p>

            <form method="post" enctype="multipart/form-data" class="card shadow-sm">
                {% csrf_token %}
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Term</label>
                        <select name="term_id" class="form-select" required>
                            {% for t in terms %}
                            <option value="{{ t.pk }}">{{ t.term_name }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Topic</label>
                        <input type="text" name="topic" value="{{ form.topic.value|default:'' }}" class="form-control" required placeholder="e.g. Introduction to Algebra">
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Learning Objectives</label>
                        <textarea name="objectives" class="form-control" rows="4" required placeholder="Describe what students should learn...">{{ form.objectives.value|default:'' }}</textarea>
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Content Type</label>
                        <div>
                            {% for radio in form.content_type %}
                            <div class="form-check form-check-inline">
                                {{ radio.tag }}
                                <label class="form-check-label" for="{{ radio.id_for_label }}">{{ radio.choice_label }}</label>
                            </div>
                            {% endfor %}
                        </div>
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Reference Material (optional)</label>
                        <input type="file" name="reference_file" class="form-control" accept=".pdf">
                        <div class="form-text">PDF only, max 50MB. Content will be grounded in this material.</div>
                    </div>

                    <div class="mb-4">
                        <label class="form-label fw-semibold">AI Model</label>
                        <select name="model_key" class="form-select">
                            {% for choice in form.model_key.field.choices %}
                            <option value="{{ choice.0 }}">{{ choice.1 }}</option>
                            {% endfor %}
                        </select>
                    </div>

                    {% if form.errors %}
                    <div class="alert alert-danger">
                        {% for field, errors in form.errors.items %}
                        {% for error in errors %}
                        <p class="mb-0">{{ error }}</p>
                        {% endfor %}
                        {% endfor %}
                    </div>
                    {% endif %}

                    <button type="submit" class="btn btn-primary">Generate Content</button>
                    <a href="{% url 'subjectDetail' subject.pk %}" class="btn btn-outline-secondary ms-2">Cancel</a>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Write the view tests**

Create `ai_content/tests/test_views.py`:

```python
from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, Client, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_content.models import GenerationRequest
from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.term_model import Term
from subject.models.subject_model import Subject

_OVERRIDES = dict(
    AI_CONTENT_MODELS={
        "haiku": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    AI_CONTENT_DEFAULT_MODEL="haiku",
)


@override_settings(**_OVERRIDES)
class GenerateContentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="teacher1", role_name="teacher")
        self.student = _create_test_user(username="student1", role_name="student")
        self.subject = _create_subject()
        # Assign teacher to subject
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.subject.refresh_from_db()

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )

    def test_form_renders_for_teacher(self):
        self.client.login(username="teacher1", password="testpass")
        resp = self.client.get(f"/ai-content/generate/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Generate with AI")
        self.assertContains(resp, "haiku")

    def test_student_cannot_access(self):
        self.client.login(username="student1", password="testpass")
        resp = self.client.get(f"/ai-content/generate/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)

    @patch("ai_content.views.generate_school_content.delay")
    def test_post_creates_request_and_redirects(self, mock_delay):
        self.client.login(username="teacher1", password="testpass")
        resp = self.client.post(
            f"/ai-content/generate/{self.subject.pk}/",
            {
                "term_id": self.term.pk,
                "topic": "Algebra Basics",
                "objectives": "Learn variables and expressions",
                "content_type": "both",
                "model_key": "haiku",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(GenerationRequest.objects.count(), 1)
        req = GenerationRequest.objects.first()
        self.assertEqual(req.topic, "Algebra Basics")
        self.assertEqual(req.content_type, "both")
        mock_delay.assert_called_once_with(req.pk)

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get(f"/ai-content/generate/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url.lower())

    @patch("ai_content.views.generate_school_content.delay")
    def test_rejects_non_pdf_file(self, mock_delay):
        self.client.login(username="teacher1", password="testpass")
        bad_file = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        resp = self.client.post(
            f"/ai-content/generate/{self.subject.pk}/",
            {
                "term_id": self.term.pk,
                "topic": "Test",
                "objectives": "Test",
                "content_type": "both",
                "model_key": "haiku",
                "reference_file": bad_file,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(GenerationRequest.objects.count(), 0)
        mock_delay.assert_not_called()
```

- [ ] **Step 7: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content.tests.test_views --keepdb -v2`
Expected: All 5 tests PASS

- [ ] **Step 8: Commit**

```bash
cd ~/classedge && git add ai_content/forms.py ai_content/views.py ai_content/urls.py ai_content/templates/ ai_content/tests/test_views.py lms/urls.py
git commit -m "feat(prime): add generation form view, template, and URLs"
```

---

## Task 6: Full Integration Test Run

- [ ] **Step 1: Run the complete test suite**

Run: `cd ~/classedge && env/bin/python manage.py test ai_content central_content received_central_content --keepdb 2>&1 | tail -10`
Expected: All tests PASS

- [ ] **Step 2: Run Django system check**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`
Expected: `System check identified no issues.`

- [ ] **Step 3: Verify migration state**

Run: `cd ~/classedge && env/bin/python manage.py showmigrations ai_content 2>&1`
Expected: `[X] 0001_initial`

- [ ] **Step 4: Final commit if any fixes needed**

```bash
cd ~/classedge && git add -A && git commit -m "fix(prime): address integration test findings"
```

---

## Summary

| Task | What it builds | Tests added |
|------|---------------|-------------|
| 1 | App scaffold + GenerationRequest model | 4 tests |
| 2 | PDF text extraction module | 4 tests |
| 3 | LLM content generator function | 5 tests |
| 4 | Celery task for content generation | 5 tests |
| 5 | Generation form view + template + URLs | 5 tests |
| 6 | Full integration verification | — |

**Total new tests: ~23**
