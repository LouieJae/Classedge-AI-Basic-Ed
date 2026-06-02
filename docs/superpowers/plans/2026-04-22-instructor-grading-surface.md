# Instructor Grading Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a teacher-facing grading surface in Classedge LMS (~/classedge) — gradebook home, per-subject grid, needs-grading queue, full-page Save & Next grading view, manual override with audit, CSV export.

**Architecture:** Extend the existing `gradebookcomponent/` Django app. New views, templates, service functions, and two schema additions (`StudentActivity.feedback`, `ScoreChangeLog.reason`). Reuse existing `teacher_base.html` design system and HTMX conventions. All new functions labeled `[Classedge LMS]`.

**Tech Stack:** Django 5.0.7 + Postgres + HTMX + Django templates. Tests via Django `TestCase` with `--keepdb` against `test_neondb`.

**Spec:** `docs/superpowers/specs/2026-04-22-instructor-grading-surface-design.md`

**Spec adjustments discovered during planning:**
- `StudentActivity.total_score` is `FloatField(default=0)` — not nullable. The "needs grading" signal for manual-grade types therefore uses `total_score == 0` combined with an existing `StudentQuestion` submission, not `IS NULL`.
- `ScoreChangeLog` currently has `student_activity`, `changed_by`, `previous_score`, `new_score`, `change_date` — no `reason` field. We add it.
- `Activity.quiz_type` is an FK to `QuizType` (its own model). Filter by `quiz_type__name__in=[...]`.
- `gradebookcomponent/urls.py` has no `app_name` namespace. To avoid breaking existing URL reverses, new URL names are explicit (`gradebook_home`, `gradebook_subject`, etc.) — no namespace.
- `gradebookcomponent/tests.py` exists as a single file; we replace it with a `tests/` package.

---

## Task 1: Add `feedback` + `reason` fields (migration)

**Files:**
- Modify: `activity/models/student_activity_model.py`
- Modify: `activity/models/score_log_models.py`
- Create: `activity/migrations/00XX_studentactivity_feedback_scorechangelog_reason.py` (auto-generated)

- [ ] **Step 1: Add `feedback` to `StudentActivity`**

Edit `activity/models/student_activity_model.py`, add field after `attendance_mode`:

```python
    feedback = models.TextField(blank=True, default="")
    # [Classedge LMS] Teacher-entered feedback shown to the student alongside their score.
```

- [ ] **Step 2: Add `reason` to `ScoreChangeLog`**

Edit `activity/models/score_log_models.py`, add field after `change_date`:

```python
    reason = models.TextField(blank=True, default="")
    # [Classedge LMS] Teacher's justification for a manual score override.
```

Rationale for `blank=True, default=""` on `reason`: existing rows have no reason and we avoid a data migration. Server-side validation in `override_score` view enforces non-empty on new overrides.

- [ ] **Step 3: Generate migration**

```bash
cd ~/classedge && ./env/bin/python manage.py makemigrations activity
```

Expected output: one new migration file in `activity/migrations/` with two `AddField` operations.

- [ ] **Step 4: Apply migration (test DB)**

```bash
cd ~/classedge && ./env/bin/python manage.py migrate activity --database=default
```

- [ ] **Step 5: Commit**

```bash
cd ~/classedge && git add -f activity/models/student_activity_model.py activity/models/score_log_models.py activity/migrations/ && git commit -m "feat: add feedback to StudentActivity and reason to ScoreChangeLog

[Classedge LMS] Schema additions for the instructor grading surface.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Convert `tests.py` into `tests/` package

**Files:**
- Delete: `gradebookcomponent/tests.py`
- Create: `gradebookcomponent/tests/__init__.py`
- Create: `gradebookcomponent/tests/helpers.py`

- [ ] **Step 1: Check current tests.py content**

```bash
cat ~/classedge/gradebookcomponent/tests.py
```

If it has real tests, preserve them in `tests/test_legacy.py`. If it's the empty Django default, delete it.

- [ ] **Step 2: Create tests package**

```bash
rm ~/classedge/gradebookcomponent/tests.py
mkdir -p ~/classedge/gradebookcomponent/tests
touch ~/classedge/gradebookcomponent/tests/__init__.py
```

- [ ] **Step 3: Create helpers.py**

Create `gradebookcomponent/tests/helpers.py`:

```python
"""[Classedge LMS] Shared test helpers for gradebookcomponent tests."""
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import Profile
from activity.models.activity_model import Activity, ActivityType, QuizType, ActivityQuestion, StudentQuestion
from activity.models.student_activity_model import StudentActivity
from course.models import Semester, Term
from roles.models import Role
from subject.models import Subject

User = get_user_model()


def make_user(email, role_name="Teacher"):
    """[Classedge LMS] Create a user with a Profile + Role for tests."""
    role, _ = Role.objects.get_or_create(name=role_name)
    user = User.objects.create_user(
        username=email, email=email, password="Test@1234"
    )
    Profile.objects.update_or_create(user=user, defaults={"role": role})
    return user


def make_term(name="Term 1"):
    """[Classedge LMS] Create a Semester + Term for tests."""
    sem, _ = Semester.objects.get_or_create(semester_name="2026 Sem 1")
    term, _ = Term.objects.get_or_create(
        term_name=name, semester=sem, defaults={"start_date": timezone.now().date()}
    )
    return term


def make_subject(teacher, name="Math 101", term=None):
    """[Classedge LMS] Create a Subject assigned to a teacher."""
    term = term or make_term()
    return Subject.objects.create(subject_name=name, assign_teacher=teacher, term=term)


def make_activity(subject, quiz_type_name="Essay", is_graded=True, max_score=10):
    """[Classedge LMS] Create an Activity with an ActivityType and QuizType."""
    atype, _ = ActivityType.objects.get_or_create(name="Quiz")
    qtype, _ = QuizType.objects.get_or_create(name=quiz_type_name)
    return Activity.objects.create(
        activity_name=f"{quiz_type_name} activity",
        activity_type=atype,
        quiz_type=qtype,
        subject=subject,
        term=subject.term,
        is_graded=is_graded,
        max_score=max_score,
    )


def make_submission(student, activity, answer_text="Answer", score=0):
    """[Classedge LMS] Create a StudentActivity + one StudentQuestion submission."""
    sa = StudentActivity.objects.create(
        student=student,
        activity=activity,
        subject=activity.subject,
        term=activity.term,
        total_score=score,
        is_editable=True,
    )
    question = ActivityQuestion.objects.create(
        activity=activity, subject=activity.subject, question_text="Q1"
    )
    StudentQuestion.objects.create(
        student=student,
        activity_question=question,
        activity=activity,
        student_answer=answer_text,
        submission_time=timezone.now(),
    )
    return sa
```

If any field names above don't exactly match the real models (e.g., `Semester.semester_name`, `Term.start_date`), adjust them by reading `course/models.py` and `subject/models.py` and pick the correct field names. The *pattern* is correct; the exact field names come from the source files.

- [ ] **Step 4: Smoke-test helpers import**

```bash
cd ~/classedge && ./env/bin/python -c "from gradebookcomponent.tests.helpers import make_user, make_subject, make_activity, make_submission; print('ok')"
```

Expected: `ok` (no ImportError).

- [ ] **Step 5: Commit**

```bash
git add -f gradebookcomponent/tests/ && git rm -f gradebookcomponent/tests.py && git commit -m "test: create gradebookcomponent tests package with helpers

