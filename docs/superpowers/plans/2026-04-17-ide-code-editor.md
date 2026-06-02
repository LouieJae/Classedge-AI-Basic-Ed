# IDE Code Editor + Execution Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a browser-based code editor (Monaco) with sandboxed execution (Judge0) that lets IT students write, run, and auto-grade Python and JavaScript code within the existing Activity system.

**Architecture:** New `ide/` Django app with `CodingExercise` (OneToOne to Activity) and `CodeSubmission` models. Judge0 REST client sends code to a self-hosted Docker sandbox. Celery task handles async execution and scoring. Monaco Editor loaded via CDN. Results update `StudentActivity` for gradebook integration.

**Tech Stack:** Django 5, Celery, Judge0 (Docker), Monaco Editor (CDN), existing gamification `award_xp` service

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `ide/__init__.py` | App package |
| `ide/apps.py` | App config |
| `ide/models.py` | CodingExercise + CodeSubmission |
| `ide/judge0_client.py` | Judge0 REST API client |
| `ide/tasks.py` | Celery task for async code execution |
| `ide/views.py` | Student + teacher views |
| `ide/forms.py` | Teacher exercise setup form |
| `ide/urls.py` | URL patterns |
| `ide/templates/ide/exercise_detail.html` | Monaco editor page |
| `ide/templates/ide/exercise_setup.html` | Teacher setup/edit form |
| `ide/tests/__init__.py` | Test package |
| `ide/tests/test_models.py` | Model tests |
| `ide/tests/test_judge0_client.py` | Judge0 client tests (mocked) |
| `ide/tests/test_views.py` | View tests |
| `ide/tests/test_tasks.py` | Celery task tests (mocked) |
| `ide/migrations/0001_initial.py` | Auto-generated |
| `ide/migrations/0002_seed_coding_activity_type.py` | Seed "Coding" ActivityType |
| `docker-compose.judge0.yml` | Judge0 deployment config |

### Modified files

| File | Change |
|------|--------|
| `lms/settings.py` | Add `'ide'` to INSTALLED_APPS, add JUDGE0_* settings |
| `lms/urls.py` | Include `ide.urls` |
| `activity/templates/activity/activities/activity_detail.html` | Add "Open Code Editor" / "Setup Test Cases" link |

---

## Task 1: App Scaffold + Models

**Files:**
- Create: `ide/__init__.py`, `ide/apps.py`, `ide/models.py`
- Create: `ide/tests/__init__.py`, `ide/tests/test_models.py`
- Modify: `lms/settings.py`

- [ ] **Step 1: Create app package**

Create `ide/__init__.py` (empty).

Create `ide/apps.py`:
```python
from django.apps import AppConfig


class IdeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ide"
```

Create `ide/tests/__init__.py` (empty).

- [ ] **Step 2: Register app + settings**

In `lms/settings.py`, add `'ide'` to INSTALLED_APPS after `'gamification'`.

Add at the end of the file:
```python
# IDE / Judge0
JUDGE0_API_URL = os.getenv("JUDGE0_API_URL", "http://localhost:2358")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY", "")
```

- [ ] **Step 3: Create models**

Create `ide/models.py`:
```python
from django.conf import settings
from django.db import models


class CodingExercise(models.Model):
    LANGUAGE_CHOICES = [
        ("python", "Python 3"),
        ("javascript", "JavaScript (Node.js)"),
    ]
    activity = models.OneToOneField(
        "activity.Activity",
        on_delete=models.CASCADE,
        related_name="coding_exercise",
    )
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    starter_code = models.TextField(blank=True, default="")
    solution_code = models.TextField(blank=True, default="")
    test_cases = models.JSONField()
    time_limit_seconds = models.PositiveSmallIntegerField(default=5)
    memory_limit_kb = models.PositiveIntegerField(default=256000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.activity.activity_name} ({self.get_language_display()})"


class CodeSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("error", "Error"),
    ]
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_submissions",
    )
    exercise = models.ForeignKey(CodingExercise, on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    result_json = models.JSONField(default=dict)
    score = models.FloatField(null=True)
    execution_time_ms = models.PositiveIntegerField(null=True)
    memory_used_kb = models.PositiveIntegerField(null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "exercise"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.student.username} — {self.exercise} ({self.status})"
```

- [ ] **Step 4: Generate and apply migration**

Run:
```bash
cd ~/classedge && env/bin/python manage.py makemigrations ide
env/bin/python manage.py migrate ide 2>&1 | tail -5
```

