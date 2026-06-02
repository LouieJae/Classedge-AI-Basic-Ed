# At-risk Student Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a teacher/admin dashboard that flags students at risk of failing based on grades, activity completion, and attendance data from existing models.

**Architecture:** New `at_risk/` Django app with a calculator module that reads from existing `StudentActivity`, `Activity`, `Attendance`, and `SubjectEnrollment` models. No new data models — purely analytical. Dashboard view renders a Bootstrap table on the subject detail page.

**Tech Stack:** Django 5, existing PostgreSQL models, Bootstrap 5 + DataTables (already in base.html)

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `at_risk/__init__.py` | App package |
| `at_risk/apps.py` | App config |
| `at_risk/calculator.py` | Risk score calculation from existing data |
| `at_risk/views.py` | Dashboard view |
| `at_risk/urls.py` | URL patterns |
| `at_risk/templates/at_risk/dashboard.html` | Dashboard template |
| `at_risk/tests/__init__.py` | Test package |
| `at_risk/tests/test_calculator.py` | Calculator tests |
| `at_risk/tests/test_views.py` | View tests |

### Modified files

| File | Change |
|------|--------|
| `lms/settings.py` | Add `'at_risk'` to INSTALLED_APPS, add weight settings |
| `lms/urls.py` | Include `at_risk.urls` |
| `course/templates/course/view_subject_dashboard.html` | Add "At-risk Students" link |

---

## Task 1: App Scaffold + Calculator

**Files:**
- Create: `at_risk/__init__.py`, `at_risk/apps.py`, `at_risk/calculator.py`
- Create: `at_risk/tests/__init__.py`, `at_risk/tests/test_calculator.py`
- Modify: `lms/settings.py`

- [ ] **Step 1: Create app package**

Create `at_risk/__init__.py` (empty).

Create `at_risk/apps.py`:
```python
from django.apps import AppConfig


class AtRiskConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "at_risk"
```

Create `at_risk/tests/__init__.py` (empty).

- [ ] **Step 2: Register app in settings**

In `lms/settings.py`, add `'at_risk'` to INSTALLED_APPS after `'rag_tutor'`.

Add at the end:
```python
# At-risk Dashboard
AT_RISK_WEIGHTS = {
    "grade": 0.5,
    "completion": 0.3,
    "attendance": 0.2,
}
AT_RISK_HIGH_THRESHOLD = 40
AT_RISK_MEDIUM_THRESHOLD = 65
```

- [ ] **Step 3: Write the calculator tests**

Create `at_risk/tests/test_calculator.py`:

```python
from datetime import date

from django.test import TestCase, override_settings

from at_risk.calculator import calculate_risk_scores
from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.attendance_model import Attendance, AttendanceStatus

_RISK_SETTINGS = {
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_RISK_SETTINGS)
class CalculateRiskScoresTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="teacher_risk", role_name="teacher")
        self.student = _create_test_user(username="student_risk", role_name="student")
        self.subject = _create_subject()

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
            passing_grade=75,
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.semester,
            status="enrolled",
        )

        self.quiz_type, _ = ActivityType.objects.get_or_create(name="Quiz")
        self.present_status, _ = AttendanceStatus.objects.get_or_create(status="Present")
        self.absent_status, _ = AttendanceStatus.objects.get_or_create(status="Absent")

    def test_low_grades_high_risk(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=20,
        )

        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["student_id"], self.student.pk)
        self.assertLess(results[0]["risk_score"], 40)
        self.assertEqual(results[0]["risk_level"], "high")

    def test_perfect_student_low_risk(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=95,
        )
        Attendance.objects.create(
            student=self.student,
            subject=self.subject,
            date=date(2026, 8, 16),
            status=self.present_status,
        )

        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertGreater(results[0]["risk_score"], 65)
        self.assertEqual(results[0]["risk_level"], "low")

    def test_no_graded_activities_neutral_grade(self):
        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["grade_score"], 50)

    def test_no_attendance_records_neutral(self):
        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["attendance_score"], 50)

    def test_empty_subject_returns_empty(self):
        SubjectEnrollment.objects.all().delete()
        results = calculate_risk_scores(self.subject, self.semester)
        self.assertEqual(results, [])

    def test_weights_applied(self):
        activity = Activity.objects.create(
            activity_name="Quiz 1",
            activity_type=self.quiz_type,
            subject=self.subject,
            term=self.term,
            max_score=100,
            is_graded=True,
        )
        StudentActivity.objects.create(
            student=self.student,
            activity=activity,
            subject=self.subject,
            term=self.term,
            total_score=75,
        )

        results = calculate_risk_scores(self.subject, self.semester)
        r = results[0]
        expected = r["grade_score"] * 0.5 + r["completion_score"] * 0.3 + r["attendance_score"] * 0.2
        self.assertAlmostEqual(r["risk_score"], expected, places=1)
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test at_risk.tests.test_calculator --keepdb -v2 2>&1 | tail -20`
Expected: ImportError