[Classedge LMS] Shared test helpers for instructor grading surface tests.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: `authorize_subject_access` helper

**Files:**
- Create: `gradebookcomponent/services/__init__.py`
- Create: `gradebookcomponent/services/access.py`
- Create: `gradebookcomponent/tests/test_access.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_access.py`:

```python
"""[Classedge LMS] Tests for subject access authorization."""
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from gradebookcomponent.services.access import authorize_subject_access
from gradebookcomponent.tests.helpers import make_user, make_subject


class AuthorizeSubjectAccessTest(TestCase):
    def test_owner_allowed(self):
        teacher = make_user("owner@t.local", "Teacher")
        subject = make_subject(teacher)
        authorize_subject_access(teacher, subject)  # should not raise

    def test_collaborator_allowed(self):
        owner = make_user("owner@t.local", "Teacher")
        collab = make_user("collab@t.local", "Teacher")
        subject = make_subject(owner)
        subject.collaborators.add(collab)
        authorize_subject_access(collab, subject)  # should not raise

    def test_other_teacher_denied(self):
        owner = make_user("owner@t.local", "Teacher")
        other = make_user("other@t.local", "Teacher")
        subject = make_subject(owner)
        with self.assertRaises(PermissionDenied):
            authorize_subject_access(other, subject)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_access --keepdb
```

Expected: `ModuleNotFoundError: No module named 'gradebookcomponent.services'`

- [ ] **Step 3: Create services package + helper**

Create `gradebookcomponent/services/__init__.py` (empty).

Create `gradebookcomponent/services/access.py`:

```python
"""[Classedge LMS] Access-control helpers for gradebook views."""
from django.core.exceptions import PermissionDenied


def authorize_subject_access(user, subject):
    """[Classedge LMS] Raise PermissionDenied unless user owns or collaborates on the subject."""
    if subject.assign_teacher_id == user.id:
        return
    if subject.collaborators.filter(pk=user.pk).exists():
        return
    raise PermissionDenied("Not authorized for this subject.")
```

- [ ] **Step 4: Run — expect pass**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_access --keepdb
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add -f gradebookcomponent/services/ gradebookcomponent/tests/test_access.py && git commit -m "feat: authorize_subject_access helper

[Classedge LMS] Shared subject ownership/collaborator check for gradebook views.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Extract `compute_weighted_grade`

**Files:**
- Read: `gradebookcomponent/views/gradebook_view.py` — locate existing `studentTotalScore` weighted logic
- Create: `gradebookcomponent/services/grades.py`
- Create: `gradebookcomponent/tests/test_grades.py`

- [ ] **Step 1: Locate the weighted-grade math**

```bash
cd ~/classedge && grep -n "studentTotalScore\|percentage\|GradeBookComponents" gradebookcomponent/views/gradebook_view.py | head -40
```

Read the relevant block (likely 200+ lines into the file). Copy the computation into the new service function unchanged — this is a pure extraction, not a rewrite.

- [ ] **Step 2: Write failing test**

Create `gradebookcomponent/tests/test_grades.py`:

```python
"""[Classedge LMS] Tests for compute_weighted_grade service."""
from django.test import TestCase

from gradebookcomponent.services.grades import compute_weighted_grade
from gradebookcomponent.models import GradeBookComponents, ActivityTypePercentage
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class ComputeWeightedGradeTest(TestCase):
    def test_no_components_returns_zero(self):
        teacher = make_user("t@t.local", "Teacher")
        student = make_user("s@t.local", "Student")
        subject = make_subject(teacher)
        result = compute_weighted_grade(student, subject, subject.term)
        self.assertEqual(result, 0.0)

    def test_single_activity_full_score(self):
        """[Classedge LMS] With one 100%-weighted component and one full-score activity, result == 100.0."""
        teacher = make_user("t@t.local", "Teacher")
        student = make_user("s@t.local", "Student")
        subject = make_subject(teacher)
        activity = make_activity(subject, quiz_type_name="Essay", max_score=10)
        make_submission(student, activity, score=10)
        # Create a GradeBookComponents row worth 100%, mapped to this Activity's type
        component = GradeBookComponents.objects.create(
            teacher=teacher, subject=subject, term=subject.term,
            component_name="Exam", percentage=100,
        )
        ActivityTypePercentage.objects.create(
            gradebook_component=component, activity_type=activity.activity_type, percentage=100,
        )
        result = compute_weighted_grade(student, subject, subject.term)
        self.assertAlmostEqual(result, 100.0, places=1)
```

If `GradeBookComponents` / `ActivityTypePercentage` field names differ, read `gradebookcomponent/models/` and adjust accordingly.

- [ ] **Step 3: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_grades --keepdb
```

Expected: ImportError for `compute_weighted_grade`.

- [ ] **Step 4: Create service by extracting existing logic**

Create `gradebookcomponent/services/grades.py`:

```python
"""[Classedge LMS] Weighted grade computation (extracted from studentTotalScore view)."""
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.models import GradeBookComponents, ActivityTypePercentage


def compute_component_subtotal(student, subject, term, component):
    """[Classedge LMS] Return the per-component subtotal (0–100) using ActivityTypePercentage weights."""
    type_weights = ActivityTypePercentage.objects.filter(gradebook_component=component)
    subtotal = 0.0
    for tw in type_weights:
        sas = StudentActivity.objects.filter(
            student=student, subject=subject, term=term,
            activity__activity_type=tw.activity_type,
        )
        if not sas.exists():
            continue
        max_sum = sum(sa.activity.max_score or 0 for sa in sas)
        earned_sum = sum(sa.total_score or 0 for sa in sas)
        pct = (earned_sum / max_sum * 100) if max_sum else 0
        subtotal += pct * (float(tw.percentage) / 100.0)
    return round(subtotal, 2)


def compute_weighted_grade(student, subject, term):
    """[Classedge LMS] Return weighted final grade (0–100) for student in subject/term.

    Applies GradeBookComponents.percentage × ActivityTypePercentage.percentage
    weights to the student's StudentActivity scores. Missing scores count as 0.
    """
    components = GradeBookComponents.objects.filter(
        subject=subject, term=term
    )
    if not components.exists():
        return 0.0

    total = 0.0
    for component in components:
        subtotal = compute_component_subtotal(student, subject, term, component)
        total += subtotal * (float(component.percentage) / 100.0)
    return round(total, 2)
```

**Important:** This implementation mirrors the conceptual shape of the existing `studentTotalScore` logic. Before committing, open `gradebookcomponent/views/gradebook_view.py`, find the actual weighted computation inside `studentTotalScore`, and align the math exactly — same field names, same edge-case handling, same ordering. The test above just validates the simple case; parity with the existing view is what matters.

- [ ] **Step 5: Run — expect pass**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_grades --keepdb
```

Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add -f gradebookcomponent/services/grades.py gradebookcomponent/tests/test_grades.py && git commit -m "feat: extract compute_weighted_grade service

[Classedge LMS] Pure extraction from studentTotalScore view for reuse in
gradebook grid right-rail and CSV export.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Needs-grading queue service

**Files:**
- Create: `gradebookcomponent/services/queue.py`
- Create: `gradebookcomponent/tests/test_queue_service.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_queue_service.py`:

```python
"""[Classedge LMS] Tests for needs-grading queue service."""
from django.test import TestCase

from gradebookcomponent.services.queue import (
    get_needs_grading_for_teacher, count_needs_grading_for_subject,
)
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class NeedsGradingQueueTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.student = make_user("s@t.local", "Student")
        self.subject = make_subject(self.teacher)

    def test_essay_with_zero_score_included(self):
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=0)
        qs = list(get_needs_grading_for_teacher(self.teacher))
        self.assertEqual(len(qs), 1)

    def test_essay_with_nonzero_score_excluded(self):
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=5)
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_multiple_choice_zero_not_flagged_without_answer(self):
        """[Classedge LMS] MCQ with zero total but empty answers is not in queue."""
        activity = make_activity(self.subject, quiz_type_name="Multiple Choice")
        sa = make_submission(self.student, activity, score=0)
        # Clear the answer that make_submission set
        from activity.models.activity_model import StudentQuestion
        StudentQuestion.objects.filter(student=self.student, activity=activity).update(student_answer="")
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_multiple_choice_zero_flagged_with_answer(self):
        """[Classedge LMS] MCQ with zero total AND non-empty answer → flagged as possibly-broken."""
        activity = make_activity(self.subject, quiz_type_name="Multiple Choice")
        make_submission(self.student, activity, score=0, answer_text="picked A")
        qs = list(get_needs_grading_for_teacher(self.teacher))
        self.assertEqual(len(qs), 1)

    def test_not_graded_activity_excluded(self):
        activity = make_activity(self.subject, quiz_type_name="Essay", is_graded=False)
        make_submission(self.student, activity, score=0)
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_other_teachers_subject_excluded(self):
        other_teacher = make_user("o@t.local", "Teacher")
        other_subject = make_subject(other_teacher)
        activity = make_activity(other_subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=0)
        self.assertEqual(list(get_needs_grading_for_teacher(self.teacher)), [])

    def test_collaborator_sees_queue(self):
        collab = make_user("c@t.local", "Teacher")
        self.subject.collaborators.add(collab)
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(self.student, activity, score=0)
        self.assertEqual(len(list(get_needs_grading_for_teacher(collab))), 1)

    def test_count_per_subject(self):
        a1 = make_activity(self.subject, quiz_type_name="Essay")
        a2 = make_activity(self.subject, quiz_type_name="Document")
        make_submission(self.student, a1, score=0)
        make_submission(self.student, a2, score=0)
        self.assertEqual(count_needs_grading_for_subject(self.teacher, self.subject), 2)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_queue_service --keepdb
```

- [ ] **Step 3: Implement**

Create `gradebookcomponent/services/queue.py`:

```python
"""[Classedge LMS] Needs-grading queue service."""
from django.db.models import Q, Exists, OuterRef, Max

from activity.models.activity_model import StudentQuestion
from activity.models.student_activity_model import StudentActivity

MANUAL_GRADE_TYPES = ["Essay", "Document", "Participation", "Direct Score"]


def _base_queryset_for_teacher(user):
    """[Classedge LMS] StudentActivity filtered to subjects the teacher owns or collaborates on."""
    return StudentActivity.objects.filter(
        Q(activity__subject__assign_teacher=user)
        | Q(activity__subject__collaborators=user),
        activity__is_graded=True,
    ).distinct()


def get_needs_grading_for_teacher(user):
    """[Classedge LMS] Return StudentActivity queryset (oldest submission first) needing teacher attention."""
    has_submission = StudentQuestion.objects.filter(
        student=OuterRef("student"), activity=OuterRef("activity"),
        submission_time__isnull=False,
    )
    has_non_empty_answer = StudentQuestion.objects.filter(
        student=OuterRef("student"), activity=OuterRef("activity"),
    ).exclude(student_answer="").exclude(student_answer__isnull=True)

    base = _base_queryset_for_teacher(user).annotate(
        submitted=Exists(has_submission),
        has_answer=Exists(has_non_empty_answer),
        latest_submission=Max(
            "activity__studentquestion__submission_time",
            filter=Q(activity__studentquestion__student=OuterRef("student")),
        ),
    ).filter(submitted=True)

    manual = base.filter(
        activity__quiz_type__name__in=MANUAL_GRADE_TYPES,
        total_score=0,
    )
    flagged = base.filter(
        is_editable=True, total_score=0, has_answer=True,
    ).exclude(activity__quiz_type__name__in=MANUAL_GRADE_TYPES)

    combined_ids = list(manual.values_list("id", flat=True)) + list(flagged.values_list("id", flat=True))
    return (
        StudentActivity.objects.filter(id__in=set(combined_ids))
        .select_related("student", "activity__subject", "activity__activity_type", "activity__quiz_type")
        .order_by("start_time", "id")
    )


def count_needs_grading_for_subject(user, subject):
    """[Classedge LMS] Count needs-grading submissions for one subject."""
    return get_needs_grading_for_teacher(user).filter(activity__subject=subject).count()
```

**Note on annotated `latest_submission`:** Django ORM restrictions may prevent the above exact annotation syntax. If it errors, compute `latest_submission` in Python after `.values()` and sort the combined list. Simpler fallback: order by `StudentActivity.start_time` (already done above) — that's good enough for FIFO.

- [ ] **Step 4: Run — expect pass**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_queue_service --keepdb
```

- [ ] **Step 5: Commit**

```bash
git add -f gradebookcomponent/services/queue.py gradebookcomponent/tests/test_queue_service.py && git commit -m "feat: needs-grading queue service

[Classedge LMS] Returns StudentActivity rows needing teacher grading across
manual-grade types and flagged auto-grades.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: `gradebook_home` view + nav entry

**Files:**
- Create: `gradebookcomponent/views/instructor_grading.py`
- Create: `gradebookcomponent/templates/gradebookcomponent/gradebook_home.html`
- Modify: `gradebookcomponent/urls.py`
- Modify: `gradebookcomponent/views/__init__.py`
- Modify: `templates/teacher_base.html`
- Create: `gradebookcomponent/tests/test_gradebook_home.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_gradebook_home.py`:

```python
"""[Classedge LMS] Tests for gradebook_home view."""
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class GradebookHomeViewTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.client.force_login(self.teacher)

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("gradebook_home"))
        self.assertIn(response.status_code, (302, 403))

    def test_renders_subjects(self):
        subject = make_subject(self.teacher, name="Algebra")
        response = self.client.get(reverse("gradebook_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algebra")

    def test_non_teacher_denied(self):
        student = make_user("s@t.local", "Student")
        self.client.force_login(student)
        response = self.client.get(reverse("gradebook_home"))
        self.assertEqual(response.status_code, 403)

    def test_shows_pending_count(self):
        subject = make_subject(self.teacher, name="Algebra")
        activity = make_activity(subject, quiz_type_name="Essay")
        student = make_user("s@t.local", "Student")
        make_submission(student, activity, score=0)
        response = self.client.get(reverse("gradebook_home"))
        self.assertContains(response, "1")  # pending count
```

- [ ] **Step 2: Run — expect NoReverseMatch / 404**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_gradebook_home --keepdb
```

- [ ] **Step 3: Implement view**

Create `gradebookcomponent/views/instructor_grading.py`:

```python
"""[Classedge LMS] Instructor grading surface views."""
from django.db.models import Q
from django.shortcuts import render

from gradebookcomponent.services.queue import count_needs_grading_for_subject
from roles.decorators import teacher_or_admin_required
from subject.models import Subject