- [ ] **Step 5: Write model tests**

Create `ide/tests/test_models.py`:
```python
from django.test import TestCase
from django.db import IntegrityError

from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from course.models.semester_model import Semester
from course.models.term_model import Term
from ide.models import CodingExercise, CodeSubmission
from datetime import date


class CodingExerciseTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="ide_teacher", role_name="teacher")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Add Two Numbers",
            activity_type=self.activity_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )

    def test_create_exercise(self):
        ex = CodingExercise.objects.create(
            activity=self.activity,
            language="python",
            starter_code="def add(a, b):\n    pass",
            test_cases=[
                {"input": "2 3", "expected_output": "5", "label": "Test 1"},
                {"input": "0 0", "expected_output": "0", "label": "Test 2"},
            ],
        )
        self.assertEqual(ex.language, "python")
        self.assertEqual(len(ex.test_cases), 2)
        self.assertEqual(ex.time_limit_seconds, 5)

    def test_one_to_one_constraint(self):
        CodingExercise.objects.create(
            activity=self.activity, language="python",
            test_cases=[{"input": "", "expected_output": "", "label": "T1"}],
        )
        with self.assertRaises(IntegrityError):
            CodingExercise.objects.create(
                activity=self.activity, language="javascript",
                test_cases=[{"input": "", "expected_output": "", "label": "T1"}],
            )


class CodeSubmissionTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="ide_student", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem2", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim2", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Hello World",
            activity_type=self.activity_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            test_cases=[{"input": "", "expected_output": "Hello", "label": "T1"}],
        )

    def test_create_submission(self):
        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code='print("Hello")', language="python",
        )
        self.assertEqual(sub.status, "pending")
        self.assertIsNone(sub.score)
        self.assertEqual(sub.result_json, {})

    def test_completed_submission(self):
        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code='print("Hello")', language="python",
            status="completed", score=1.0,
            result_json={"tests": [{"label": "T1", "passed": True}]},
            execution_time_ms=50, memory_used_kb=8000,
        )
        self.assertEqual(sub.score, 1.0)
        self.assertEqual(sub.execution_time_ms, 50)
```

- [ ] **Step 6: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ide.tests.test_models --keepdb -v2`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add ide/ && git add -f lms/settings.py
git commit -m "feat(ide): add app scaffold with CodingExercise and CodeSubmission models"
```

---

## Task 2: Judge0 Client

**Files:**
- Create: `ide/judge0_client.py`
- Create: `ide/tests/test_judge0_client.py`

- [ ] **Step 1: Write client tests**

Create `ide/tests/test_judge0_client.py`:
```python
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings

from ide.judge0_client import submit_code, Judge0Error, LANGUAGE_IDS


@override_settings(JUDGE0_API_URL="http://judge0-test:2358", JUDGE0_API_KEY="test-key")
class Judge0ClientTests(TestCase):
    @patch("ide.judge0_client.requests.post")
    def test_submit_code_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": {"id": 3, "description": "Accepted"},
            "stdout": "5\n",
            "stderr": None,
            "time": "0.01",
            "memory": 8000,
            "compile_output": None,
        }
        mock_post.return_value = mock_resp

        result = submit_code("print(2+3)", "python", stdin="")
        self.assertEqual(result["status"]["id"], 3)
        self.assertEqual(result["stdout"], "5\n")

        call_args = mock_post.call_args
        self.assertIn("language_id", call_args[1]["json"])
        self.assertEqual(call_args[1]["json"]["language_id"], LANGUAGE_IDS["python"])

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_with_stdin(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": {"id": 3}, "stdout": "5\n", "stderr": None,
            "time": "0.02", "memory": 9000, "compile_output": None,
        }
        mock_post.return_value = mock_resp

        result = submit_code("print(input())", "python", stdin="5")
        call_json = mock_post.call_args[1]["json"]
        self.assertEqual(call_json["stdin"], "5")

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_timeout(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": {"id": 5, "description": "Time Limit Exceeded"},
            "stdout": None, "stderr": None, "time": "5.0", "memory": 0,
            "compile_output": None,
        }
        mock_post.return_value = mock_resp

        result = submit_code("while True: pass", "python")
        self.assertEqual(result["status"]["id"], 5)

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.raise_for_status.side_effect = Exception("500 Server Error")
        mock_post.return_value = mock_resp

        with self.assertRaises(Judge0Error):
            submit_code("print(1)", "python")

    def test_language_ids_mapping(self):
        self.assertEqual(LANGUAGE_IDS["python"], 71)
        self.assertEqual(LANGUAGE_IDS["javascript"], 63)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test ide.tests.test_judge0_client --keepdb -v2 2>&1 | tail -10`
