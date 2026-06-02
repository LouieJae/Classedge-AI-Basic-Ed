# Curriculum Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a curriculum planner that takes parsed textbook chapters and a school's session schedule, calls an LLM to produce a week-by-week chapter mapping, and lets publishers review/edit/approve the plan.

**Architecture:** School-side schedule API provides session data. Central-side `llm.py` module calls the Anthropic API with chapter + session info and returns structured JSON. `CurriculumPlan` model stores the plan with a draft/approved/rejected workflow. Celery tasks handle async generation. Central portal UI provides plan generation, inline editing, and approval.

**Tech Stack:** Django 5, Celery, Anthropic Python SDK, HTMX + Tailwind (CDN), PostgreSQL (test DB: `test_neondb` with `--keepdb`)

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `received_central_content/views/schedule.py` | School-side schedule API endpoint |
| `received_central_content/tests/test_schedule_api.py` | Tests for schedule API |
| `central_content/models/curriculum_plan.py` | CurriculumPlan model |
| `central_content/llm.py` | LLM caller: builds prompt, calls Anthropic API, parses response |
| `central_content/views/plans.py` | Plan generation, detail/edit, approve/reject, bulk-run views |
| `central_content/templates/central_content/plans/generate.html` | Plan generation form page |
| `central_content/templates/central_content/plans/detail.html` | Plan detail + inline editor |
| `central_content/templates/central_content/plans/list.html` | Plans list for a textbook |
| `central_content/tests/test_llm.py` | Tests for LLM module |
| `central_content/tests/test_curriculum_plan_model.py` | Model tests for CurriculumPlan |
| `central_content/tests/test_plan_tasks.py` | Celery task tests |
| `central_content/tests/test_plan_views.py` | View tests for plan pages |

### Modified files

| File | Change |
|------|--------|
| `received_central_content/urls.py` | Add schedule endpoint route |
| `central_content/models/__init__.py` | Export CurriculumPlan |
| `central_content/tasks.py` | Add `generate_curriculum_plan` and `bulk_generate_plans` tasks |
| `central_content/urls.py` | Add plan URL routes |
| `central_content/tests/factories.py` | Add `make_textbook`, `make_chapter`, `make_curriculum_plan` helpers |
| `central_content/templates/central_content/textbooks/detail.html` | Add "Generate Plan" button + existing plans list |
| `central_content/templates/central_content/subjects/detail.html` | Add "Generate Plans for All Textbooks" button |

---

## Task 1: School-side Schedule API

**Files:**
- Create: `received_central_content/views/schedule.py`
- Create: `received_central_content/tests/test_schedule_api.py`
- Modify: `received_central_content/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `received_central_content/tests/test_schedule_api.py`:

```python
import json
from datetime import date, time

from django.db import connection
from django.test import TestCase, override_settings, Client

from course.models.semester_model import Semester
from course.models.term_model import Term
from received_central_content.tests.test_native_ingest import _create_subject


def _auth():
    return {"HTTP_AUTHORIZATION": "Bearer " + "t" * 40}


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class ScheduleAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.subject = _create_subject(subject_name="Math 101", subject_code="MATH101")

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

        from subject.models.schedule_model import Schedule
        Schedule.objects.create(
            subject_id=self.subject["id"],
            schedule_start_time=time(8, 0),
            schedule_end_time=time(9, 30),
            days_of_week=["Mon", "Wed", "Fri"],
            semester=self.semester,
        )

    def test_no_token_returns_401(self):
        resp = self.client.get(f"/api/central/schedule/{self.subject['id']}/")
        self.assertEqual(resp.status_code, 401)

    def test_unknown_subject_returns_404(self):
        resp = self.client.get("/api/central/schedule/99999/", **_auth())
        self.assertEqual(resp.status_code, 404)

    def test_subject_with_no_term_returns_400(self):
        no_term_subj = _create_subject(subject_name="No Term", subject_code="NT101")
        # Create schedule without a semester that has terms
        from subject.models.schedule_model import Schedule
        sem_no_term = Semester.objects.create(
            semester_name="Second Semester",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 5, 31),
        )
        Schedule.objects.create(
            subject_id=no_term_subj["id"],
            schedule_start_time=time(10, 0),
            schedule_end_time=time(11, 0),
            days_of_week=["Tue"],
            semester=sem_no_term,
        )
        resp = self.client.get(f"/api/central/schedule/{no_term_subj['id']}/", **_auth())
        self.assertEqual(resp.status_code, 400)

    def test_schedule_returns_correct_data(self):
        resp = self.client.get(f"/api/central/schedule/{self.subject['id']}/", **_auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["subject_id"], self.subject["id"])
        self.assertEqual(data["subject_name"], "Math 101")
        self.assertIn("term", data)
        self.assertEqual(data["term"]["name"], "Prelim")
        self.assertEqual(data["term"]["start_date"], "2026-08-15")
        self.assertEqual(data["term"]["end_date"], "2026-10-15")
        self.assertIn("sessions", data)
        self.assertGreater(len(data["sessions"]), 0)
        self.assertIn("session_count", data)
        self.assertEqual(data["session_count"], len(data["sessions"]))
        self.assertEqual(data["minutes_per_session"], 90)
        first_session = data["sessions"][0]
        self.assertIn("date", first_session)
        self.assertIn("start_time", first_session)
        self.assertIn("end_time", first_session)
        self.assertIn("minutes", first_session)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_schedule_api --keepdb -v2 2>&1 | tail -20`
Expected: ImportError or 404 (endpoint doesn't exist yet)

- [ ] **Step 3: Write the schedule view**

Create `received_central_content/views/schedule.py`:

```python
from collections import Counter
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from received_central_content.auth import require_central_token
from subject.models.subject_model import Subject
from subject.models.schedule_model import Schedule
from course.models.term_model import Term