@teacher_or_admin_required
def gradebook_home(request):
    """[Classedge LMS] Teacher landing page — subject tiles with pending-grading badges."""
    subjects = Subject.objects.filter(
        Q(assign_teacher=request.user) | Q(collaborators=request.user)
    ).distinct().select_related("term")
    tiles = [
        {
            "subject": s,
            "pending": count_needs_grading_for_subject(request.user, s),
        }
        for s in subjects
    ]
    return render(request, "gradebookcomponent/gradebook_home.html", {"tiles": tiles})
```

- [ ] **Step 4: Create template**

Create `gradebookcomponent/templates/gradebookcomponent/gradebook_home.html`:

```django
{% extends "teacher_base.html" %}
{% block content %}
<div class="gradebook-home">
  <h1>Gradebook</h1>
  {% if not tiles %}
    <p class="empty">No subjects assigned yet.</p>
  {% endif %}
  <div class="tile-grid">
    {% for tile in tiles %}
      <a class="tile" href="{% url 'gradebook_subject' tile.subject.id %}">
        <div class="tile-name">{{ tile.subject.subject_name }}</div>
        <div class="tile-term">{{ tile.subject.term.term_name }}</div>
        {% if tile.pending %}
          <span class="badge pending">{{ tile.pending }} need grading</span>
        {% else %}
          <span class="badge clear">All graded</span>
        {% endif %}
      </a>
    {% endfor %}
  </div>