- [ ] **Step 5: Create the calculator**

Create `at_risk/calculator.py`:

```python
from django.conf import settings
from django.db.models import Avg, Count, Q

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from course.models.attendance_model import Attendance
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term


def calculate_risk_scores(subject, semester):
    weights = settings.AT_RISK_WEIGHTS
    high_threshold = settings.AT_RISK_HIGH_THRESHOLD
    medium_threshold = settings.AT_RISK_MEDIUM_THRESHOLD

    enrollments = SubjectEnrollment.objects.filter(
        subject=subject,
        semester=semester,
        status="enrolled",
    ).select_related("student")

    if not enrollments.exists():
        return []

    terms = Term.objects.filter(semester=semester)
    passing_grade = semester.passing_grade or 75

    graded_activities = Activity.objects.filter(
        subject=subject,
        term__in=terms,
        is_graded=True,
    )
    total_activities = graded_activities.count()

    total_attendance_days = Attendance.objects.filter(
        subject=subject,
        date__gte=semester.start_date,
        date__lte=semester.end_date,
    ).values("date").distinct().count()

    results = []
    for enrollment in enrollments:
        student = enrollment.student

        grade_score = _calc_grade_score(student, subject, terms, passing_grade)
        completion_score = _calc_completion_score(student, graded_activities, total_activities)
        attendance_score = _calc_attendance_score(student, subject, semester, total_attendance_days)

        risk_score = (
            grade_score * weights["grade"]
            + completion_score * weights["completion"]
            + attendance_score * weights["attendance"]
        )

        if risk_score < high_threshold:
            risk_level = "high"
        elif risk_score < medium_threshold:
            risk_level = "medium"
        else:
            risk_level = "low"

        results.append({
            "student_id": student.pk,
            "student_name": student.get_full_name() or student.username,
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "grade_score": round(grade_score, 1),
            "completion_score": round(completion_score, 1),
            "attendance_score": round(attendance_score, 1),
        })

    results.sort(key=lambda r: r["risk_score"])
    return results


def _calc_grade_score(student, subject, terms, passing_grade):
    scores = StudentActivity.objects.filter(
        student=student,
        subject=subject,
        term__in=terms,
        activity__is_graded=True,
    ).select_related("activity")

    if not scores.exists():
        return 50.0

    total_earned = 0
    total_possible = 0
    for sa in scores:
        total_earned += sa.total_score
        total_possible += sa.activity.max_score

    if total_possible == 0:
        return 50.0

    average_pct = (total_earned / total_possible) * 100
    if average_pct >= passing_grade:
        return 100.0
    return min((average_pct / passing_grade) * 100, 100.0)


def _calc_completion_score(student, graded_activities, total_activities):
    if total_activities == 0:
        return 50.0

    submitted = StudentActivity.objects.filter(
        student=student,
        activity__in=graded_activities,
    ).count()

    return (submitted / total_activities) * 100


def _calc_attendance_score(student, subject, semester, total_days):
    if total_days == 0:
        return 50.0

    present_count = Attendance.objects.filter(
        student=student,
        subject=subject,
        date__gte=semester.start_date,
        date__lte=semester.end_date,
        status__status__in=["Present", "Present_Online", "Late"],
    ).count()

    return (present_count / total_days) * 100


```