Expected: ImportError

- [ ] **Step 3: Write the Judge0 client**

Create `ide/judge0_client.py`:
```python
import requests
from django.conf import settings


LANGUAGE_IDS = {
    "python": 71,
    "javascript": 63,
}


class Judge0Error(Exception):
    """Raised when Judge0 API returns an error."""
    pass


def submit_code(source_code, language, stdin="", time_limit=5, memory_limit=256000):
    """Submit code to Judge0 for execution. Blocks until result is ready.

    Returns parsed JSON response with status, stdout, stderr, time, memory.
    Raises Judge0Error on HTTP errors or connection failures.
    """
    api_url = settings.JUDGE0_API_URL
    api_key = getattr(settings, "JUDGE0_API_KEY", "")

    language_id = LANGUAGE_IDS.get(language)
    if not language_id:
        raise Judge0Error(f"Unsupported language: {language}")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Auth-Token"] = api_key

    payload = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
        "cpu_time_limit": time_limit,
        "memory_limit": memory_limit,
        "wall_time_limit": time_limit * 2,
    }

    try:
        resp = requests.post(
            f"{api_url}/submissions/?base64_encoded=false&wait=true",
            json=payload,
            headers=headers,
            timeout=time_limit * 3 + 10,
        )
        resp.raise_for_status()
    except Exception as e:
        raise Judge0Error(f"Judge0 request failed: {e}")

    return resp.json()
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ide.tests.test_judge0_client --keepdb -v2`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add ide/judge0_client.py ide/tests/test_judge0_client.py
git commit -m "feat(ide): add Judge0 REST client with language mapping"
```

---

## Task 3: Celery Task

**Files:**
- Create: `ide/tasks.py`
- Create: `ide/tests/test_tasks.py`

- [ ] **Step 1: Write task tests**

Create `ide/tests/test_tasks.py`:
```python
from unittest.mock import patch, MagicMock
from datetime import date