</div>
<style>
  .gradebook-home { padding: 2rem; font-family: var(--body, 'Inter Tight', sans-serif); }
  .gradebook-home h1 { font-family: var(--display, 'Fraunces', serif); color: #1b4332; }
  .tile-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
  .tile { display: block; background: #faf7f2; border: 1px solid #b7925a33;
          border-radius: 16px; padding: 1.25rem; color: #2d3142; text-decoration: none; }
  .tile:hover { border-color: #b7925a; }
  .tile-name { font-size: 1.15rem; font-weight: 600; color: #1b4332; }
  .tile-term { color: #7a7a7a; margin-bottom: 0.75rem; font-size: 0.9rem; }
  .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.8rem; }
  .badge.pending { background: #b7925a; color: white; }
  .badge.clear { background: #1b4332; color: white; }
</style>
{% endblock %}
```

- [ ] **Step 5: Register URL**

Edit `gradebookcomponent/urls.py`. Add at the end of `urlpatterns` (keep existing entries):

```python
    # --- [Classedge LMS] Instructor grading surface ---
    path('gradebook/', gradebook_home, name='gradebook_home'),
    path('gradebook/subject/<int:subject_id>/', subject_gradebook, name='gradebook_subject'),
    path('gradebook/subject/<int:subject_id>/export.csv', subject_gradebook_csv, name='gradebook_subject_csv'),
    path('gradebook/queue/', grading_queue, name='gradebook_queue'),
    path('gradebook/grade/<int:student_activity_id>/', grade_submission, name='gradebook_grade'),
    path('gradebook/override/<int:student_activity_id>/', override_score, name='gradebook_override'),
```

Edit `gradebookcomponent/views/__init__.py` to import the new views:

```python
from gradebookcomponent.views.gradebook_view import *
from gradebookcomponent.views.activity_details_view import *
from gradebookcomponent.views.termbook_view import *
from gradebookcomponent.views.transmutation_view import *
from gradebookcomponent.views.utility_view import *
from gradebookcomponent.views.instructor_grading import (
    gradebook_home, subject_gradebook, subject_gradebook_csv,
    grading_queue, grade_submission, override_score,
)
```

If `__init__.py` is currently empty and views were imported via `from gradebookcomponent.views import *` from `urls.py`, preserve that pattern — the wildcard in `urls.py` (`from gradebookcomponent.views import *`) needs these names reachable. Add explicit imports in `__init__.py` as shown.

**Note:** the URL registrations reference views that don't exist yet (`subject_gradebook`, etc.) — you must stub them before this URL list will import. Add these stubs to `instructor_grading.py` now:

```python
@teacher_or_admin_required
def subject_gradebook(request, subject_id):
    """[Classedge LMS] TEMPORARY stub — real implementation in Task 7."""
    return render(request, "gradebookcomponent/gradebook_home.html", {"tiles": []})

@teacher_or_admin_required
def subject_gradebook_csv(request, subject_id):
    """[Classedge LMS] TEMPORARY stub — real implementation in Task 11."""
    from django.http import HttpResponse
    return HttpResponse("", content_type="text/csv")

@teacher_or_admin_required
def grading_queue(request):
    """[Classedge LMS] TEMPORARY stub — real implementation in Task 8."""
    return render(request, "gradebookcomponent/gradebook_home.html", {"tiles": []})

@teacher_or_admin_required
def grade_submission(request, student_activity_id):
    """[Classedge LMS] TEMPORARY stub — real implementation in Task 9."""
    return render(request, "gradebookcomponent/gradebook_home.html", {"tiles": []})

@teacher_or_admin_required
def override_score(request, student_activity_id):
    """[Classedge LMS] TEMPORARY stub — real implementation in Task 10."""
    from django.http import HttpResponseNotAllowed
    return HttpResponseNotAllowed(["POST"])
```

Each later task replaces the corresponding stub.

- [ ] **Step 6: Add sidebar link**

Edit `templates/teacher_base.html` — locate the sidebar nav block. Add this item below the "Dashboard" link and above whatever comes next:

```django
<!-- [Classedge LMS] Instructor Gradebook -->
<a href="{% url 'gradebook_home' %}"
   class="nav-link {% if request.resolver_match.url_name|slice:':9' == 'gradebook' %}active{% endif %}">
  <span class="icon">📊</span> Gradebook
</a>
```

(The exact class names / markup must mirror the existing nav items in `teacher_base.html`. Read 20 lines of that file first and match the pattern.)

- [ ] **Step 7: Run tests**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_gradebook_home --keepdb
```

Expected: 4 tests pass.

- [ ] **Step 8: Commit**

```bash
git add -f gradebookcomponent/views/ gradebookcomponent/urls.py gradebookcomponent/templates/ templates/teacher_base.html gradebookcomponent/tests/test_gradebook_home.py && git commit -m "feat: gradebook_home view with subject tiles and nav entry

[Classedge LMS] Teacher landing page for the instructor grading surface.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: `subject_gradebook` grid view

**Files:**
- Modify: `gradebookcomponent/views/instructor_grading.py`
- Create: `gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html`
- Create: `gradebookcomponent/tests/test_subject_gradebook.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_subject_gradebook.py`:

```python
"""[Classedge LMS] Tests for subject_gradebook grid view."""
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class SubjectGradebookTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.subject = make_subject(self.teacher, name="Algebra")
        self.client.force_login(self.teacher)

    def test_renders_grid(self):
        student = make_user("s@t.local", "Student")
        activity = make_activity(self.subject, quiz_type_name="Essay")
        make_submission(student, activity, score=8)
        response = self.client.get(reverse("gradebook_subject", args=[self.subject.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Algebra")
        self.assertContains(response, "Essay activity")
        self.assertContains(response, "8")

    def test_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.get(reverse("gradebook_subject", args=[self.subject.id]))
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_subject_gradebook --keepdb
```

- [ ] **Step 3: Replace stub with real implementation**

In `gradebookcomponent/views/instructor_grading.py`, replace the `subject_gradebook` stub with:

```python
from django.shortcuts import get_object_or_404
from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.services.access import authorize_subject_access
from gradebookcomponent.services.grades import compute_weighted_grade
from subject.models import Subject


@teacher_or_admin_required
def subject_gradebook(request, subject_id):
    """[Classedge LMS] Per-subject grid: students × activities with weighted subtotals."""
    subject = get_object_or_404(Subject, pk=subject_id)
    authorize_subject_access(request.user, subject)

    activities = list(
        Activity.objects.filter(subject=subject, term=subject.term, is_graded=True)
        .select_related("activity_type", "quiz_type")
        .order_by("start_time", "id")
    )
    # Enrolled students = distinct students with at least one StudentActivity in this subject/term
    from accounts.models import CustomUser
    student_ids = StudentActivity.objects.filter(
        subject=subject, term=subject.term
    ).values_list("student_id", flat=True).distinct()
    students = list(CustomUser.objects.filter(pk__in=student_ids).order_by("last_name", "first_name"))

    # Build cell map {(student_id, activity_id): StudentActivity}
    sa_rows = StudentActivity.objects.filter(
        subject=subject, term=subject.term, student_id__in=student_ids,
    ).select_related("activity")
    cells = {(sa.student_id, sa.activity_id): sa for sa in sa_rows}

    rows = []
    for student in students:
        row = {"student": student, "cells": [], "final": compute_weighted_grade(student, subject, subject.term)}
        for a in activities:
            sa = cells.get((student.id, a.id))
            row["cells"].append({"activity": a, "sa": sa})
        rows.append(row)

    return render(request, "gradebookcomponent/subject_gradebook.html", {
        "subject": subject, "activities": activities, "rows": rows,
    })
```

(The Subject → enrolled students relationship may be modeled via a dedicated Enrollment model. If one exists — check with `grep -rn "class Enrollment" ~/classedge` — use it instead of the distinct-StudentActivity heuristic.)

- [ ] **Step 4: Create template**

Create `gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html`:

```django
{% extends "teacher_base.html" %}
{% block content %}
<div class="subject-gb">
  <header>
    <a href="{% url 'gradebook_home' %}">← All subjects</a>
    <h1>{{ subject.subject_name }} — {{ subject.term.term_name }}</h1>
    <a class="csv-btn" href="{% url 'gradebook_subject_csv' subject.id %}">Export CSV</a>
  </header>
  <div class="grid-wrap">
    <table class="gb-grid">
      <thead>
        <tr>
          <th class="sticky-left">Student</th>
          {% for a in activities %}
            <th>{{ a.activity_name }}<br><small>({{ a.max_score }})</small></th>
          {% endfor %}
          <th class="final-col">Final</th>
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
          <tr>
            <td class="sticky-left">{{ row.student.last_name }}, {{ row.student.first_name }}</td>
            {% for cell in row.cells %}
              <td class="{% if cell.sa %}{% if cell.sa.total_score > 0 %}graded{% else %}ungraded{% endif %}{% else %}not-attempted{% endif %}">
                {% if cell.sa %}{{ cell.sa.total_score }}{% else %}—{% endif %}
              </td>
            {% endfor %}
            <td class="final-col">{{ row.final }}%</td>
          </tr>
        {% empty %}
          <tr><td colspan="100">No students enrolled yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
<style>
  .subject-gb { padding: 2rem; font-family: var(--body, 'Inter Tight', sans-serif); }
  .subject-gb header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1rem; }
  .subject-gb h1 { font-family: var(--display, 'Fraunces', serif); color: #1b4332; flex: 1; }
  .csv-btn { background: #1b4332; color: white; padding: 0.5rem 1rem; border-radius: 8px; text-decoration: none; }
  .grid-wrap { overflow-x: auto; border: 1px solid #b7925a33; border-radius: 12px; }
  .gb-grid { width: 100%; border-collapse: collapse; background: #faf7f2; }
  .gb-grid th, .gb-grid td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #b7925a22; text-align: left; }
  .gb-grid thead th { background: #1b4332; color: white; position: sticky; top: 0; }
  .sticky-left { position: sticky; left: 0; background: #faf7f2; z-index: 1; }
  .graded { color: #1b4332; font-weight: 600; }
  .ungraded { background: #b7925a33; }
  .not-attempted { color: #c08479; }
  .final-col { font-weight: 700; color: #b7925a; }
</style>
{% endblock %}
```

- [ ] **Step 5: Run tests**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_subject_gradebook --keepdb
```

- [ ] **Step 6: Commit**

```bash
git add -f gradebookcomponent/views/instructor_grading.py gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html gradebookcomponent/tests/test_subject_gradebook.py && git commit -m "feat: subject_gradebook grid view

[Classedge LMS] Per-subject grid with sticky columns, cell color semantics,
and weighted final grade column.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 8: `grading_queue` view

**Files:**
- Modify: `gradebookcomponent/views/instructor_grading.py`
- Create: `gradebookcomponent/templates/gradebookcomponent/grading_queue.html`
- Create: `gradebookcomponent/tests/test_grading_queue.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_grading_queue.py`:

```python
"""[Classedge LMS] Tests for grading_queue view."""
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class GradingQueueTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.client.force_login(self.teacher)

    def test_empty_queue(self):
        response = self.client.get(reverse("gradebook_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No submissions awaiting your attention")

    def test_queue_lists_essay(self):
        subject = make_subject(self.teacher, name="Algebra")
        activity = make_activity(subject, quiz_type_name="Essay")
        student = make_user("s@t.local", "Student")
        make_submission(student, activity, score=0)
        response = self.client.get(reverse("gradebook_queue"))
        self.assertContains(response, "Essay activity")
        self.assertContains(response, "Algebra")
        self.assertContains(response, "Needs grading")
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_grading_queue --keepdb
```

- [ ] **Step 3: Replace stub with real implementation**

In `gradebookcomponent/views/instructor_grading.py`, replace the `grading_queue` stub:

```python
from gradebookcomponent.services.queue import get_needs_grading_for_teacher

MANUAL_GRADE_TYPES = ["Essay", "Document", "Participation", "Direct Score"]


@teacher_or_admin_required
def grading_queue(request):
    """[Classedge LMS] Needs-grading queue across all subjects the teacher owns."""
    items = list(get_needs_grading_for_teacher(request.user))
    rows = []
    for sa in items:
        qt_name = sa.activity.quiz_type.name if sa.activity.quiz_type_id else ""
        rows.append({
            "sa": sa,
            "badge": "Needs grading" if qt_name in MANUAL_GRADE_TYPES else "Review auto-grade",
        })
    return render(request, "gradebookcomponent/grading_queue.html", {"rows": rows})
```

- [ ] **Step 4: Create template**

Create `gradebookcomponent/templates/gradebookcomponent/grading_queue.html`:

```django
{% extends "teacher_base.html" %}
{% block content %}
<div class="grading-queue">
  <h1>Grading Queue</h1>
  {% if not rows %}
    <p class="empty">No submissions awaiting your attention.</p>
  {% else %}
    <table>
      <thead>
        <tr>
          <th>Student</th>
          <th>Subject</th>
          <th>Activity</th>
          <th>Type</th>
          <th>Status</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
          <tr>
            <td>{{ row.sa.student.last_name }}, {{ row.sa.student.first_name }}</td>
            <td>{{ row.sa.activity.subject.subject_name }}</td>
            <td>{{ row.sa.activity.activity_name }}</td>
            <td>{{ row.sa.activity.quiz_type.name }}</td>
            <td><span class="badge {% if row.badge == 'Needs grading' %}needs{% else %}flagged{% endif %}">{{ row.badge }}</span></td>
            <td><a class="btn" href="{% url 'gradebook_grade' row.sa.id %}">Grade →</a></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}
</div>
<style>
  .grading-queue { padding: 2rem; font-family: var(--body, 'Inter Tight', sans-serif); }
  .grading-queue h1 { font-family: var(--display, 'Fraunces', serif); color: #1b4332; }
  table { width: 100%; border-collapse: collapse; background: #faf7f2; border-radius: 12px; overflow: hidden; }
  th, td { padding: 0.75rem 1rem; border-bottom: 1px solid #b7925a22; text-align: left; }
  thead th { background: #1b4332; color: white; }
  .badge.needs { background: #b7925a; color: white; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.8rem; }
  .badge.flagged { background: #c08479; color: white; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.8rem; }
  .btn { background: #1b4332; color: white; padding: 0.4rem 0.8rem; border-radius: 8px; text-decoration: none; }
</style>
{% endblock %}
```

- [ ] **Step 5: Run tests**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_grading_queue --keepdb
```

- [ ] **Step 6: Commit**

```bash
git add -f gradebookcomponent/views/instructor_grading.py gradebookcomponent/templates/gradebookcomponent/grading_queue.html gradebookcomponent/tests/test_grading_queue.py && git commit -m "feat: grading_queue view

[Classedge LMS] Cross-subject needs-grading queue with per-row badges
distinguishing manual-grade items from flagged auto-grades.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 9: `grade_submission` full-page view + Save & Next

**Files:**
- Modify: `gradebookcomponent/views/instructor_grading.py`
- Create: `gradebookcomponent/templates/gradebookcomponent/grade_submission.html`
- Create: `gradebookcomponent/tests/test_grade_submission.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_grade_submission.py`:

```python
"""[Classedge LMS] Tests for grade_submission view."""
from django.test import TestCase
from django.urls import reverse

from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class GradeSubmissionTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.student = make_user("s@t.local", "Student")
        self.subject = make_subject(self.teacher)
        self.activity = make_activity(self.subject, quiz_type_name="Essay", max_score=10)
        self.sa = make_submission(self.student, self.activity, score=0, answer_text="My essay")
        self.client.force_login(self.teacher)

    def test_get_renders_form(self):
        response = self.client.get(reverse("gradebook_grade", args=[self.sa.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My essay")

    def test_post_saves_score_and_feedback(self):
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "8.5", "feedback": "Solid argument."},
        )
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 8.5)
        self.assertEqual(self.sa.feedback, "Solid argument.")

    def test_post_redirects_to_next(self):
        student2 = make_user("s2@t.local", "Student")
        make_submission(student2, self.activity, score=0, answer_text="Another")
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "8", "feedback": "", "save_and_next": "1"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/gradebook/grade/", response.url)

    def test_post_no_next_redirects_to_queue(self):
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "8", "feedback": "", "save_and_next": "1"},
        )
        # Only one submission → redirects to queue
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("gradebook_queue"), response.url)

    def test_score_above_max_rejected(self):
        response = self.client.post(
            reverse("gradebook_grade", args=[self.sa.id]),
            {"score": "100", "feedback": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 0)

    def test_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.get(reverse("gradebook_grade", args=[self.sa.id]))
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_grade_submission --keepdb
```

- [ ] **Step 3: Replace stub with real implementation**

In `gradebookcomponent/views/instructor_grading.py`, replace the `grade_submission` stub:

```python
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from activity.models.activity_model import StudentQuestion


@teacher_or_admin_required
@require_http_methods(["GET", "POST"])
def grade_submission(request, student_activity_id):
    """[Classedge LMS] Full-page grading view with Save & Next progression."""
    sa = get_object_or_404(
        StudentActivity.objects.select_related("student", "activity__subject", "activity__quiz_type"),
        pk=student_activity_id,
    )
    authorize_subject_access(request.user, sa.activity.subject)

    if request.method == "POST":
        try:
            score = float(request.POST.get("score", ""))
        except ValueError:
            return HttpResponseBadRequest("Invalid score")
        if score < 0 or score > (sa.activity.max_score or 0):
            return HttpResponseBadRequest("Score out of range")
        sa.total_score = score
        sa.feedback = request.POST.get("feedback", "")
        sa.save(update_fields=["total_score", "feedback"])

        if request.POST.get("save_and_next"):
            next_sa = (
                get_needs_grading_for_teacher(request.user)
                .exclude(pk=sa.pk).first()
            )
            if next_sa:
                return redirect("gradebook_grade", student_activity_id=next_sa.id)
            return redirect("gradebook_queue")
        return redirect("gradebook_grade", student_activity_id=sa.id)

    answers = StudentQuestion.objects.filter(
        student=sa.student, activity=sa.activity
    ).select_related("activity_question")
    next_sa = (
        get_needs_grading_for_teacher(request.user)
        .exclude(pk=sa.pk).first()
    )
    return render(request, "gradebookcomponent/grade_submission.html", {
        "sa": sa, "answers": answers, "has_next": bool(next_sa),
    })
```

- [ ] **Step 4: Create template**

Create `gradebookcomponent/templates/gradebookcomponent/grade_submission.html`:

```django
{% extends "teacher_base.html" %}
{% block content %}
<div class="grade-view">
  <header>
    <a href="{% url 'gradebook_queue' %}">← Back to queue</a>
    <h1>{{ sa.student.last_name }}, {{ sa.student.first_name }} — {{ sa.activity.activity_name }}</h1>
  </header>
  <div class="split">
    <section class="answer">
      <h2>Student's Answer</h2>
      {% for a in answers %}
        <div class="answer-block">
          <p class="q"><strong>Q:</strong> {{ a.activity_question.question_text }}</p>
          {% if a.student_answer %}<p class="ans">{{ a.student_answer|linebreaks }}</p>{% endif %}
          {% if a.uploaded_file %}<a href="{{ a.uploaded_file.url }}" target="_blank">📎 {{ a.uploaded_file.name }}</a>{% endif %}
        </div>
      {% endfor %}
    </section>
    <section class="form">
      <h2>Grade</h2>
      <form method="post">
        {% csrf_token %}
        <label>Score (0–{{ sa.activity.max_score }})
          <input name="score" type="number" min="0" max="{{ sa.activity.max_score }}" step="0.01" value="{{ sa.total_score }}" required>
        </label>
        <label>Feedback
          <textarea name="feedback" rows="6">{{ sa.feedback }}</textarea>
        </label>
        <div class="btn-row">
          <button type="submit">Save</button>
          {% if has_next %}
            <button type="submit" name="save_and_next" value="1">Save & Next →</button>
          {% endif %}
        </div>
      </form>
    </section>
  </div>
</div>
<style>
  .grade-view { padding: 2rem; font-family: var(--body, 'Inter Tight', sans-serif); }
  .grade-view h1 { font-family: var(--display, 'Fraunces', serif); color: #1b4332; }
  .split { display: grid; grid-template-columns: 1.5fr 1fr; gap: 2rem; margin-top: 1rem; }
  .answer { background: #faf7f2; padding: 1.5rem; border-radius: 12px; }
  .answer-block { border-bottom: 1px solid #b7925a22; padding: 0.75rem 0; }
  .q { color: #1b4332; }
  .form { background: #faf7f2; padding: 1.5rem; border-radius: 12px; display: flex; flex-direction: column; gap: 1rem; }
  .form label { display: flex; flex-direction: column; gap: 0.4rem; font-weight: 600; color: #1b4332; }
  .form input, .form textarea { padding: 0.5rem; border: 1px solid #b7925a55; border-radius: 8px; font: inherit; }
  .btn-row { display: flex; gap: 0.75rem; }
  .btn-row button { padding: 0.6rem 1rem; border: 0; border-radius: 8px; background: #1b4332; color: white; cursor: pointer; font-weight: 600; }
  .btn-row button[name="save_and_next"] { background: #b7925a; }
</style>
{% endblock %}
```

- [ ] **Step 5: Run tests**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_grade_submission --keepdb
```

- [ ] **Step 6: Commit**

```bash
git add -f gradebookcomponent/views/instructor_grading.py gradebookcomponent/templates/gradebookcomponent/grade_submission.html gradebookcomponent/tests/test_grade_submission.py && git commit -m "feat: grade_submission full-page view with Save & Next

[Classedge LMS] Teacher grades an essay/document/participation submission;
Save & Next advances to the next ungraded item or returns to the queue.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 10: `override_score` with audit log

**Files:**
- Modify: `gradebookcomponent/views/instructor_grading.py`
- Create: `gradebookcomponent/services/override.py`
- Create: `gradebookcomponent/tests/test_override.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_override.py`:

```python
"""[Classedge LMS] Tests for override_score view and audit log."""
from django.test import TestCase
from django.urls import reverse

from activity.models.score_log_models import ScoreChangeLog
from activity.models.student_activity_model import StudentActivity
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class OverrideScoreTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.student = make_user("s@t.local", "Student")
        subject = make_subject(self.teacher)
        activity = make_activity(subject, quiz_type_name="Multiple Choice", max_score=10)
        self.sa = make_submission(self.student, activity, score=5)
        self.sa.is_editable = True
        self.sa.save()
        self.client.force_login(self.teacher)

    def test_override_with_reason_writes_log(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": "Accepted alternate answer in Q2."},
        )
        self.assertEqual(response.status_code, 200)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 8.0)
        log = ScoreChangeLog.objects.get(student_activity=self.sa)
        self.assertEqual(log.new_score, 8.0)
        self.assertEqual(log.previous_score, 5.0)
        self.assertEqual(log.reason, "Accepted alternate answer in Q2.")
        self.assertEqual(log.changed_by, self.teacher)

    def test_override_without_reason_rejected(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": ""},
        )
        self.assertEqual(response.status_code, 400)
        self.sa.refresh_from_db()
        self.assertEqual(self.sa.total_score, 5.0)
        self.assertFalse(ScoreChangeLog.objects.filter(student_activity=self.sa).exists())

    def test_override_score_out_of_range_rejected(self):
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "99", "reason": "anything"},
        )
        self.assertEqual(response.status_code, 400)

    def test_override_creates_one_log_per_change(self):
        self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "7", "reason": "first"},
        )
        self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "9", "reason": "second"},
        )
        self.assertEqual(ScoreChangeLog.objects.filter(student_activity=self.sa).count(), 2)

    def test_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.post(
            reverse("gradebook_override", args=[self.sa.id]),
            {"new_score": "8", "reason": "x"},
        )
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_override --keepdb
```

- [ ] **Step 3: Create override service**

Create `gradebookcomponent/services/override.py`:

```python
"""[Classedge LMS] Override service — writes ScoreChangeLog atomically."""
from django.db import transaction

from activity.models.score_log_models import ScoreChangeLog


def apply_override(student_activity, new_score, reason, changed_by):
    """[Classedge LMS] Persist a score override and an audit log row atomically."""
    with transaction.atomic():
        old = student_activity.total_score
        student_activity.total_score = new_score
        student_activity.save(update_fields=["total_score"])
        ScoreChangeLog.objects.create(
            student_activity=student_activity,
            changed_by=changed_by,
            previous_score=old,
            new_score=new_score,
            reason=reason,
        )
```

- [ ] **Step 4: Replace view stub**

In `gradebookcomponent/views/instructor_grading.py`, replace the `override_score` stub:

```python
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from gradebookcomponent.services.override import apply_override


@teacher_or_admin_required
@require_POST
def override_score(request, student_activity_id):
    """[Classedge LMS] HTMX POST: override an auto-graded score; reason is required."""
    sa = get_object_or_404(
        StudentActivity.objects.select_related("activity__subject"),
        pk=student_activity_id,
    )
    authorize_subject_access(request.user, sa.activity.subject)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        return HttpResponseBadRequest("Reason is required for overrides.")

    try:
        new_score = float(request.POST.get("new_score", ""))
    except ValueError:
        return HttpResponseBadRequest("Invalid score")
    if new_score < 0 or new_score > (sa.activity.max_score or 0):
        return HttpResponseBadRequest("Score out of range")

    apply_override(sa, new_score, reason, request.user)
    # Return the new score as a minimal HTMX cell fragment
    return HttpResponse(f'<span class="graded">{new_score}*</span>')
```

- [ ] **Step 5: Run tests**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_override --keepdb
```

- [ ] **Step 6: Commit**

```bash
git add -f gradebookcomponent/views/instructor_grading.py gradebookcomponent/services/override.py gradebookcomponent/tests/test_override.py && git commit -m "feat: override_score with required reason and audit log

[Classedge LMS] Manual override of auto-graded scores writes ScoreChangeLog
atomically; blank reason rejected with 400.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 11: CSV export

**Files:**
- Create: `gradebookcomponent/services/csv_export.py`
- Modify: `gradebookcomponent/views/instructor_grading.py`
- Create: `gradebookcomponent/tests/test_csv_export.py`

- [ ] **Step 1: Write failing tests**

Create `gradebookcomponent/tests/test_csv_export.py`:

```python
"""[Classedge LMS] Tests for CSV export."""
from django.http import StreamingHttpResponse
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.services.csv_export import build_gradebook_csv
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class CSVExportTest(TestCase):
    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.subject = make_subject(self.teacher, name="Algebra")
        self.activity = make_activity(self.subject, quiz_type_name="Essay", max_score=10)
        self.student = make_user("s@t.local", "Student")
        make_submission(self.student, self.activity, score=8)
        self.client.force_login(self.teacher)

    def test_generator_yields_header_row(self):
        rows = list(build_gradebook_csv(self.subject, self.subject.term))
        self.assertTrue(any("Student ID" in r for r in rows))
        self.assertTrue(any("Essay activity" in r for r in rows))

    def test_generator_yields_student_row(self):
        rows = list(build_gradebook_csv(self.subject, self.subject.term))
        joined = "".join(rows)
        self.assertIn(self.student.last_name or self.student.username, joined)
        self.assertIn("8", joined)  # raw score

    def test_view_returns_streaming_response(self):
        response = self.client.get(reverse("gradebook_subject_csv", args=[self.subject.id]))
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_view_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.get(reverse("gradebook_subject_csv", args=[self.subject.id]))
        self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: Run — expect fail**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_csv_export --keepdb
```

- [ ] **Step 3: Implement CSV service**

Create `gradebookcomponent/services/csv_export.py`:

```python
"""[Classedge LMS] CSV export — streaming generator for per-subject gradebook."""
import csv
from io import StringIO

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from accounts.models import CustomUser
from gradebookcomponent.models import GradeBookComponents
from gradebookcomponent.services.grades import (
    compute_weighted_grade, compute_component_subtotal,
)


class _Echo:
    """[Classedge LMS] Minimal file-like object for csv.writer to stream into."""
    def write(self, value):
        return value


def build_gradebook_csv(subject, term):
    """[Classedge LMS] Yield CSV rows: header + one row per student with raw scores + weighted grade."""
    writer = csv.writer(_Echo())
    activities = list(
        Activity.objects.filter(subject=subject, term=term, is_graded=True)
        .order_by("start_time", "id")
    )
    components = list(GradeBookComponents.objects.filter(subject=subject, term=term))

    header = ["Student ID", "Last Name", "First Name"]
    for a in activities:
        header.append(f"{a.activity_name} ({a.max_score})")
    for c in components:
        header.append(f"{c.component_name} Subtotal (%)")
    header.append("Final Grade (%)")
    yield writer.writerow(header)

    student_ids = StudentActivity.objects.filter(
        subject=subject, term=term
    ).values_list("student_id", flat=True).distinct()
    students = CustomUser.objects.filter(pk__in=student_ids).order_by("last_name", "first_name")

    for student in students:
        row = [
            getattr(student, "id_number", "") or student.id,
            student.last_name or "",
            student.first_name or "",
        ]
        sa_map = {
            sa.activity_id: sa
            for sa in StudentActivity.objects.filter(
                student=student, subject=subject, term=term
            )
        }
        for a in activities:
            sa = sa_map.get(a.id)
            if sa is None:
                row.append("")
            else:
                has_override = sa.score_logs.exists() if hasattr(sa, "score_logs") else False
                marker = "*" if has_override else ""
                row.append(f"{sa.total_score}{marker}")
        for c in components:
            row.append(f"{compute_component_subtotal(student, subject, term, c)}")
        row.append(f"{compute_weighted_grade(student, subject, term)}")
        yield writer.writerow(row)
```

- [ ] **Step 4: Replace view stub**

In `gradebookcomponent/views/instructor_grading.py`, replace the `subject_gradebook_csv` stub:

```python
from django.http import StreamingHttpResponse
from django.utils.text import slugify
from datetime import date

from gradebookcomponent.services.csv_export import build_gradebook_csv


@teacher_or_admin_required
def subject_gradebook_csv(request, subject_id):
    """[Classedge LMS] Stream a CSV export of the subject's gradebook."""
    subject = get_object_or_404(Subject, pk=subject_id)
    authorize_subject_access(request.user, subject)

    filename = f"gradebook_{slugify(subject.subject_name)}_{slugify(subject.term.term_name)}_{date.today().isoformat()}.csv"
    response = StreamingHttpResponse(
        build_gradebook_csv(subject, subject.term),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
```

- [ ] **Step 5: Run tests**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_csv_export --keepdb
```

- [ ] **Step 6: Commit**

```bash
git add -f gradebookcomponent/services/csv_export.py gradebookcomponent/views/instructor_grading.py gradebookcomponent/tests/test_csv_export.py && git commit -m "feat: gradebook CSV export (streaming)

[Classedge LMS] Per-subject CSV with raw scores + weighted final grade;
override marker (*) trails any overridden score.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 12: Dashboard shortcut on subject cards

**Files:**
- Modify: `gamification/templates/gamification/teacher_dashboard.html`

- [ ] **Step 1: Locate the subject card block**

```bash
cd ~/classedge && grep -n "subject" gamification/templates/gamification/teacher_dashboard.html | head -20
```

Identify the `{% for subject in ... %}` loop that renders subject cards on the dashboard.

- [ ] **Step 2: Add the link**

Inside the subject-card markup, before the closing tag, add:

```django
<a href="{% url 'gradebook_subject' subject.id %}" class="card-cta">Open Gradebook →</a>
```

Match the existing CTA styling convention used elsewhere on the dashboard (inspect a nearby link for class names).

- [ ] **Step 3: Smoke-test**

```bash
cd ~/classedge && ./env/bin/python manage.py test gamification --keepdb
```

Expected: existing gamification tests still pass (no regression).

- [ ] **Step 4: Commit**

```bash
git add -f gamification/templates/gamification/teacher_dashboard.html && git commit -m "feat: 'Open Gradebook' shortcut on teacher dashboard subject cards

[Classedge LMS] One-click entry to per-subject gradebook from the dashboard.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 13: Function label enforcement test

**Files:**
- Create: `gradebookcomponent/tests/test_function_labels.py`

- [ ] **Step 1: Write the label test**

Create `gradebookcomponent/tests/test_function_labels.py`:

```python
"""[Classedge LMS] Enforce the '[Classedge LMS]' label on all instructor_grading public functions."""
import inspect

from django.test import TestCase

from gradebookcomponent.views import instructor_grading
from gradebookcomponent.services import access, grades, queue, override, csv_export


LABEL = "[Classedge LMS]"


class FunctionLabelTest(TestCase):
    def _check(self, module):
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            if obj.__module__ != module.__name__:
                continue  # skip re-exports
            doc = inspect.getdoc(obj) or ""
            src = inspect.getsource(obj)[:400]
            self.assertTrue(
                LABEL in doc or LABEL in src,
                f"{module.__name__}.{name} missing '{LABEL}' label",
            )

    def test_views(self):
        self._check(instructor_grading)

    def test_services(self):
        for mod in [access, grades, queue, override, csv_export]:
            self._check(mod)
```

- [ ] **Step 2: Run**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent.tests.test_function_labels --keepdb
```

Expected: pass. If any function is missing the label, add it to that function's docstring or leading comment, then re-run.

- [ ] **Step 3: Commit**

```bash
git add -f gradebookcomponent/tests/test_function_labels.py && git commit -m "test: enforce [Classedge LMS] label on grading surface functions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 14: Full-suite smoke + push

- [ ] **Step 1: Run the full gradebookcomponent test suite**

```bash
cd ~/classedge && ./env/bin/python manage.py test gradebookcomponent --keepdb -v 2
```

Expected: all new tests pass; no existing tests break.

- [ ] **Step 2: Run broader safety-net (activity, gamification, subject)**

```bash
cd ~/classedge && ./env/bin/python manage.py test activity gamification subject --keepdb -v 1
```

Expected: no regressions.

- [ ] **Step 3: Manual UI smoke**

Start the dev server:

```bash
cd ~/classedge && ./env/bin/python manage.py runserver 0.0.0.0:8000
```

Log in as a teacher. Visit `/gradebook/`, click a subject, verify the grid renders, visit `/gradebook/queue/`, click Grade →, save with feedback. If anything looks off, fix before pushing.

- [ ] **Step 4: Push**

```bash
cd ~/classedge && git push personal main
```

---

## Spec traceability

| Spec section | Implemented in task |
|---|---|
| §2.1 `feedback` field | Task 1 |
| §2.2 `ScoreChangeLog.reason` | Task 1 |
| §2.4 permissions | Task 3 (`authorize_subject_access`) |
| §3 URL table | Task 6 (registers all 6 routes with stubs; later tasks replace stubs) |
| §4.2 sidebar nav | Task 6 |
| §4.3 dashboard shortcut | Task 12 |
| §5 queue query | Task 5 |
| §6 CSV export | Task 11 |
| §6.5 `compute_weighted_grade` extraction | Task 4 |
| §7 override + audit | Task 10 |
| §8 testing strategy | Tasks 3, 5, 6, 7, 8, 9, 10, 11, 13 |
| §9 commit ordering | Tasks 1–13 |