- [ ] **Step 6: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test at_risk.tests.test_calculator --keepdb -v2`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add at_risk/ lms/settings.py
git commit -m "feat(at-risk): add at_risk app with risk score calculator"
```

---

## Task 2: Dashboard View + Template + URLs

**Files:**
- Create: `at_risk/views.py`
- Create: `at_risk/urls.py`
- Create: `at_risk/templates/at_risk/dashboard.html`
- Create: `at_risk/tests/test_views.py`
- Modify: `lms/urls.py`
- Modify: `course/templates/course/view_subject_dashboard.html`

- [ ] **Step 1: Write the view tests**

Create `at_risk/tests/test_views.py`:

```python
from datetime import date

from django.test import TestCase, Client, override_settings

from ai_content.tests.test_models import _create_test_user, _create_subject
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.semester_model import Semester
from course.models.term_model import Term
from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models.subject_model import Subject

_RISK_SETTINGS = {
    "AT_RISK_WEIGHTS": {"grade": 0.5, "completion": 0.3, "attendance": 0.2},
    "AT_RISK_HIGH_THRESHOLD": 40,
    "AT_RISK_MEDIUM_THRESHOLD": 65,
}


@override_settings(**_RISK_SETTINGS)
class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user(username="teacher_dash", role_name="teacher")
        self.student = _create_test_user(username="student_dash", role_name="student")
        self.subject = _create_subject()
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)
        self.subject.refresh_from_db()

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 1, 1),
            end_date=date(2027, 12, 31),
            passing_grade=75,
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            semester=self.semester,
            status="enrolled",
        )

    def test_dashboard_renders_for_teacher(self):
        self.client.login(username="teacher_dash", password="testpass")
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "At-risk")

    def test_dashboard_shows_students(self):
        self.client.login(username="teacher_dash", password="testpass")
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "student_dash")

    def test_student_cannot_access(self):
        self.client.login(username="student_dash", password="testpass")
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)

    def test_unauthenticated_redirects(self):
        resp = self.client.get(f"/at-risk/dashboard/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/classedge && env/bin/python manage.py test at_risk.tests.test_views --keepdb -v2 2>&1 | tail -20`
Expected: ImportError or 404

- [ ] **Step 3: Create the view**

Create `at_risk/views.py`:

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from activity.utils.authorization import check_subject_access
from at_risk.calculator import calculate_risk_scores
from course.models.semester_model import Semester
from subject.models.subject_model import Subject


@login_required
def dashboard(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)

    has_access, redirect_resp = check_subject_access(
        request, subject, require_teacher=True,
    )
    if not has_access:
        return redirect_resp

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()

    results = []
    high_count = 0
    medium_count = 0

    if semester:
        results = calculate_risk_scores(subject, semester)
        high_count = sum(1 for r in results if r["risk_level"] == "high")
        medium_count = sum(1 for r in results if r["risk_level"] == "medium")

    return render(
        request,
        "at_risk/dashboard.html",
        {
            "subject": subject,
            "semester": semester,
            "results": results,
            "high_count": high_count,
            "medium_count": medium_count,
            "total_enrolled": len(results),
        },
    )
```

- [ ] **Step 4: Create URL patterns**

Create `at_risk/urls.py`:

```python
from django.urls import path

from at_risk import views

urlpatterns = [
    path("at-risk/dashboard/<int:subject_id>/", views.dashboard, name="at_risk_dashboard"),
]
```

- [ ] **Step 5: Register URLs in `lms/urls.py`**

Add before the closing `]`:
```python
    path('', include('at_risk.urls')),