@require_GET
@require_central_token
def subject_schedule(request, subject_id):
    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return JsonResponse({"error": "subject_not_found"}, status=404)

    schedule = (
        Schedule.objects
        .filter(subject=subject, is_active_semester=True)
        .select_related("semester")
        .first()
    )

    if not schedule:
        return JsonResponse({"error": "no_active_schedule"}, status=400)

    term = (
        Term.objects
        .filter(semester=schedule.semester)
        .order_by("start_date")
        .first()
    )

    if not term or not term.start_date or not term.end_date:
        return JsonResponse({"error": "no_term_assigned"}, status=400)

    day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
    schedule_days = [day_map[d] for d in schedule.days_of_week if d in day_map]

    sessions = []
    current = term.start_date
    while current <= term.end_date:
        if current.weekday() in schedule_days:
            start_t = schedule.schedule_start_time
            end_t = schedule.schedule_end_time
            start_minutes = start_t.hour * 60 + start_t.minute
            end_minutes = end_t.hour * 60 + end_t.minute
            duration = end_minutes - start_minutes
            sessions.append({
                "date": current.isoformat(),
                "start_time": start_t.strftime("%H:%M"),
                "end_time": end_t.strftime("%H:%M"),
                "minutes": duration,
            })
        current += timedelta(days=1)

    durations = [s["minutes"] for s in sessions]
    mode_minutes = Counter(durations).most_common(1)[0][0] if durations else 0

    return JsonResponse({
        "subject_id": subject.pk,
        "subject_name": subject.subject_name,
        "term": {
            "name": term.term_name,
            "start_date": term.start_date.isoformat(),
            "end_date": term.end_date.isoformat(),
        },
        "sessions": sessions,
        "session_count": len(sessions),
        "minutes_per_session": mode_minutes,
    })
```

- [ ] **Step 4: Register the URL**

In `received_central_content/urls.py`, add the import and path:

```python
from django.urls import path

from received_central_content.views import catalog, ingest, schedule

app_name = "received_central_content"