from django.test import TestCase, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from gamification.models import XPTransaction
from ide.models import CodingExercise, CodeSubmission
from ide.tasks import run_code_submission

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class RunCodeSubmissionTests(TestCase):
    def setUp(self):
        self.student = _create_test_user(username="task_stu", role_name="student")
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Add", activity_type=self.activity_type,
            subject=self.subject, term=self.term, max_score=100, is_graded=True,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            test_cases=[
                {"input": "2 3", "expected_output": "5", "label": "Test 1"},
                {"input": "0 0", "expected_output": "0", "label": "Test 2"},
                {"input": "-1 1", "expected_output": "0", "label": "Test 3"},
            ],
        )

    @patch("ide.tasks.submit_code")
    def test_all_tests_pass(self, mock_submit):
        mock_submit.side_effect = [
            {"status": {"id": 3}, "stdout": "5\n", "stderr": None, "time": "0.01", "memory": 8000, "compile_output": None},
            {"status": {"id": 3}, "stdout": "0\n", "stderr": None, "time": "0.01", "memory": 8000, "compile_output": None},
            {"status": {"id": 3}, "stdout": "0\n", "stderr": None, "time": "0.01", "memory": 8000, "compile_output": None},
        ]

        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="a,b=map(int,input().split());print(a+b)", language="python",
        )
        run_code_submission(sub.pk)

        sub.refresh_from_db()
        self.assertEqual(sub.status, "completed")
        self.assertEqual(sub.score, 1.0)
        self.assertEqual(len(sub.result_json["tests"]), 3)
        self.assertTrue(all(t["passed"] for t in sub.result_json["tests"]))

    @patch("ide.tasks.submit_code")
    def test_partial_pass(self, mock_submit):
        mock_submit.side_effect = [
            {"status": {"id": 3}, "stdout": "5\n", "stderr": None, "time": "0.01", "memory": 8000, "compile_output": None},
            {"status": {"id": 3}, "stdout": "0\n", "stderr": None, "time": "0.01", "memory": 8000, "compile_output": None},
            {"status": {"id": 3}, "stdout": "WRONG\n", "stderr": None, "time": "0.01", "memory": 8000, "compile_output": None},
        ]

        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="bad code", language="python",
        )
        run_code_submission(sub.pk)

        sub.refresh_from_db()
        self.assertEqual(sub.status, "completed")
        self.assertAlmostEqual(sub.score, 2 / 3, places=2)

    @patch("ide.tasks.submit_code")
    def test_updates_student_activity(self, mock_submit):
        mock_submit.return_value = {
            "status": {"id": 3}, "stdout": "5\n", "stderr": None,
            "time": "0.01", "memory": 8000, "compile_output": None,
        }
        # Only 1 test case for simplicity
        self.exercise.test_cases = [{"input": "2 3", "expected_output": "5", "label": "T1"}]
        self.exercise.save()

        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(5)", language="python",
        )
        run_code_submission(sub.pk)

        sa = StudentActivity.objects.filter(student=self.student, activity=self.activity).first()
        self.assertIsNotNone(sa)
        self.assertEqual(sa.total_score, 100.0)  # 1.0 * max_score(100)

    @patch("ide.tasks.submit_code")
    def test_awards_xp_high_score(self, mock_submit):
        mock_submit.return_value = {
            "status": {"id": 3}, "stdout": "5\n", "stderr": None,
            "time": "0.01", "memory": 8000, "compile_output": None,
        }
        self.exercise.test_cases = [{"input": "2 3", "expected_output": "5", "label": "T1"}]
        self.exercise.save()

        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(5)", language="python",
        )
        run_code_submission(sub.pk)

        xp = XPTransaction.objects.filter(student=self.student, source_type="coding")
        self.assertTrue(xp.exists())
        self.assertEqual(xp.first().amount, 30)  # score >= 0.9

    @patch("ide.tasks.submit_code")
    def test_compilation_error(self, mock_submit):
        mock_submit.return_value = {
            "status": {"id": 6, "description": "Compilation Error"},
            "stdout": None, "stderr": None, "time": None, "memory": None,
            "compile_output": "SyntaxError: invalid syntax",
        }
        self.exercise.test_cases = [{"input": "", "expected_output": "5", "label": "T1"}]
        self.exercise.save()

        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="def bad(", language="python",
        )
        run_code_submission(sub.pk)

        sub.refresh_from_db()
        self.assertEqual(sub.status, "completed")
        self.assertEqual(sub.score, 0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test ide.tests.test_tasks --keepdb -v2 2>&1 | tail -10`
Expected: ImportError

- [ ] **Step 3: Write the Celery task**

Create `ide/tasks.py`:
```python
import logging

from celery import shared_task

from activity.models.student_activity_model import StudentActivity
from gamification.services import award_xp
from ide.judge0_client import submit_code, Judge0Error
from ide.models import CodeSubmission

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def run_code_submission(self, submission_id):
    """Execute a code submission against all test cases via Judge0."""
    try:
        submission = CodeSubmission.objects.select_related(
            "exercise", "exercise__activity", "student",
        ).get(pk=submission_id)
    except CodeSubmission.DoesNotExist:
        logger.error("CodeSubmission %s not found", submission_id)
        return

    submission.status = "running"
    submission.save(update_fields=["status"])

    exercise = submission.exercise
    test_cases = exercise.test_cases
    test_results = []
    passed = 0
    total_time = 0.0
    max_memory = 0

    for tc in test_cases:
        try:
            result = submit_code(
                source_code=submission.code,
                language=submission.language,
                stdin=tc.get("input", ""),
                time_limit=exercise.time_limit_seconds,
                memory_limit=exercise.memory_limit_kb,
            )
        except Judge0Error as e:
            test_results.append({
                "label": tc.get("label", ""),
                "passed": False,
                "stdout": "",
                "expected": tc["expected_output"],
                "error": str(e),
            })
            continue

        status_id = result.get("status", {}).get("id", 0)
        stdout = (result.get("stdout") or "").strip()
        expected = tc["expected_output"].strip()
        is_passed = status_id == 3 and stdout == expected

        if is_passed:
            passed += 1

        time_val = result.get("time")
        if time_val:
            try:
                total_time += float(time_val)
            except (ValueError, TypeError):
                pass

        mem_val = result.get("memory")
        if mem_val and isinstance(mem_val, (int, float)):
            max_memory = max(max_memory, int(mem_val))

        test_results.append({
            "label": tc.get("label", ""),
            "passed": is_passed,
            "stdout": stdout,
            "expected": expected,
            "time": str(time_val or ""),
            "status": result.get("status", {}).get("description", ""),
            "stderr": (result.get("stderr") or "").strip(),
            "compile_output": (result.get("compile_output") or "").strip(),
        })

    score = passed / len(test_cases) if test_cases else 0.0

    submission.status = "completed"
    submission.score = round(score, 4)
    submission.result_json = {"tests": test_results}
    submission.execution_time_ms = int(total_time * 1000)
    submission.memory_used_kb = max_memory
    submission.save(update_fields=[
        "status", "score", "result_json", "execution_time_ms", "memory_used_kb",
    ])

    # Update StudentActivity for gradebook
    activity = exercise.activity
    sa, _ = StudentActivity.objects.get_or_create(
        student=submission.student,
        activity=activity,
        defaults={
            "subject": activity.subject,
            "term": activity.term,
            "total_score": score * (activity.max_score or 100),
        },
    )
    if not _:  # existing record — update if better score
        new_score = score * (activity.max_score or 100)
        if new_score > sa.total_score:
            sa.total_score = new_score
            sa.save(update_fields=["total_score"])

    # Award XP
    if score >= 0.9:
        award_xp(submission.student, 30, "Coding exercise ≥90%", "coding", source_id=submission.pk)
    elif score >= 0.5:
        award_xp(submission.student, 10, "Coding exercise ≥50%", "coding", source_id=submission.pk)
```

- [ ] **Step 4: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ide.tests.test_tasks --keepdb -v2`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add ide/tasks.py ide/tests/test_tasks.py
git commit -m "feat(ide): add Celery task for async code execution and grading"
```

---

## Task 4: Views + URLs

**Files:**
- Create: `ide/views.py`
- Create: `ide/forms.py`
- Create: `ide/urls.py`
- Modify: `lms/urls.py`

- [ ] **Step 1: Create the views**

Create `ide/views.py`:
```python
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from activity.models.activity_model import Activity
from activity.utils.authorization import check_subject_access
from ide.forms import CodingExerciseForm
from ide.models import CodingExercise, CodeSubmission
from ide.tasks import run_code_submission


@login_required
def exercise_detail(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    exercise = get_object_or_404(CodingExercise, activity=activity)

    previous_submissions = CodeSubmission.objects.filter(
        student=request.user, exercise=exercise,
    ).order_by("-submitted_at")[:10]

    test_labels = [tc.get("label", f"Test {i+1}") for i, tc in enumerate(exercise.test_cases)]

    return render(request, "ide/exercise_detail.html", {
        "activity": activity,
        "exercise": exercise,
        "test_labels": test_labels,
        "previous_submissions": previous_submissions,
        "starter_code": exercise.starter_code,
    })


@login_required
@require_POST
def submit_code_view(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    exercise = get_object_or_404(CodingExercise, activity=activity)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    code = data.get("code", "")
    if not code.strip():
        return JsonResponse({"error": "No code provided"}, status=400)

    submission = CodeSubmission.objects.create(
        student=request.user,
        exercise=exercise,
        code=code,
        language=exercise.language,
    )

    run_code_submission.delay(submission.pk)

    return JsonResponse({"submission_id": submission.pk})


@login_required
def submission_status(request, submission_id):
    submission = get_object_or_404(
        CodeSubmission, pk=submission_id, student=request.user,
    )
    return JsonResponse({
        "status": submission.status,
        "score": submission.score,
        "score_pct": int(submission.score * 100) if submission.score is not None else None,
        "result_json": submission.result_json,
        "execution_time_ms": submission.execution_time_ms,
        "memory_used_kb": submission.memory_used_kb,
    })


@login_required
def exercise_create(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)

    has_access, redirect_resp = check_subject_access(
        request, activity.subject, require_teacher=True,
    )
    if not has_access:
        return redirect_resp

    if hasattr(activity, "coding_exercise"):
        return redirect("exercise_edit", exercise_id=activity.coding_exercise.pk)

    if request.method == "POST":
        form = CodingExerciseForm(request.POST)
        if form.is_valid():
            ex = form.save(commit=False)
            ex.activity = activity
            ex.save()
            return redirect("exercise_detail", activity_id=activity.pk)
    else:
        form = CodingExerciseForm()

    return render(request, "ide/exercise_setup.html", {
        "form": form, "activity": activity, "is_edit": False,
    })


@login_required
def exercise_edit(request, exercise_id):
    exercise = get_object_or_404(CodingExercise, pk=exercise_id)

    has_access, redirect_resp = check_subject_access(
        request, exercise.activity.subject, require_teacher=True,
    )
    if not has_access:
        return redirect_resp

    if request.method == "POST":
        form = CodingExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            form.save()
            return redirect("exercise_detail", activity_id=exercise.activity_id)
    else:
        form = CodingExerciseForm(
            instance=exercise,
            initial={"test_cases_text": json.dumps(exercise.test_cases, indent=2)},
        )

    return render(request, "ide/exercise_setup.html", {
        "form": form, "activity": exercise.activity, "exercise": exercise, "is_edit": True,
    })
```

- [ ] **Step 2: Create the form**

Create `ide/forms.py`:
```python
import json

from django import forms
from ide.models import CodingExercise


class CodingExerciseForm(forms.ModelForm):
    test_cases_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 12,
            "placeholder": '[{"input": "2 3", "expected_output": "5", "label": "Test 1"}]',
            "style": "font-family:monospace;font-size:13px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);",
        }),
        help_text="JSON array of test cases. Each test: {input, expected_output, label}.",
    )

    class Meta:
        model = CodingExercise
        fields = ["language", "starter_code", "solution_code", "time_limit_seconds", "memory_limit_kb"]
        widgets = {
            "language": forms.Select(attrs={"class": "form-select", "style": "background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
            "starter_code": forms.Textarea(attrs={"rows": 8, "style": "font-family:monospace;font-size:13px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
            "solution_code": forms.Textarea(attrs={"rows": 8, "style": "font-family:monospace;font-size:13px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
            "time_limit_seconds": forms.NumberInput(attrs={"class": "form-control", "style": "width:100px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
            "memory_limit_kb": forms.NumberInput(attrs={"class": "form-control", "style": "width:150px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
        }

    def clean_test_cases_text(self):
        raw = self.cleaned_data["test_cases_text"]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
        if not isinstance(data, list) or not data:
            raise forms.ValidationError("Must be a non-empty JSON array.")
        for i, tc in enumerate(data):
            if "expected_output" not in tc:
                raise forms.ValidationError(f"Test case {i+1} missing 'expected_output'.")
        return data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.test_cases = self.cleaned_data["test_cases_text"]
        if commit:
            instance.save()
        return instance
```

- [ ] **Step 3: Create URL patterns**

Create `ide/urls.py`:
```python
from django.urls import path
from ide import views

urlpatterns = [
    path("ide/exercise/<int:activity_id>/", views.exercise_detail, name="exercise_detail"),
    path("ide/exercise/<int:activity_id>/submit/", views.submit_code_view, name="submit_code"),
    path("ide/submission/<int:submission_id>/status/", views.submission_status, name="submission_status"),
    path("ide/exercise/<int:activity_id>/setup/", views.exercise_create, name="exercise_create"),
    path("ide/exercise/<int:exercise_id>/edit/", views.exercise_edit, name="exercise_edit"),
]
```

- [ ] **Step 4: Register URLs in lms/urls.py**

In `lms/urls.py`, add before the closing `]`:
```python
    path('', include('ide.urls')),
```

- [ ] **Step 5: Verify**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add ide/views.py ide/forms.py ide/urls.py lms/urls.py
git commit -m "feat(ide): add views, forms, and URL patterns"
```

---

## Task 5: Templates + Monaco Editor

**Files:**
- Create: `ide/templates/ide/exercise_detail.html`
- Create: `ide/templates/ide/exercise_setup.html`

- [ ] **Step 1: Create the exercise detail template**

Create `ide/templates/ide/exercise_detail.html` extending `student_base.html`. This is the main coding page with:

1. **Problem panel** (left side):
   - Activity name as title
   - Language badge + time/memory limits
   - Activity description (if any)
   - Test case labels listed (NOT expected outputs — students shouldn't see answers)
   - Previous submissions list with score badges and timestamps

2. **Editor panel** (right side):
   - Monaco Editor container (`#editor-container`, min-height 400px)
   - "Run Code" button that:
     - POSTs `{code: editor.getValue()}` to `{% url 'submit_code' activity.pk %}`
     - Shows spinner
     - Polls `{% url 'submission_status' %}` + submission_id every 2s
     - Shows results: per-test pass/fail, execution time, memory, stderr

3. **Monaco initialization** (inline script):
   ```javascript
   require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }});
   require(['vs/editor/editor.main'], function() {
       var editor = monaco.editor.create(document.getElementById('editor-container'), {
           value: starterCode,
           language: language,  // 'python' or 'javascript'
           theme: document.body.dataset.theme === 'dark' ? 'vs-dark' : 'vs',
           automaticLayout: true,
           minimap: { enabled: false },
           fontSize: 14,
           lineNumbers: 'on',
           scrollBeyondLastLine: false,
       });
       window.codeEditor = editor;
   });
   ```

4. **Submit + poll JS** (inline script):
   ```javascript
   document.getElementById('run-btn').addEventListener('click', function() {
       var code = window.codeEditor.getValue();
       // POST to submit endpoint, get submission_id, poll status
   });
   ```

Layout: CSS grid with `grid-template-columns: 1fr 1.5fr` on desktop, single column on mobile.

Use the student theme CSS variables for all styling. Monaco CDN loaded via `<script>` in the template.

- [ ] **Step 2: Create the exercise setup template**

Create `ide/templates/ide/exercise_setup.html` extending `student_base.html`:
- Title: "Setup Test Cases" or "Edit Test Cases" based on `is_edit`
- Render form fields: language, starter_code, solution_code, test_cases_text, time_limit, memory_limit
- Submit button + cancel link back to activity detail
- Help text for test case JSON format

- [ ] **Step 3: Verify templates render**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && mkdir -p ide/templates/ide && git add ide/templates/
git commit -m "feat(ide): add Monaco editor exercise detail and setup templates"
```

---

## Task 6: Activity Integration + Seed

**Files:**
- Create: `ide/migrations/0002_seed_coding_activity_type.py`
- Modify: `activity/templates/activity/activities/activity_detail.html`
- Create: `docker-compose.judge0.yml`

- [ ] **Step 1: Create ActivityType seed migration**

Create `ide/migrations/0002_seed_coding_activity_type.py`:
```python
from django.db import migrations


def seed_coding_type(apps, schema_editor):
    ActivityType = apps.get_model("activity", "ActivityType")
    ActivityType.objects.get_or_create(name="Coding")


def reverse_seed(apps, schema_editor):
    ActivityType = apps.get_model("activity", "ActivityType")
    ActivityType.objects.filter(name="Coding").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("ide", "0001_initial"),
        ("activity", "__latest__"),
    ]
    operations = [
        migrations.RunPython(seed_coding_type, reverse_seed),
    ]
```

- [ ] **Step 2: Apply migration**

Run: `cd ~/classedge && env/bin/python manage.py migrate ide 2>&1 | tail -5`

- [ ] **Step 3: Add link to activity detail template**

In `activity/templates/activity/activities/activity_detail.html`, find an appropriate location (near the top of the content block, or after the activity info section) and add:

```html
{% if activity.activity_type.name == "Coding" %}
<div class="mb-3">
    {% if activity.coding_exercise %}
    <a href="{% url 'exercise_detail' activity.pk %}" class="btn btn-primary btn-sm">
        <i class="fas fa-code"></i> Open Code Editor
    </a>
    {% if is_teacher %}
    <a href="{% url 'exercise_edit' activity.coding_exercise.pk %}" class="btn btn-outline-secondary btn-sm ms-2">
        <i class="fas fa-cog"></i> Edit Test Cases
    </a>
    {% endif %}
    {% elif is_teacher %}
    <a href="{% url 'exercise_create' activity.pk %}" class="btn btn-warning btn-sm">
        <i class="fas fa-plus"></i> Setup Test Cases
    </a>
    {% endif %}
</div>
{% endif %}
```

Note: check if `is_teacher` is available in the template context. If not, use a different check like `{% if request.user.profile.role.name == "teacher" %}` or check how other parts of the template detect teacher role.

- [ ] **Step 4: Create Docker Compose file**

Create `docker-compose.judge0.yml` at the project root:
```yaml
# Judge0 — Sandboxed Code Execution
# Start: docker compose -f docker-compose.judge0.yml up -d
# Test:  curl http://localhost:2358/system_info

services:
  judge0-server:
    image: judge0/judge0:1.13.0
    ports:
      - "2358:2358"
    depends_on:
      - judge0-redis
      - judge0-db
    environment:
      - REDIS_URL=redis://judge0-redis:6379
      - POSTGRES_HOST=judge0-db
      - POSTGRES_DB=judge0
      - POSTGRES_USER=judge0
      - POSTGRES_PASSWORD=judge0

  judge0-worker:
    image: judge0/judge0:1.13.0
    command: ["./scripts/workers"]
    depends_on:
      - judge0-server
    environment:
      - REDIS_URL=redis://judge0-redis:6379
      - POSTGRES_HOST=judge0-db
      - POSTGRES_DB=judge0
      - POSTGRES_USER=judge0
      - POSTGRES_PASSWORD=judge0
    privileged: true

  judge0-redis:
    image: redis:7-alpine

  judge0-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=judge0
      - POSTGRES_USER=judge0
      - POSTGRES_PASSWORD=judge0
    volumes:
      - judge0-db-data:/var/lib/postgresql/data

volumes:
  judge0-db-data:
```

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add ide/migrations/0002_seed_coding_activity_type.py docker-compose.judge0.yml activity/templates/activity/activities/activity_detail.html
git commit -m "feat(ide): add Coding activity type seed, activity detail link, Docker Compose"
```

---

## Task 7: View Tests

**Files:**
- Create: `ide/tests/test_views.py`

- [ ] **Step 1: Write view tests**

Create `ide/tests/test_views.py`:
```python
import json
from datetime import date
from unittest.mock import patch

from django.test import TestCase, Client, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from course.models.semester_model import Semester
from course.models.term_model import Term
from ide.models import CodingExercise, CodeSubmission
from subject.models.subject_model import Subject

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75, "score_90": 30,
        "score_75": 15, "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


@override_settings(**_GAM_SETTINGS)
class ExerciseDetailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="ide_v_stu", role_name="student")
        self.teacher = _create_test_user(username="ide_v_teach", role_name="teacher")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Add Numbers",
            activity_type=self.activity_type,
            subject=self.subject, term=self.term,
            max_score=100, is_graded=True,
        )
        self.exercise = CodingExercise.objects.create(
            activity=self.activity, language="python",
            starter_code="def add(a, b):\n    pass",
            test_cases=[{"input": "2 3", "expected_output": "5", "label": "Test 1"}],
        )

    def test_exercise_detail_renders(self):
        self.client.login(username="ide_v_stu", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "monaco")

    def test_unauthenticated_redirects(self):
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/")
        self.assertEqual(resp.status_code, 302)

    @patch("ide.views.run_code_submission")
    def test_submit_creates_submission(self, mock_task):
        mock_task.delay = lambda *a: None
        self.client.login(username="ide_v_stu", password="testpass")
        resp = self.client.post(
            f"/ide/exercise/{self.activity.pk}/submit/",
            json.dumps({"code": "print(5)"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("submission_id", data)
        self.assertTrue(CodeSubmission.objects.filter(pk=data["submission_id"]).exists())

    def test_submission_status_endpoint(self):
        self.client.login(username="ide_v_stu", password="testpass")
        sub = CodeSubmission.objects.create(
            student=self.student, exercise=self.exercise,
            code="print(5)", language="python",
            status="completed", score=1.0,
            result_json={"tests": [{"label": "T1", "passed": True}]},
        )
        resp = self.client.get(f"/ide/submission/{sub.pk}/status/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["score"], 1.0)


@override_settings(**_GAM_SETTINGS)
class TeacherSetupTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="ide_s_stu", role_name="student")
        self.teacher = _create_test_user(username="ide_s_teach", role_name="teacher")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.semester = Semester.objects.create(
            semester_name="Sem2", start_date=date(2026, 1, 1), end_date=date(2027, 12, 31),
        )
        self.term = Term.objects.create(
            term_name="Prelim2", semester=self.semester,
            start_date=date(2026, 8, 15), end_date=date(2026, 10, 15),
        )
        self.activity_type, _ = ActivityType.objects.get_or_create(name="Coding")
        self.activity = Activity.objects.create(
            activity_name="Hello World",
            activity_type=self.activity_type,
            subject=self.subject, term=self.term,
            max_score=100, is_graded=True,
        )

    def test_teacher_can_access_setup(self):
        self.client.login(username="ide_s_teach", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/setup/")
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_setup(self):
        self.client.login(username="ide_s_stu", password="testpass")
        resp = self.client.get(f"/ide/exercise/{self.activity.pk}/setup/")
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 2: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test ide --keepdb -v2`
Expected: All ~15 tests PASS (4 model + 5 judge0 + 5 task + 6 view = ~20)

- [ ] **Step 3: Run full test suite**

Run: `cd ~/classedge && env/bin/python manage.py test ide gamification --keepdb 2>&1 | tail -5`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && git add ide/tests/test_views.py
git commit -m "test(ide): add exercise detail, submit, status, and teacher setup tests"
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | App scaffold + 2 models | 4 |
| 2 | Judge0 REST client | 5 |
| 3 | Celery task (async execution + grading) | 5 |
| 4 | Views + forms + URLs | — |
| 5 | Templates (Monaco editor + setup form) | — |
| 6 | Activity type seed + detail link + Docker Compose | — |
| 7 | View tests | 6 |

**Total new tests: ~20**