```

- [ ] **Step 6: Create the dashboard template**

Create `at_risk/templates/at_risk/dashboard.html`:

```html
{% extends 'base.html' %}
{% block title %}At-risk Students — {{ subject.subject_name }}{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
            <h3>At-risk Students</h3>
            <p class="text-muted">{{ subject.subject_name }}{% if semester %} · {{ semester.semester_name }}{% endif %}</p>
        </div>
        <a href="{% url 'subjectDetail' subject.pk %}" class="btn btn-outline-secondary btn-sm">&larr; Back to subject</a>
    </div>

    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card text-center border-danger">
                <div class="card-body py-2">
                    <h4 class="text-danger mb-0">{{ high_count }}</h4>
                    <small class="text-muted">High Risk</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center border-warning">
                <div class="card-body py-2">
                    <h4 class="text-warning mb-0">{{ medium_count }}</h4>
                    <small class="text-muted">Medium Risk</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card text-center">
                <div class="card-body py-2">
                    <h4 class="mb-0">{{ total_enrolled }}</h4>
                    <small class="text-muted">Total Enrolled</small>
                </div>
            </div>
        </div>
    </div>

    {% if results %}
    <div class="card shadow-sm">
        <div class="card-body p-0">
            <table class="table table-hover mb-0" id="at-risk-table">
                <thead class="table-light">
                    <tr>
                        <th>Student</th>
                        <th>Risk Score</th>
                        <th>Risk Level</th>
                        <th>Grade %</th>
                        <th>Completion %</th>
                        <th>Attendance %</th>
                    </tr>
                </thead>
                <tbody>
                {% for r in results %}
                <tr>
                    <td>{{ r.student_name }}</td>
                    <td>{{ r.risk_score }}</td>
                    <td>
                        {% if r.risk_level == "high" %}
                        <span class="badge bg-danger">High</span>
                        {% elif r.risk_level == "medium" %}
                        <span class="badge bg-warning text-dark">Medium</span>
                        {% else %}
                        <span class="badge bg-success">Low</span>
                        {% endif %}
                    </td>
                    <td>{{ r.grade_score }}</td>
                    <td>{{ r.completion_score }}</td>
                    <td>{{ r.attendance_score }}</td>
                </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
    document.addEventListener('DOMContentLoaded', function() {
        if (typeof $.fn.DataTable !== 'undefined') {
            $('#at-risk-table').DataTable({paging: false, searching: true, order: [[1, 'asc']]});
        }
    });
    </script>
    {% else %}
    <p class="text-muted">No enrolled students found for the current semester.</p>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 7: Add link to subject detail page**

In `course/templates/course/view_subject_dashboard.html`, find where the RAG tutor widget was added (before `{% endblock %}`). Add the at-risk link BEFORE the rag_tutor include:

```html
{% if is_teacher %}
<div class="mt-3">
    <a href="{% url 'at_risk_dashboard' subject.pk %}" class="btn btn-outline-danger btn-sm">
        <i class="fas fa-exclamation-triangle"></i> At-risk Students
    </a>
</div>
{% endif %}
```

- [ ] **Step 8: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test at_risk.tests.test_views --keepdb -v2`
Expected: All 4 tests PASS

- [ ] **Step 9: Commit**

```bash
cd ~/classedge && git add at_risk/views.py at_risk/urls.py at_risk/templates/ at_risk/tests/test_views.py lms/urls.py course/templates/course/view_subject_dashboard.html
git commit -m "feat(at-risk): add dashboard view, template, and URLs"
```

---

## Task 3: Full Integration Test Run

- [ ] **Step 1: Run the complete test suite**

Run: `cd ~/classedge && env/bin/python manage.py test at_risk rag_tutor ai_content central_content received_central_content --keepdb 2>&1 | tail -10`
Expected: All tests PASS

- [ ] **Step 2: Run Django system check**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`
Expected: `System check identified no issues.`

- [ ] **Step 3: Commit if any fixes needed**

```bash
cd ~/classedge && git add -A && git commit -m "fix(at-risk): address integration test findings"
```

---

## Summary

| Task | What it builds | Tests added |
|------|---------------|-------------|
| 1 | App scaffold + risk calculator | 6 tests |
| 2 | Dashboard view + template + URLs | 4 tests |
| 3 | Full integration verification | — |

**Total new tests: ~10**