urlpatterns = [
    path("subjects/", catalog.list_subjects, name="list_subjects"),
    path("ingest/", ingest.ingest_subject, name="ingest_subject"),
    path("ingest/<int:central_id>/", ingest.delete_subject, name="delete_subject"),
    path("schedule/<int:subject_id>/", schedule.subject_schedule, name="subject_schedule"),
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_schedule_api --keepdb -v2 2>&1 | tail -30`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add received_central_content/views/schedule.py received_central_content/tests/test_schedule_api.py received_central_content/urls.py
git commit -m "feat(4b): add school-side schedule API endpoint"
```

---

## Task 2: CurriculumPlan Model

**Files:**
- Create: `central_content/models/curriculum_plan.py`
- Create: `central_content/tests/test_curriculum_plan_model.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/factories.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_curriculum_plan_model.py`:

```python
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from central_content.models import ParsedTextbook, ParsedChapter, CurriculumPlan
from central_content.tests.factories import make_editor, make_publisher, make_subject


def _fake_pdf():
    return SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf")


def _setup_textbook_with_chapters(editor, subject, num_chapters=5):
    tb = ParsedTextbook.objects.create(
        central_subject=subject,
        title="Algebra 101",
        original_file=_fake_pdf(),
        uploaded_by=editor,
        status=ParsedTextbook.Status.TOC_READY,
    )
    for i in range(1, num_chapters + 1):
        ParsedChapter.objects.create(
            textbook=tb,
            chapter_number=i,
            title=f"Chapter {i}",
            start_page=i * 10,
            end_page=i * 10 + 9,
        )
    return tb


class CurriculumPlanModelTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = _setup_textbook_with_chapters(self.editor, self.subject, num_chapters=5)

    def test_create_valid_plan(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2], "title": "Foundations", "description": "Intro"},
                {"week": 2, "chapters": [3], "title": "Middle", "description": "Core"},
                {"week": 3, "chapters": [4, 5], "title": "Advanced", "description": "End"},
            ],
            status=CurriculumPlan.Status.DRAFT,
            generated_by=self.publisher,
        )
        plan.full_clean()
        plan.save()
        self.assertEqual(plan.status, CurriculumPlan.Status.DRAFT)
        self.assertEqual(plan.textbook, self.textbook)
        self.assertEqual(len(plan.plan_data), 3)

    def test_multiple_plans_per_textbook(self):
        for model_key in ["haiku", "sonnet"]:
            CurriculumPlan.objects.create(
                textbook=self.textbook,
                school_subject_id=42,
                session_count=30,
                minutes_per_session=90,
                model_key=model_key,
                plan_data=[
                    {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                    {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
                ],
                generated_by=self.publisher,
            )
        self.assertEqual(self.textbook.plans.count(), 2)

    def test_validation_rejects_duplicate_chapters(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
                {"week": 2, "chapters": [2, 3, 4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_validation_rejects_missing_chapters(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("missing", str(ctx.exception).lower())

    def test_validation_rejects_nonexistent_chapters(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5, 99], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("not exist", str(ctx.exception).lower())

    def test_validation_rejects_nonsequential_weeks(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 3, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("sequential", str(ctx.exception).lower())

    def test_validation_rejects_empty_week(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3, 4, 5], "title": "A", "description": ""},
                {"week": 2, "chapters": [], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("at least one chapter", str(ctx.exception).lower())

    def test_status_draft_to_approved(self):
        plan = CurriculumPlan.objects.create(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        plan.status = CurriculumPlan.Status.APPROVED
        plan.save(update_fields=["status"])
        plan.refresh_from_db()
        self.assertEqual(plan.status, CurriculumPlan.Status.APPROVED)

    def test_status_draft_to_rejected(self):
        plan = CurriculumPlan.objects.create(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        plan.status = CurriculumPlan.Status.REJECTED
        plan.save(update_fields=["status"])
        plan.refresh_from_db()
        self.assertEqual(plan.status, CurriculumPlan.Status.REJECTED)

    def test_cascade_delete_with_textbook(self):
        CurriculumPlan.objects.create(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        self.assertEqual(CurriculumPlan.objects.count(), 1)
        self.textbook.delete()
        self.assertEqual(CurriculumPlan.objects.count(), 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_curriculum_plan_model --keepdb -v2 2>&1 | tail -20`
Expected: ImportError (CurriculumPlan doesn't exist)

- [ ] **Step 3: Create the CurriculumPlan model**

Create `central_content/models/curriculum_plan.py`:

```python
from django.core.exceptions import ValidationError
from django.db import models


class CurriculumPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    textbook = models.ForeignKey(
        "central_content.ParsedTextbook",
        on_delete=models.CASCADE,
        related_name="plans",
    )
    school_subject_id = models.PositiveIntegerField()
    session_count = models.PositiveIntegerField()
    minutes_per_session = models.PositiveIntegerField()
    model_key = models.CharField(max_length=50)
    plan_data = models.JSONField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    generated_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="curriculum_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_curriculum_plan"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Plan for {self.textbook.title} ({self.model_key})"

    def clean(self):
        super().clean()
        if not self.plan_data:
            return
        self._validate_plan_data()

    def _validate_plan_data(self):
        if not isinstance(self.plan_data, list) or len(self.plan_data) == 0:
            raise ValidationError("plan_data must be a non-empty list.")

        textbook_chapter_numbers = set(
            self.textbook.chapters.values_list("chapter_number", flat=True)
        )

        week_numbers = [entry["week"] for entry in self.plan_data]
        expected_weeks = list(range(1, len(self.plan_data) + 1))
        if week_numbers != expected_weeks:
            raise ValidationError(
                f"Weeks must be sequential starting from 1. Got: {week_numbers}"
            )

        all_assigned = []
        for entry in self.plan_data:
            chapters = entry.get("chapters", [])
            if len(chapters) == 0:
                raise ValidationError(
                    f"Week {entry['week']} must have at least one chapter."
                )
            all_assigned.extend(chapters)

        assigned_set = set(all_assigned)
        if len(all_assigned) != len(assigned_set):
            duplicates = [c for c in all_assigned if all_assigned.count(c) > 1]
            raise ValidationError(
                f"Duplicate chapter assignments: {set(duplicates)}"
            )

        nonexistent = assigned_set - textbook_chapter_numbers
        if nonexistent:
            raise ValidationError(
                f"Chapters do not exist in textbook: {nonexistent}"
            )

        missing = textbook_chapter_numbers - assigned_set
        if missing:
            raise ValidationError(
                f"Missing chapters not assigned to any week: {missing}"
            )
```

- [ ] **Step 4: Export the model from `__init__.py`**

In `central_content/models/__init__.py`, add:

```python
from .curriculum_plan import CurriculumPlan
```

And update `__all__` to include `"CurriculumPlan"`.

- [ ] **Step 5: Create and run migration**

Run: `cd ~/classedge && env/bin/python manage.py makemigrations central_content --name curriculum_plan -v0 && env/bin/python manage.py migrate --run-syncdb --keepdb -v0`

- [ ] **Step 6: Add factory helpers**

In `central_content/tests/factories.py`, add these helpers at the end of the file:

```python
def make_textbook(central_subject=None, uploaded_by=None, status=None, num_chapters=5, **kw):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from central_content.models import ParsedTextbook, ParsedChapter

    if status is None:
        from central_content.models import ParsedTextbook as PT
        status = PT.Status.TOC_READY
    if uploaded_by is None:
        uploaded_by = make_editor()
    if central_subject is None:
        central_subject = make_subject(created_by=uploaded_by)
    defaults = {
        "central_subject": central_subject,
        "title": f"Textbook {_next()}",
        "original_file": SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf"),
        "uploaded_by": uploaded_by,
        "status": status,
    }
    defaults.update(kw)
    tb = ParsedTextbook.objects.create(**defaults)
    for i in range(1, num_chapters + 1):
        ParsedChapter.objects.create(
            textbook=tb,
            chapter_number=i,
            title=f"Chapter {i}",
            start_page=i * 10,
            end_page=i * 10 + 9,
        )
    return tb


def make_curriculum_plan(textbook=None, generated_by=None, plan_data=None, **kw):
    from central_content.models import CurriculumPlan
    if generated_by is None:
        generated_by = make_publisher()
    if textbook is None:
        textbook = make_textbook(uploaded_by=make_editor())
    if plan_data is None:
        chapter_numbers = list(
            textbook.chapters.values_list("chapter_number", flat=True)
        )
        mid = len(chapter_numbers) // 2
        plan_data = [
            {"week": 1, "chapters": chapter_numbers[:mid] or chapter_numbers, "title": "Part A", "description": "First half"},
            {"week": 2, "chapters": chapter_numbers[mid:], "title": "Part B", "description": "Second half"},
        ]
        if not chapter_numbers[mid:]:
            plan_data = [plan_data[0]]
    defaults = {
        "textbook": textbook,
        "school_subject_id": 42,
        "session_count": 30,
        "minutes_per_session": 90,
        "model_key": "haiku",
        "plan_data": plan_data,
        "generated_by": generated_by,
    }
    defaults.update(kw)
    return CurriculumPlan.objects.create(**defaults)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_curriculum_plan_model --keepdb -v2 2>&1 | tail -30`
Expected: All 10 tests PASS

- [ ] **Step 8: Commit**

```bash
cd ~/classedge && git add central_content/models/curriculum_plan.py central_content/models/__init__.py central_content/tests/test_curriculum_plan_model.py central_content/tests/factories.py central_content/migrations/
git commit -m "feat(4b): add CurriculumPlan model with validation"
```

---

## Task 3: LLM Module

**Files:**
- Create: `central_content/llm.py`
- Create: `central_content/tests/test_llm.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_llm.py`:

```python
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from central_content.llm import call_curriculum_planner

_LLM_SETTINGS = {
    "CURRICULUM_PLANNER_MODELS": {
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
    },
    "CURRICULUM_PLANNER_DEFAULT_MODEL": "haiku",
}

_VALID_RESPONSE = json.dumps([
    {"week": 1, "chapters": [1, 2], "title": "Foundations", "description": "Intro to real numbers"},
    {"week": 2, "chapters": [3, 4], "title": "Operations", "description": "Basic operations"},
    {"week": 3, "chapters": [5], "title": "Applications", "description": "Word problems"},
])

_CHAPTERS = [
    {"number": 1, "title": "Real Numbers", "start_page": 1, "end_page": 20},
    {"number": 2, "title": "Integers", "start_page": 21, "end_page": 40},
    {"number": 3, "title": "Addition", "start_page": 41, "end_page": 60},
    {"number": 4, "title": "Subtraction", "start_page": 61, "end_page": 80},
    {"number": 5, "title": "Word Problems", "start_page": 81, "end_page": 100},
]


def _mock_anthropic_response(text_content):
    mock_block = MagicMock()
    mock_block.text = text_content
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    return mock_response


@override_settings(**_LLM_SETTINGS)
class CallCurriculumPlannerTests(TestCase):
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_valid_response_parsed(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        result = call_curriculum_planner(
            chapters=_CHAPTERS,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["week"], 1)
        self.assertEqual(result[0]["chapters"], [1, 2])
        self.assertIn("title", result[0])
        self.assertIn("description", result[0])

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_prompt_includes_chapter_info(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        call_curriculum_planner(
            chapters=_CHAPTERS,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
        )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        prompt_text = messages[0]["content"]
        self.assertIn("Real Numbers", prompt_text)
        self.assertIn("30", prompt_text)
        self.assertIn("90", prompt_text)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_uses_correct_model(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response(_VALID_RESPONSE)

        call_curriculum_planner(
            chapters=_CHAPTERS,
            session_count=30,
            minutes_per_session=90,
            model_key="sonnet",
        )

        call_args = mock_client.messages.create.call_args
        model_used = call_args.kwargs.get("model") or call_args[1].get("model")
        self.assertEqual(model_used, "claude-sonnet-4-6")

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    @patch("central_content.llm.anthropic.Anthropic")
    def test_invalid_json_raises(self, MockAnthropic):
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("not json at all")

        with self.assertRaises(ValueError):
            call_curriculum_planner(
                chapters=_CHAPTERS,
                session_count=30,
                minutes_per_session=90,
                model_key="haiku",
            )

    def test_unknown_model_key_raises(self):
        with self.assertRaises(KeyError):
            call_curriculum_planner(
                chapters=_CHAPTERS,
                session_count=30,
                minutes_per_session=90,
                model_key="nonexistent",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_llm --keepdb -v2 2>&1 | tail -20`
Expected: ImportError (llm module doesn't exist)

- [ ] **Step 3: Write the LLM module**

Create `central_content/llm.py`:

```python
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
```

- [ ] **Step 4: Install the anthropic package**

Run: `cd ~/classedge && env/bin/pip install anthropic 2>&1 | tail -5`

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_llm --keepdb -v2 2>&1 | tail -20`
Expected: All 5 tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add central_content/llm.py central_content/tests/test_llm.py
git commit -m "feat(4b): add LLM curriculum planner module"
```

---

## Task 4: Celery Tasks — generate_curriculum_plan and bulk_generate_plans

**Files:**
- Create: `central_content/tests/test_plan_tasks.py`
- Modify: `central_content/tasks.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_plan_tasks.py`:

```python
import json
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import ParsedTextbook, ParsedChapter, CurriculumPlan
from central_content.tests.factories import (
    make_editor, make_publisher, make_subject, make_school, make_binding,
    make_textbook,
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

_VALID_PLAN = [
    {"week": 1, "chapters": [1, 2, 3], "title": "Foundations", "description": "Intro"},
    {"week": 2, "chapters": [4, 5], "title": "Advanced", "description": "More"},
]

_SCHEDULE_RESPONSE = {
    "subject_id": 42,
    "subject_name": "Math 101",
    "term": {"name": "Prelim", "start_date": "2026-08-15", "end_date": "2026-10-15"},
    "sessions": [{"date": "2026-08-16", "start_time": "08:00", "end_time": "09:30", "minutes": 90}] * 30,
    "session_count": 30,
    "minutes_per_session": 90,
}


@override_settings(**_LLM_SETTINGS)
class GenerateCurriculumPlanTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_success_creates_draft_plan(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SCHEDULE_RESPONSE
        mock_get.return_value = mock_resp
        mock_llm.return_value = _VALID_PLAN

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "success")
        plan = CurriculumPlan.objects.get(textbook=self.textbook)
        self.assertEqual(plan.status, CurriculumPlan.Status.DRAFT)
        self.assertEqual(plan.model_key, "haiku")
        self.assertEqual(plan.session_count, 30)
        self.assertEqual(len(plan.plan_data), 2)

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_schedule_fetch_failure(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "not found"
        mock_get.return_value = mock_resp

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "error")
        self.assertIn("schedule", result["detail"].lower())
        self.assertEqual(CurriculumPlan.objects.count(), 0)

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_llm_failure_returns_error(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SCHEDULE_RESPONSE
        mock_get.return_value = mock_resp
        mock_llm.side_effect = ValueError("LLM returned invalid JSON")

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "error")
        self.assertEqual(CurriculumPlan.objects.count(), 0)

    @patch("central_content.tasks.call_curriculum_planner")
    @patch("central_content.tasks.requests.get")
    def test_invalid_plan_retries_then_stores_with_warnings(self, mock_get, mock_llm):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _SCHEDULE_RESPONSE
        mock_get.return_value = mock_resp

        bad_plan = [
            {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
            {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
        ]
        mock_llm.return_value = bad_plan

        from central_content.tasks import generate_curriculum_plan
        result = generate_curriculum_plan(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(mock_llm.call_count, 2)
        plan = CurriculumPlan.objects.get(textbook=self.textbook)
        self.assertEqual(plan.status, CurriculumPlan.Status.DRAFT)


@override_settings(**_LLM_SETTINGS)
class BulkGeneratePlansTaskTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )

    @patch("central_content.tasks.generate_curriculum_plan.delay")
    def test_dispatches_per_textbook(self, mock_delay):
        tb1 = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.TOC_READY,
        )
        tb2 = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.TOC_READY,
        )
        make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            status=ParsedTextbook.Status.UPLOADING,
        )

        from central_content.tasks import bulk_generate_plans
        result = bulk_generate_plans(
            self.subject.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

        self.assertEqual(mock_delay.call_count, 2)
        self.assertEqual(result["dispatched"], 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_plan_tasks --keepdb -v2 2>&1 | tail -20`
Expected: ImportError (tasks don't exist yet)

- [ ] **Step 3: Add the Celery tasks**

Append to `central_content/tasks.py` (after the existing `parse_single_chapter` task):

```python
@shared_task
def generate_curriculum_plan(textbook_id, binding_id, model_key, triggered_by_id):
    from central_content.llm import call_curriculum_planner
    from central_content.models import (
        CentralStaff, CurriculumPlan, ParsedTextbook, SchoolSubjectBinding,
    )

    try:
        textbook = ParsedTextbook.objects.get(pk=textbook_id)
        binding = SchoolSubjectBinding.objects.select_related("target_school").get(pk=binding_id)
        triggered_by = CentralStaff.objects.get(pk=triggered_by_id)
    except (ParsedTextbook.DoesNotExist, SchoolSubjectBinding.DoesNotExist, CentralStaff.DoesNotExist) as exc:
        return {"status": "error", "detail": str(exc)}

    schedule_url = (
        f"{binding.target_school.base_url}/api/central/schedule/{binding.school_subject_id}/"
    )
    try:
        resp = requests.get(
            schedule_url,
            headers={"Authorization": f"Bearer {binding.target_school.api_token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return {"status": "error", "detail": f"Schedule fetch failed ({resp.status_code}): {resp.text[:500]}"}
        schedule_data = resp.json()
    except requests.RequestException as exc:
        return {"status": "error", "detail": f"Schedule fetch error: {exc}"}

    chapters = [
        {
            "number": ch.chapter_number,
            "title": ch.title,
            "start_page": ch.start_page,
            "end_page": ch.end_page,
        }
        for ch in textbook.chapters.all()
    ]

    session_count = schedule_data["session_count"]
    minutes_per_session = schedule_data["minutes_per_session"]

    plan_data = None
    for attempt in range(2):
        try:
            plan_data = call_curriculum_planner(
                chapters=chapters,
                session_count=session_count,
                minutes_per_session=minutes_per_session,
                model_key=model_key,
            )
        except (ValueError, Exception) as exc:
            if attempt == 1:
                return {"status": "error", "detail": f"LLM error: {exc}"}
            continue

        try:
            test_plan = CurriculumPlan(
                textbook=textbook,
                school_subject_id=binding.school_subject_id,
                session_count=session_count,
                minutes_per_session=minutes_per_session,
                model_key=model_key,
                plan_data=plan_data,
                generated_by=triggered_by,
            )
            test_plan._validate_plan_data()
            break
        except Exception:
            if attempt == 1:
                break
            continue

    if plan_data is None:
        return {"status": "error", "detail": "LLM failed to produce a plan"}

    plan = CurriculumPlan.objects.create(
        textbook=textbook,
        school_subject_id=binding.school_subject_id,
        session_count=session_count,
        minutes_per_session=minutes_per_session,
        model_key=model_key,
        plan_data=plan_data,
        generated_by=triggered_by,
    )

    return {"status": "success", "plan_id": plan.pk}


@shared_task
def bulk_generate_plans(central_subject_id, binding_id, model_key, triggered_by_id):
    from central_content.models import CentralSubject, ParsedTextbook

    try:
        subject = CentralSubject.objects.get(pk=central_subject_id)
    except CentralSubject.DoesNotExist:
        return {"status": "error", "detail": "subject_not_found"}

    textbooks = subject.textbooks.filter(status=ParsedTextbook.Status.TOC_READY)
    count = 0
    for tb in textbooks:
        generate_curriculum_plan.delay(tb.pk, binding_id, model_key, triggered_by_id)
        count += 1

    return {"status": "success", "dispatched": count}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_plan_tasks --keepdb -v2 2>&1 | tail -30`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add central_content/tasks.py central_content/tests/test_plan_tasks.py
git commit -m "feat(4b): add generate_curriculum_plan and bulk_generate_plans Celery tasks"
```

---

## Task 5: Plan Views (generate, detail/edit, approve/reject, bulk-run)

**Files:**
- Create: `central_content/views/plans.py`
- Create: `central_content/tests/test_plan_views.py`
- Modify: `central_content/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_plan_views.py`:

```python
import json
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import (
    CurriculumPlan, ParsedTextbook, ParsedChapter,
)
from central_content.tests.factories import (
    make_editor, make_publisher, make_reviewer, make_subject,
    make_school, make_binding, make_textbook, make_curriculum_plan,
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
        "sonnet": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "api_key_env": "ANTHROPIC_API_KEY",
        },
    },
    CURRICULUM_PLANNER_DEFAULT_MODEL="haiku",
)


@override_settings(**_OVERRIDES)
class PlanGenerateViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_generate_page_renders(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/generate"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "haiku")
        self.assertContains(resp, "sonnet")

    @patch("central_content.views.plans.generate_curriculum_plan.delay")
    def test_post_triggers_task_and_redirects(self, mock_delay):
        mock_delay.return_value = MagicMock(id="task-123")
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/generate",
            {"binding_id": self.binding.pk, "model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 302)
        mock_delay.assert_called_once_with(
            self.textbook.pk, self.binding.pk, "haiku", self.publisher.pk,
        )

    def test_editor_cannot_access_generate(self):
        self._login("ed@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/generate"
        )
        self.assertIn(resp.status_code, [302, 403])


@override_settings(**_OVERRIDES)
class PlanDetailViewTests(TestCase):
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
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_detail_renders(self):
        self._login("pub@example.com")
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Week 1")
        self.assertContains(resp, "Week 2")


@override_settings(**_OVERRIDES)
class PlanEditViewTests(TestCase):
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
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_save_valid_edit(self):
        self._login("pub@example.com")
        new_plan_data = [
            {"week": 1, "chapters": [1], "title": "Intro", "description": "Start"},
            {"week": 2, "chapters": [2, 3], "title": "Core", "description": "Middle"},
            {"week": 3, "chapters": [4, 5], "title": "End", "description": "Finish"},
        ]
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/edit",
            {"plan_data": json.dumps(new_plan_data)},
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(len(self.plan.plan_data), 3)

    def test_save_invalid_edit_returns_error(self):
        self._login("pub@example.com")
        bad_plan_data = [
            {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
        ]
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/edit",
            {"plan_data": json.dumps(bad_plan_data)},
        )
        self.assertEqual(resp.status_code, 400)

    def test_cannot_edit_approved_plan(self):
        self._login("pub@example.com")
        self.plan.status = CurriculumPlan.Status.APPROVED
        self.plan.save(update_fields=["status"])
        new_plan_data = [
            {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
            {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
        ]
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/edit",
            {"plan_data": json.dumps(new_plan_data)},
        )
        self.assertEqual(resp.status_code, 400)


@override_settings(**_OVERRIDES)
class PlanApproveRejectViewTests(TestCase):
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
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    def test_approve_plan(self):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/approve"
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, CurriculumPlan.Status.APPROVED)

    def test_reject_plan(self):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/reject"
        )
        self.assertEqual(resp.status_code, 302)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.status, CurriculumPlan.Status.REJECTED)

    def test_cannot_approve_already_approved(self):
        self._login("pub@example.com")
        self.plan.status = CurriculumPlan.Status.APPROVED
        self.plan.save(update_fields=["status"])
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/approve"
        )
        self.assertEqual(resp.status_code, 400)

    def test_editor_cannot_approve(self):
        self._login("ed@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/plans/{self.plan.pk}/approve"
        )
        self.assertIn(resp.status_code, [302, 403])


@override_settings(**_OVERRIDES)
class BulkRunViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(email="pub@example.com", password="testpass")
        self.editor = make_editor(email="ed@example.com", password="testpass")
        self.subject = make_subject(created_by=self.editor)
        self.school = make_school(created_by=self.publisher)
        self.binding = make_binding(
            central_subject=self.subject,
            target_school=self.school,
            school_subject_id=42,
            bound_by=self.publisher,
        )

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "testpass"})

    @patch("central_content.views.plans.bulk_generate_plans.delay")
    def test_bulk_run_triggers_task(self, mock_delay):
        self._login("pub@example.com")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/plans/bulk-generate",
            {"binding_id": self.binding.pk, "model_key": "haiku"},
        )
        self.assertEqual(resp.status_code, 302)
        mock_delay.assert_called_once_with(
            self.subject.pk, self.binding.pk, "haiku", self.publisher.pk,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_plan_views --keepdb -v2 2>&1 | tail -20`
Expected: ImportError or 404 (views/URLs don't exist)

- [ ] **Step 3: Create the plan views**

Create `central_content/views/plans.py`:

```python
import json

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from central_content.models import (
    CentralSubject, CurriculumPlan, ParsedTextbook, SchoolSubjectBinding,
)
from central_content.permissions import central_role_required
from central_content.tasks import generate_curriculum_plan, bulk_generate_plans


@central_role_required("publisher")
def plan_generate(request, subject_id, textbook_id):
    textbook = get_object_or_404(
        ParsedTextbook.objects.select_related("central_subject"),
        pk=textbook_id,
        central_subject_id=subject_id,
    )
    subject = textbook.central_subject
    bindings = SchoolSubjectBinding.objects.filter(
        central_subject=subject,
    ).select_related("target_school")
    model_keys = list(settings.CURRICULUM_PLANNER_MODELS.keys())

    if request.method == "POST":
        binding_id = request.POST.get("binding_id")
        model_key = request.POST.get("model_key", settings.CURRICULUM_PLANNER_DEFAULT_MODEL)
        if not binding_id:
            return HttpResponseBadRequest("binding_id is required")
        generate_curriculum_plan.delay(
            textbook.pk, int(binding_id), model_key, request.user.pk,
        )
        return HttpResponseRedirect(
            f"/subjects/{subject_id}/textbooks/{textbook_id}/"
        )

    return render(
        request,
        "central_content/plans/generate.html",
        {
            "subject": subject,
            "textbook": textbook,
            "bindings": bindings,
            "model_keys": model_keys,
        },
    )


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

    return render(
        request,
        "central_content/plans/detail.html",
        {
            "subject": plan.textbook.central_subject,
            "textbook": plan.textbook,
            "plan": plan,
        },
    )


@central_role_required("publisher", "reviewer")
@require_POST
def plan_edit(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan,
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.DRAFT:
        return HttpResponseBadRequest("Only draft plans can be edited.")

    try:
        new_data = json.loads(request.POST.get("plan_data", "[]"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON.")

    plan.plan_data = new_data
    try:
        plan._validate_plan_data()
    except Exception as exc:
        return HttpResponseBadRequest(str(exc))

    plan.save(update_fields=["plan_data", "updated_at"])
    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/"
    )


@central_role_required("publisher", "reviewer")
@require_POST
def plan_approve(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan,
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.DRAFT:
        return HttpResponseBadRequest("Only draft plans can be approved.")
    plan.status = CurriculumPlan.Status.APPROVED
    plan.save(update_fields=["status", "updated_at"])
    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/"
    )


@central_role_required("publisher", "reviewer")
@require_POST
def plan_reject(request, subject_id, textbook_id, plan_id):
    plan = get_object_or_404(
        CurriculumPlan,
        pk=plan_id,
        textbook_id=textbook_id,
        textbook__central_subject_id=subject_id,
    )
    if plan.status != CurriculumPlan.Status.DRAFT:
        return HttpResponseBadRequest("Only draft plans can be rejected.")
    plan.status = CurriculumPlan.Status.REJECTED
    plan.save(update_fields=["status", "updated_at"])
    return HttpResponseRedirect(
        f"/subjects/{subject_id}/textbooks/{textbook_id}/plans/{plan_id}/"
    )


@central_role_required("publisher")
@require_POST
def bulk_generate(request, subject_id):
    subject = get_object_or_404(CentralSubject, pk=subject_id)
    binding_id = request.POST.get("binding_id")
    model_key = request.POST.get("model_key", settings.CURRICULUM_PLANNER_DEFAULT_MODEL)
    if not binding_id:
        return HttpResponseBadRequest("binding_id is required")
    bulk_generate_plans.delay(
        subject.pk, int(binding_id), model_key, request.user.pk,
    )
    return HttpResponseRedirect(f"/subjects/{subject_id}/")
```

- [ ] **Step 4: Register URL patterns**

In `central_content/urls.py`, add the plan imports and paths. Add these after the textbook URL patterns:

```python
from central_content.views import plans as plan_views
```

Add these URL patterns (within the `urlpatterns` list, after the textbook patterns):

```python
    # Plans
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/generate", plan_views.plan_generate, name="plan_generate"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/", plan_views.plan_detail, name="plan_detail"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/edit", plan_views.plan_edit, name="plan_edit"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/approve", plan_views.plan_approve, name="plan_approve"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/plans/<int:plan_id>/reject", plan_views.plan_reject, name="plan_reject"),
    path("subjects/<int:subject_id>/plans/bulk-generate", plan_views.bulk_generate, name="bulk_generate"),
```

- [ ] **Step 5: Create plan templates**

Create `central_content/templates/central_content/plans/generate.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Generate Plan — {{ textbook.title }}{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">Generate Curriculum Plan</h1>
<p class="text-gray-600 mb-6">{{ textbook.title }} · {{ textbook.chapters.count }} chapters</p>

<form method="post" class="bg-white p-6 rounded shadow max-w-lg">
    {% csrf_token %}
    <div class="mb-4">
        <label class="block text-sm font-medium mb-1">Target School + Subject</label>
        <select name="binding_id" required class="w-full border rounded px-3 py-2">
            {% for b in bindings %}
            <option value="{{ b.pk }}">{{ b.target_school.name }} — {{ b.school_subject_name }}</option>
            {% empty %}
            <option disabled>No school bindings. Bind a school first.</option>
            {% endfor %}
        </select>
    </div>
    <div class="mb-6">
        <label class="block text-sm font-medium mb-1">LLM Model</label>
        <select name="model_key" class="w-full border rounded px-3 py-2">
            {% for key in model_keys %}
            <option value="{{ key }}">{{ key }}</option>
            {% endfor %}
        </select>
    </div>
    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"{% if not bindings %} disabled{% endif %}>
        Generate Plan
    </button>
</form>

<div class="mt-4">
    <a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/" class="text-blue-700">&larr; Back to textbook</a>
</div>
{% endblock %}
```

Create `central_content/templates/central_content/plans/detail.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Plan — {{ textbook.title }}{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-4">
    <div>
        <h1 class="text-2xl font-semibold">Curriculum Plan</h1>
        <p class="text-gray-600">{{ textbook.title }} · {{ plan.model_key }} · {{ plan.session_count }} sessions × {{ plan.minutes_per_session }}min</p>
    </div>
    <span class="px-3 py-1 rounded text-sm {% if plan.status == 'approved' %}bg-green-100 text-green-800{% elif plan.status == 'rejected' %}bg-red-100 text-red-800{% else %}bg-yellow-100 text-yellow-800{% endif %}">
        {{ plan.get_status_display }}
    </span>
</div>

<div class="bg-white rounded shadow overflow-hidden mb-6">
    <table class="w-full text-sm">
        <thead>
            <tr class="text-left text-gray-500 border-b bg-gray-50">
                <th class="py-3 px-4 w-16">Week</th>
                <th class="py-3 px-4">Chapters</th>
                <th class="py-3 px-4">Title</th>
                <th class="py-3 px-4">Description</th>
            </tr>
        </thead>
        <tbody id="plan-body">
        {% for week in plan.plan_data %}
            <tr class="border-t">
                <td class="py-3 px-4 font-medium">{{ week.week }}</td>
                <td class="py-3 px-4">
                    {% for title in week.chapter_titles %}
                    <span class="inline-block bg-blue-50 text-blue-700 rounded px-2 py-0.5 text-xs mr-1 mb-1">{{ title }}</span>
                    {% endfor %}
                </td>
                <td class="py-3 px-4">{{ week.title }}</td>
                <td class="py-3 px-4 text-gray-600">{{ week.description }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>

{% if plan.status == "draft" %}
<div class="flex gap-3 mb-6">
    <form method="post" action="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/approve">
        {% csrf_token %}
        <button type="submit" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Approve</button>
    </form>
    <form method="post" action="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/reject">
        {% csrf_token %}
        <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700">Reject</button>
    </form>
    <a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/generate" class="border px-4 py-2 rounded hover:bg-gray-50">Regenerate with different model</a>
</div>

<details class="bg-white p-4 rounded shadow mb-6">
    <summary class="font-semibold cursor-pointer">Edit Plan (advanced)</summary>
    <form method="post" action="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ plan.id }}/edit" class="mt-4">
        {% csrf_token %}
        <textarea name="plan_data" rows="15" class="w-full border rounded px-3 py-2 font-mono text-sm">{{ plan.plan_data|safe }}</textarea>
        <p class="text-xs text-gray-500 mt-1">Edit the JSON directly. Every chapter must be assigned to exactly one week.</p>
        <button type="submit" class="mt-3 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Save Changes</button>
    </form>
</details>
{% endif %}

<div class="text-sm text-gray-500 mb-4">
    Generated by {{ plan.generated_by.full_name }} · {{ plan.created_at|date:"M d, Y H:i" }}
</div>

<a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/" class="text-blue-700">&larr; Back to textbook</a>
{% endblock %}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd ~/classedge && env/bin/python manage.py test central_content.tests.test_plan_views --keepdb -v2 2>&1 | tail -30`
Expected: All 12 tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add central_content/views/plans.py central_content/tests/test_plan_views.py central_content/urls.py central_content/templates/central_content/plans/
git commit -m "feat(4b): add plan views, templates, and URL routes"
```

---

## Task 6: Update Textbook Detail and Subject Detail Templates

**Files:**
- Modify: `central_content/templates/central_content/textbooks/detail.html`
- Modify: `central_content/templates/central_content/subjects/detail.html`
- Modify: `central_content/views/textbooks.py`
- Modify: `central_content/views/subjects.py`

- [ ] **Step 1: Update textbook detail view to pass plans and bindings**

In `central_content/views/textbooks.py`, update the `textbook_detail` function to also pass `plans` and show the generate button. The full updated function:

```python
@central_role_required("publisher", "editor", "reviewer")
def textbook_detail(request, subject_id: int, textbook_id: int):
    textbook = get_object_or_404(
        ParsedTextbook.objects.select_related("central_subject", "uploaded_by"),
        pk=textbook_id,
        central_subject_id=subject_id,
    )
    chapters = textbook.chapters.all()
    plans = textbook.plans.select_related("generated_by").all()

    return render(
        request,
        "central_content/textbooks/detail.html",
        {
            "textbook": textbook,
            "subject": textbook.central_subject,
            "chapters": chapters,
            "plans": plans,
        },
    )
```

Add `CurriculumPlan` to the existing imports if needed (it's accessed through the ORM so it's not strictly required, but it's good practice). Actually, since we access `textbook.plans` via the related manager, no explicit import is needed.

- [ ] **Step 2: Update the textbook detail template**

Replace the full content of `central_content/templates/central_content/textbooks/detail.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{{ textbook.title }}{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-4">
    <div>
        <h1 class="text-2xl font-semibold">{{ textbook.title }}</h1>
        <p class="text-gray-600">{{ subject.subject_name }}</p>
    </div>
    {% include "central_content/textbooks/status_badge.html" %}
</div>

<div class="mb-6 bg-white p-4 rounded shadow">
    <h2 class="font-semibold mb-2">Details</h2>
    <p class="text-sm text-gray-500">Uploaded by {{ textbook.uploaded_by.full_name }} · {{ textbook.created_at|date:"M d, Y H:i" }}</p>
    {% if textbook.toc_data %}
    <p class="text-sm text-gray-500 mt-1">{{ textbook.toc_data.total_pages }} pages · {{ textbook.chapters.count }} chapters</p>
    {% endif %}
</div>

{% if textbook.status == "toc_ready" %}
<div class="bg-white p-4 rounded shadow">
    <h2 class="font-semibold mb-2">Chapters</h2>
    <table class="w-full text-sm">
        <thead>
            <tr class="text-left text-gray-500 border-b">
                <th class="py-2 w-12">#</th>
                <th class="py-2">Title</th>
                <th class="py-2 w-24">Pages</th>
                <th class="py-2 w-24">Status</th>
            </tr>
        </thead>
        <tbody>
        {% for ch in chapters %}
            <tr class="border-t">
                <td class="py-2">{{ ch.chapter_number }}</td>
                <td class="py-2">{{ ch.title }}</td>
                <td class="py-2 text-gray-500">{{ ch.start_page }}–{{ ch.end_page }}</td>
                <td class="py-2">
                    {% if ch.status == "complete" %}
                    <span class="text-green-700">Complete</span>
                    {% elif ch.status == "parsing" %}
                    <span class="text-amber-700">Parsing...</span>
                    {% elif ch.status == "failed" %}
                    <span class="text-red-700" title="{{ ch.error_message }}">Failed</span>
                    {% else %}
                    <span class="text-gray-500">Pending</span>
                    {% endif %}
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>

<div class="bg-white p-4 rounded shadow mt-6">
    <div class="flex justify-between items-center mb-2">
        <h2 class="font-semibold">Curriculum Plans</h2>
        <a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/generate" class="text-blue-700">+ Generate plan</a>
    </div>
    <ul>
    {% for p in plans %}
        <li class="border-t py-2 flex justify-between items-center">
            <a href="/subjects/{{ subject.id }}/textbooks/{{ textbook.id }}/plans/{{ p.id }}/" class="text-blue-700">
                {{ p.model_key }} · {{ p.created_at|date:"M d, Y H:i" }}
            </a>
            <span class="text-xs px-2 py-0.5 rounded {% if p.status == 'approved' %}bg-green-100 text-green-800{% elif p.status == 'rejected' %}bg-red-100 text-red-800{% else %}bg-yellow-100 text-yellow-800{% endif %}">
                {{ p.get_status_display }}
            </span>
        </li>
    {% empty %}
        <li class="text-gray-500 py-2">No plans yet.</li>
    {% endfor %}
    </ul>
</div>

{% elif textbook.status == "failed" %}
<div class="bg-red-50 border border-red-200 p-4 rounded">
    <p class="text-red-800 font-medium">Parsing failed</p>
    <p class="text-red-700 text-sm mt-1">{{ textbook.error_message }}</p>
</div>
{% endif %}

<div class="mt-4">
    <a href="/subjects/{{ subject.id }}/" class="text-blue-700">&larr; Back to subject</a>
</div>
{% endblock %}
```

- [ ] **Step 3: Update subject detail view to pass bindings**

In `central_content/views/subjects.py`, update the `subject_detail` function to also pass `bindings`:

```python
@central_role_required(*_ALL_ROLES)
def subject_detail(request, subject_id: int):
    subj = get_object_or_404(
        CentralSubject.objects.prefetch_related("modules", "activities", "textbooks"),
        pk=subject_id,
    )
    bindings = subj.school_bindings.select_related("target_school").all()
    return render(
        request,
        "central_content/subjects/detail.html",
        {
            "subject": subj,
            "modules": subj.modules.all(),
            "activities": subj.activities.all(),
            "textbooks": subj.textbooks.all(),
            "bindings": bindings,
        },
    )
```

Add `SchoolSubjectBinding` to imports (actually we access it via `subj.school_bindings` so no import needed).

- [ ] **Step 4: Update the subject detail template**

Add the bulk-generate section. After the Textbooks section closing `</div>` tag, before `{% endblock %}`, add:

```html
{% if bindings %}
<div class="bg-white p-4 rounded shadow mt-6">
    <h2 class="font-semibold mb-3">Bulk Generate Plans</h2>
    <p class="text-sm text-gray-600 mb-3">Generate curriculum plans for all TOC-ready textbooks in this subject.</p>
    <form method="post" action="/subjects/{{ subject.id }}/plans/bulk-generate" class="flex gap-3 items-end">
        {% csrf_token %}
        <div>
            <label class="block text-xs text-gray-500 mb-1">School Binding</label>
            <select name="binding_id" class="border rounded px-3 py-1.5 text-sm">
                {% for b in bindings %}
                <option value="{{ b.pk }}">{{ b.target_school.name }} — {{ b.school_subject_name }}</option>
                {% endfor %}
            </select>
        </div>
        <div>
            <label class="block text-xs text-gray-500 mb-1">Model</label>
            <select name="model_key" class="border rounded px-3 py-1.5 text-sm">
                <option value="haiku">haiku</option>
                <option value="sonnet">sonnet</option>
            </select>
        </div>
        <button type="submit" class="bg-blue-600 text-white px-4 py-1.5 rounded text-sm hover:bg-blue-700">Generate All</button>
    </form>
</div>
{% endif %}
```

- [ ] **Step 5: Run the full test suite to make sure nothing broke**

Run: `cd ~/classedge && env/bin/python manage.py test central_content received_central_content --keepdb -v2 2>&1 | tail -30`
Expected: All tests PASS (176 prior + new tests)

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add central_content/views/textbooks.py central_content/views/subjects.py central_content/templates/central_content/textbooks/detail.html central_content/templates/central_content/subjects/detail.html
git commit -m "feat(4b): add plan links to textbook detail + bulk generate to subject detail"
```

---

## Task 7: Full Integration Test Run

- [ ] **Step 1: Run the complete test suite**

Run: `cd ~/classedge && env/bin/python manage.py test central_content received_central_content --keepdb -v2 2>&1 | tail -40`
Expected: All tests PASS

- [ ] **Step 2: Run Django system check**

Run: `cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central env/bin/python manage.py check 2>&1`
Expected: `System check identified no issues.`

- [ ] **Step 3: Verify migration state**

Run: `cd ~/classedge && env/bin/python manage.py showmigrations central_content 2>&1 | tail -10`
Expected: All migrations applied (with `[X]`)

- [ ] **Step 4: Final commit if any fixes needed**

If any fixes were needed, commit them:
```bash
cd ~/classedge && git add -A && git commit -m "fix(4b): address integration test findings"
```

---

## Summary

| Task | What it builds | Tests added |
|------|---------------|-------------|
| 1 | School-side schedule API | 4 tests |
| 2 | CurriculumPlan model + factories | 10 tests |
| 3 | LLM module (Anthropic caller) | 5 tests |
| 4 | Celery tasks (generate + bulk) | 5 tests |
| 5 | Plan views + templates + URLs | 12 tests |
| 6 | Updated textbook/subject detail UI | (covered by existing view tests) |
| 7 | Full integration verification | — |

**Total new tests: ~36**
