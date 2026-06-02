# Auto-Quest Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI-assisted, manual, and bulk-upload quest authoring per lesson, with org-admin gating and opt-in gradebook integration.

**Architecture:** New `gamification` quest models + threaded generation pipeline. Pluggable AI provider (Anthropic/OpenAI) chosen by registrar. Quest score (float 0–100, 2dp) feeds existing `compute_component_subtotal` via a single branch on `gradebook_category == 'quest_completion'`. Three teacher entry points (AI/manual/upload) gated by `OrganizationQuestSettings` toggles.

**Tech Stack:** Django 4.x, Python 3.x, `anthropic`, `openai`, `pypdf`, `python-docx`, `python-pptx`, `jsonschema`, Django `threading`.

**Spec:** `docs/superpowers/specs/2026-05-12-auto-quest-generation-design.md`

---

## Phase 1 — Settings & Configuration Foundation

### Task 1: Add `quest_count_per_lesson` to Subject

**Files:**
- Modify: `subject/models/subject.py` (or wherever `Subject` is defined; verify path first)
- Create: `subject/migrations/<next>_subject_quest_count_per_lesson.py`
- Test: `subject/tests/test_quest_count_field.py`

- [ ] **Step 1: Locate Subject model**

Run: `grep -rn "class Subject" subject/models/ | head -3`
Note the file. All edits below assume `subject/models/subject_model.py`; adjust if different.

- [ ] **Step 2: Write failing test**

```python
# subject/tests/test_quest_count_field.py
from django.test import TestCase
from subject.models import Subject

class QuestCountFieldTests(TestCase):
    def test_default_is_5(self):
        s = Subject.objects.create(subject_name="Math")
        self.assertEqual(s.quest_count_per_lesson, 5)

    def test_can_set_custom(self):
        s = Subject.objects.create(subject_name="Sci", quest_count_per_lesson=8)
        self.assertEqual(s.quest_count_per_lesson, 8)
```

- [ ] **Step 3: Run, expect FAIL**

Run: `python manage.py test subject.tests.test_quest_count_field -v 2`
Expected: AttributeError / field does not exist.

- [ ] **Step 4: Add field**

Add to `Subject`:
```python
quest_count_per_lesson = models.PositiveIntegerField(default=5)
```

- [ ] **Step 5: Generate & apply migration**

Run:
```bash
python manage.py makemigrations subject
python manage.py migrate subject
```

- [ ] **Step 6: Run test, expect PASS**

Run: `python manage.py test subject.tests.test_quest_count_field -v 2`

- [ ] **Step 7: Commit**

```bash
git add subject/models subject/migrations subject/tests/test_quest_count_field.py
git commit -m "feat(subject): add quest_count_per_lesson field (default 5)"
```

---

### Task 2: `OrganizationQuestSettings` singleton model

**Files:**
- Create: `gamification/quest_settings_models.py`
- Modify: `gamification/models.py` (re-export at bottom)
- Create: `gamification/migrations/<next>_organization_quest_settings.py`
- Test: `gamification/tests/test_quest_settings_model.py`

- [ ] **Step 1: Write failing test**

```python
# gamification/tests/test_quest_settings_model.py
from django.core.exceptions import ValidationError
from django.test import TestCase
from gamification.quest_settings_models import OrganizationQuestSettings

class OrgQuestSettingsTests(TestCase):
    def test_load_creates_singleton_with_defaults(self):
        s = OrganizationQuestSettings.load()
        self.assertTrue(s.ai_mode_enabled)
        self.assertTrue(s.manual_mode_enabled)
        self.assertTrue(s.upload_mode_enabled)
        self.assertEqual(s.ai_provider, "anthropic")
        self.assertEqual(s.pk, 1)

    def test_load_returns_same_row(self):
        a = OrganizationQuestSettings.load()
        b = OrganizationQuestSettings.load()
        self.assertEqual(a.pk, b.pk)

    def test_cannot_disable_all_modes(self):
        s = OrganizationQuestSettings.load()
        s.ai_mode_enabled = False
        s.manual_mode_enabled = False
        s.upload_mode_enabled = False
        with self.assertRaises(ValidationError):
            s.full_clean()
```

- [ ] **Step 2: Run, expect FAIL**

Run: `python manage.py test gamification.tests.test_quest_settings_model -v 2`

- [ ] **Step 3: Create model**

```python
# gamification/quest_settings_models.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

PROVIDER_CHOICES = [("anthropic", "Anthropic"), ("openai", "OpenAI")]


class OrganizationQuestSettings(models.Model):
    """[Classedge LMS] Singleton config for quest authoring modes & AI provider."""
    ai_mode_enabled = models.BooleanField(default=True)
    manual_mode_enabled = models.BooleanField(default=True)
    upload_mode_enabled = models.BooleanField(default=True)
    ai_provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="anthropic")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Organization Quest Settings"
        verbose_name_plural = "Organization Quest Settings"

    def __str__(self):
        return "Organization Quest Settings"

    def clean(self):
        if not (self.ai_mode_enabled or self.manual_mode_enabled or self.upload_mode_enabled):
            raise ValidationError("At least one authoring mode must remain enabled.")

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

- [ ] **Step 4: Re-export from models.py**

Append to `gamification/models.py`:
```python
from gamification.quest_settings_models import OrganizationQuestSettings  # noqa: F401
```

- [ ] **Step 5: Migrate**

```bash
python manage.py makemigrations gamification
python manage.py migrate gamification
```

- [ ] **Step 6: Tests pass**

Run: `python manage.py test gamification.tests.test_quest_settings_model -v 2`

- [ ] **Step 7: Commit**

```bash
git add gamification/quest_settings_models.py gamification/models.py gamification/migrations gamification/tests/test_quest_settings_model.py
git commit -m "feat(gamification): add OrganizationQuestSettings singleton"
```

---

### Task 3: Registrar quest-settings page

**Files:**
- Create: `gamification/registrar_views.py`
- Create: `gamification/forms/quest_settings_form.py`
- Create: `templates/operations/registrar_quest_settings.html`
- Modify: `accounts/urls.py` (add the route under registrar/)
- Test: `gamification/tests/test_registrar_quest_settings.py`

- [ ] **Step 1: Write failing tests**

```python
# gamification/tests/test_registrar_quest_settings.py
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models.account_models import Profile
from roles.models import Role
from gamification.quest_settings_models import OrganizationQuestSettings

User = get_user_model()

class RegistrarQuestSettingsTests(TestCase):
    def setUp(self):
        self.registrar_role = Role.objects.create(name="Registrar")
        self.other_role = Role.objects.create(name="Teacher")
        self.registrar = User.objects.create_user("reg", password="x")
        Profile.objects.create(user=self.registrar, role=self.registrar_role)
        self.teacher = User.objects.create_user("tch", password="x")
        Profile.objects.create(user=self.teacher, role=self.other_role)

    def test_non_registrar_blocked(self):
        c = Client(); c.force_login(self.teacher)
        r = c.get(reverse("registrar_quest_settings"))
        self.assertIn(r.status_code, (302, 403))

    def test_registrar_can_view(self):
        c = Client(); c.force_login(self.registrar)
        r = c.get(reverse("registrar_quest_settings"))
        self.assertEqual(r.status_code, 200)

    def test_registrar_can_save(self):
        c = Client(); c.force_login(self.registrar)
        r = c.post(reverse("registrar_quest_settings"), {
            "ai_mode_enabled": "on",
            "manual_mode_enabled": "",
            "upload_mode_enabled": "on",
            "ai_provider": "openai",
        })
        self.assertEqual(r.status_code, 302)
        s = OrganizationQuestSettings.load()
        self.assertTrue(s.ai_mode_enabled)
        self.assertFalse(s.manual_mode_enabled)
        self.assertEqual(s.ai_provider, "openai")
        self.assertEqual(s.updated_by, self.registrar)

    def test_cannot_save_all_disabled(self):
        c = Client(); c.force_login(self.registrar)
        r = c.post(reverse("registrar_quest_settings"), {
            "ai_mode_enabled": "", "manual_mode_enabled": "", "upload_mode_enabled": "",
            "ai_provider": "anthropic",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "At least one")
```

- [ ] **Step 2: Run, expect FAIL** (NoReverseMatch)

- [ ] **Step 3: Create form**

```python
# gamification/forms/quest_settings_form.py
from django import forms
from gamification.quest_settings_models import OrganizationQuestSettings


class OrganizationQuestSettingsForm(forms.ModelForm):
    class Meta:
        model = OrganizationQuestSettings
        fields = ["ai_mode_enabled", "manual_mode_enabled", "upload_mode_enabled", "ai_provider"]
```

Create `gamification/forms/__init__.py` if missing:
```python
from gamification.forms.quest_settings_form import OrganizationQuestSettingsForm  # noqa
```

- [ ] **Step 4: Create view**

```python
# gamification/registrar_views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render
from gamification.forms.quest_settings_form import OrganizationQuestSettingsForm
from gamification.quest_settings_models import OrganizationQuestSettings


def _is_registrar(user):
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.role
        and user.profile.role.name == "Registrar"
    )


@login_required
@user_passes_test(_is_registrar)
def registrar_quest_settings(request):
    obj = OrganizationQuestSettings.load()
    if request.method == "POST":
        form = OrganizationQuestSettingsForm(request.POST, instance=obj)
        if form.is_valid():
            inst = form.save(commit=False)
            inst.updated_by = request.user
            try:
                inst.save()
            except Exception as e:
                form.add_error(None, str(e))
            else:
                messages.success(request, "Quest settings saved.")
                return redirect("registrar_quest_settings")
    else:
        form = OrganizationQuestSettingsForm(instance=obj)
    return render(request, "operations/registrar_quest_settings.html", {"form": form, "obj": obj})
```

- [ ] **Step 5: Template**

```html
<!-- templates/operations/registrar_quest_settings.html -->
{% extends 'base.html' %}
{% block content %}
<div class="container" style="max-width:640px;padding:24px;">
  <h2>Quest Authoring Settings</h2>
  <p>Choose which quest authoring modes teachers can use.</p>
  <form method="post">{% csrf_token %}
    {% if form.non_field_errors %}<div class="alert alert-danger">{{ form.non_field_errors }}</div>{% endif %}
    <label><input type="checkbox" name="ai_mode_enabled" {% if form.ai_mode_enabled.value %}checked{% endif %}> AI-assisted generation</label><br>
    <label><input type="checkbox" name="manual_mode_enabled" {% if form.manual_mode_enabled.value %}checked{% endif %}> Manual entry</label><br>
    <label><input type="checkbox" name="upload_mode_enabled" {% if form.upload_mode_enabled.value %}checked{% endif %}> Bulk upload (CSV/JSON)</label><br><br>
    <label>AI provider:
      <select name="ai_provider">
        <option value="anthropic" {% if form.ai_provider.value == 'anthropic' %}selected{% endif %}>Anthropic</option>
        <option value="openai" {% if form.ai_provider.value == 'openai' %}selected{% endif %}>OpenAI</option>
      </select>
    </label><br><br>
    <button type="submit" class="btn btn-primary">Save</button>
  </form>
  {% if obj.updated_at %}<p style="color:#888;margin-top:16px;">Last updated {{ obj.updated_at }} by {{ obj.updated_by|default:'—' }}</p>{% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Wire URL**

In `accounts/urls.py`, add:
```python
from gamification.registrar_views import registrar_quest_settings
# in urlpatterns, under the registrar/ section:
path("registrar/quest-settings/", registrar_quest_settings, name="registrar_quest_settings"),
```

- [ ] **Step 7: Tests pass**

Run: `python manage.py test gamification.tests.test_registrar_quest_settings -v 2`

- [ ] **Step 8: Commit**

```bash
git add gamification/registrar_views.py gamification/forms templates/operations/registrar_quest_settings.html accounts/urls.py gamification/tests/test_registrar_quest_settings.py
git commit -m "feat(gamification): registrar page to gate quest authoring modes"
```

---

## Phase 2 — Quest Data Model

### Task 4: `Quest`, `QuestAttempt`, `QuestGenerationJob` models

**Files:**
- Create: `gamification/quest_models.py`
- Modify: `gamification/models.py` (re-export)
- Create: `gamification/migrations/<next>_quest_models.py`
- Test: `gamification/tests/test_quest_models.py`

- [ ] **Step 1: Write failing test**

```python
# gamification/tests/test_quest_models.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt, QuestGenerationJob

User = get_user_model()


class QuestModelTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="Math")
        self.module = Module.objects.create(file_name="Lesson 1", subject=self.subject)
        self.student = User.objects.create_user("s1", password="x")

    def test_create_quest_defaults(self):
        q = Quest.objects.create(module=self.module, order=1, kind="quiz",
                                 title="T", body="B", payload={"options": ["a"], "correct_index": 0})
        self.assertEqual(q.status, "draft")
        self.assertTrue(q.counts_toward_grade)

    def test_attempt_unique_per_student(self):
        q = Quest.objects.create(module=self.module, order=1, kind="task",
                                 title="t", body="b", payload={})
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        with self.assertRaises(IntegrityError):
            QuestAttempt.objects.create(quest=q, student=self.student, is_correct=False, score=0.0)

    def test_job_default_status(self):
        j = QuestGenerationJob.objects.create(module=self.module)
        self.assertEqual(j.status, "queued")
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create models**

```python
# gamification/quest_models.py
from django.conf import settings
from django.db import models


class Quest(models.Model):
    KIND_CHOICES = [("quiz", "Quiz"), ("reading_check", "Reading Check"), ("task", "Task")]
    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published")]

    module = models.ForeignKey("module.Module", on_delete=models.CASCADE, related_name="quests")
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    title = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    counts_toward_grade = models.BooleanField(default=True)
    ai_provider = models.CharField(max_length=20, blank=True)
    source_chunk = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["module", "order"]

    def __str__(self):
        return f"{self.module_id}#{self.order} {self.title[:30]}"


class QuestAttempt(models.Model):
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submitted_answer = models.JSONField(default=dict)
    is_correct = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)
    completed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("quest", "student")


class QuestGenerationJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"), ("running", "Running"),
        ("complete", "Complete"), ("failed", "Failed"),
    ]
    module = models.ForeignKey("module.Module", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="queued")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["module", "status"])]
```

- [ ] **Step 4: Re-export & migrate**

Append to `gamification/models.py`:
```python
from gamification.quest_models import Quest, QuestAttempt, QuestGenerationJob  # noqa: F401
```

Run:
```bash
python manage.py makemigrations gamification
python manage.py migrate gamification
```

- [ ] **Step 5: Tests pass**

Run: `python manage.py test gamification.tests.test_quest_models -v 2`

- [ ] **Step 6: Commit**

```bash
git add gamification/quest_models.py gamification/models.py gamification/migrations gamification/tests/test_quest_models.py
git commit -m "feat(gamification): Quest, QuestAttempt, QuestGenerationJob models"
```

---

## Phase 3 — Grading Integration

### Task 5: `get_student_quest_score` service

**Files:**
- Create: `gamification/quest_grading.py`
- Test: `gamification/tests/test_quest_grading.py`

- [ ] **Step 1: Write failing test**

```python
# gamification/tests/test_quest_grading.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from course.models.term_model import Term
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt
from gamification.quest_grading import get_student_quest_score

User = get_user_model()


class QuestGradingTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="S")
        self.term = Term.objects.create(name="T1")
        self.module = Module.objects.create(file_name="L", subject=self.subject, term=self.term)
        self.student = User.objects.create_user("s", password="x")

    def _q(self, status="published", grade=True):
        return Quest.objects.create(module=self.module, order=1, kind="quiz",
                                    title="t", body="b", payload={},
                                    status=status, counts_toward_grade=grade)

    def test_no_quests_returns_zero(self):
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_unattempted_counts_as_zero(self):
        self._q()
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_full_correct_returns_100(self):
        q = self._q()
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 100.0)

    def test_partial_average(self):
        q1 = self._q()
        q2 = Quest.objects.create(module=self.module, order=2, kind="quiz", title="t2", body="b",
                                  payload={}, status="published", counts_toward_grade=True)
        QuestAttempt.objects.create(quest=q1, student=self.student, is_correct=True, score=1.0)
        QuestAttempt.objects.create(quest=q2, student=self.student, is_correct=False, score=0.5)
        # (100 + 50) / 2 = 75.0
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 75.0)

    def test_draft_excluded(self):
        q = self._q(status="draft")
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_counts_toward_grade_false_excluded(self):
        q = self._q(grade=False)
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.assertEqual(get_student_quest_score(self.student, self.subject, self.term), 0.0)

    def test_return_is_float_two_dp(self):
        q1 = self._q()
        q2 = Quest.objects.create(module=self.module, order=2, kind="quiz", title="t2", body="b",
                                  payload={}, status="published", counts_toward_grade=True)
        q3 = Quest.objects.create(module=self.module, order=3, kind="quiz", title="t3", body="b",
                                  payload={}, status="published", counts_toward_grade=True)
        QuestAttempt.objects.create(quest=q1, student=self.student, is_correct=True, score=1.0)
        # (100 + 0 + 0) / 3 = 33.33...
        result = get_student_quest_score(self.student, self.subject, self.term)
        self.assertIsInstance(result, float)
        self.assertEqual(result, 33.33)
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Implement**

```python
# gamification/quest_grading.py
"""[Classedge LMS] Compute student quest score (0..100 float, 2dp) for gradebook."""
from gamification.quest_models import Quest, QuestAttempt


def get_student_quest_score(student, subject, term) -> float:
    quests = Quest.objects.filter(
        module__subject=subject,
        module__term=term,
        status="published",
        counts_toward_grade=True,
    )
    total_quests = quests.count()
    if total_quests == 0:
        return 0.0
    attempts = {
        a.quest_id: a
        for a in QuestAttempt.objects.filter(quest__in=quests, student=student)
    }
    total = 0.0
    for q in quests:
        a = attempts.get(q.id)
        total += (a.score * 100.0) if a else 0.0
    return round(total / total_quests, 2)
```

- [ ] **Step 4: Tests pass**

Run: `python manage.py test gamification.tests.test_quest_grading -v 2`

- [ ] **Step 5: Commit**

```bash
git add gamification/quest_grading.py gamification/tests/test_quest_grading.py
git commit -m "feat(gamification): quest score service (float 0-100, 2dp)"
```

---

### Task 6: Wire quest score into `compute_component_subtotal`

**Files:**
- Modify: `gradebookcomponent/services/grades.py`
- Test: `gradebookcomponent/tests/test_grades_quest_branch.py`

- [ ] **Step 1: Write failing test**

```python
# gradebookcomponent/tests/test_grades_quest_branch.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from accounts.models.account_models import CustomUser  # adjust if path differs
from course.models.term_model import Term
from gradebookcomponent.models import GradeBookComponents
from gradebookcomponent.services.grades import compute_component_subtotal, compute_weighted_grade
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt

User = get_user_model()

class GradesQuestBranchTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("t", password="x")
        self.student = User.objects.create_user("s", password="x")
        self.subject = Subject.objects.create(subject_name="S")
        self.term = Term.objects.create(name="T")
        self.module = Module.objects.create(file_name="L", subject=self.subject, term=self.term)
        q = Quest.objects.create(module=self.module, order=1, kind="quiz", title="t", body="b",
                                 payload={}, status="published", counts_toward_grade=True)
        QuestAttempt.objects.create(quest=q, student=self.student, is_correct=True, score=1.0)
        self.component = GradeBookComponents.objects.create(
            teacher=self.teacher, subject=self.subject, term=self.term,
            gradebook_name="Quests", gradebook_category="quest_completion",
            percentage=20,
        )

    def test_subtotal_uses_quest_score(self):
        sub = compute_component_subtotal(self.student, self.subject, self.term, self.component)
        self.assertEqual(sub, 100.0)
        self.assertIsInstance(sub, float)

    def test_weighted_grade_applies_component_weight(self):
        # 100 (quest subtotal) * 20% (component weight) = 20.0
        grade = compute_weighted_grade(self.student, self.subject, self.term)
        self.assertEqual(grade, 20.0)
```

- [ ] **Step 2: Run, expect FAIL** (subtotal will be 0.0)

- [ ] **Step 3: Add branch**

In `gradebookcomponent/services/grades.py`, at the top of `compute_component_subtotal`:
```python
def compute_component_subtotal(student, subject, term, component):
    if component.gradebook_category == "quest_completion":
        from gamification.quest_grading import get_student_quest_score
        return get_student_quest_score(student, subject, term)
    # existing body unchanged
    type_weights = ActivityTypePercentage.objects.filter(gradebook_component=component)
    ...
```

- [ ] **Step 4: Tests pass**

Run: `python manage.py test gradebookcomponent.tests.test_grades_quest_branch -v 2`

- [ ] **Step 5: Commit**

```bash
git add gradebookcomponent/services/grades.py gradebookcomponent/tests/test_grades_quest_branch.py
git commit -m "feat(gradebook): route quest_completion components to quest grading"
```

---

## Phase 4 — Text Extraction & AI Providers

### Task 7: File text extractor

**Files:**
- Create: `gamification/lesson_text.py`
- Test: `gamification/tests/test_lesson_text.py`
- Add deps to `requirements.txt`: `pypdf`, `python-docx`, `python-pptx`

- [ ] **Step 1: Install deps**

```bash
pip install pypdf python-docx python-pptx
```
Add to `requirements.txt`:
```
pypdf
python-docx
python-pptx
```

- [ ] **Step 2: Write failing test**

```python
# gamification/tests/test_lesson_text.py
import io
from django.test import TestCase
from gamification.lesson_text import extract_text, UnsupportedFileType, EmptyContent


class LessonTextTests(TestCase):
    def test_txt_passthrough(self):
        f = io.BytesIO(b"Hello world. " * 30)
        f.name = "x.txt"
        self.assertIn("Hello world", extract_text(f))

    def test_unsupported_raises(self):
        f = io.BytesIO(b"xx"); f.name = "x.exe"
        with self.assertRaises(UnsupportedFileType):
            extract_text(f)

    def test_empty_raises(self):
        f = io.BytesIO(b"a"); f.name = "x.txt"
        with self.assertRaises(EmptyContent):
            extract_text(f)
```

- [ ] **Step 3: Run, expect FAIL**

- [ ] **Step 4: Implement**

```python
# gamification/lesson_text.py
"""[Classedge LMS] Extract plain text from uploaded lesson files."""
import os
import re

MAX_CHARS = 20_000
MIN_USABLE_CHARS = 200


class UnsupportedFileType(Exception):
    pass


class EmptyContent(Exception):
    pass


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]


def _from_pdf(file_obj) -> str:
    from pypdf import PdfReader
    reader = PdfReader(file_obj)
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def _from_docx(file_obj) -> str:
    from docx import Document
    doc = Document(file_obj)
    return "\n".join(p.text for p in doc.paragraphs)


def _from_pptx(file_obj) -> str:
    from pptx import Presentation
    prs = Presentation(file_obj)
    out = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                out.append(shape.text)
    return "\n".join(out)


def _from_txt(file_obj) -> str:
    raw = file_obj.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    return raw


_HANDLERS = {".pdf": _from_pdf, ".docx": _from_docx, ".pptx": _from_pptx, ".txt": _from_txt}


def extract_text(file_obj) -> str:
    name = getattr(file_obj, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    handler = _HANDLERS.get(ext)
    if handler is None:
        raise UnsupportedFileType(f"Unsupported file type: {ext or 'unknown'}")
    raw = handler(file_obj)
    cleaned = _clean(raw)
    if len(cleaned) < MIN_USABLE_CHARS:
        raise EmptyContent("Lesson file appears empty or unreadable.")
    return cleaned
```

- [ ] **Step 5: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_lesson_text -v 2
git add gamification/lesson_text.py gamification/tests/test_lesson_text.py requirements.txt
git commit -m "feat(gamification): lesson text extraction (PDF/DOCX/PPTX/TXT)"
```

---

### Task 8: AI provider abstraction

**Files:**
- Create: `gamification/ai_providers/__init__.py`
- Create: `gamification/ai_providers/base.py`
- Create: `gamification/ai_providers/anthropic_provider.py`
- Create: `gamification/ai_providers/openai_provider.py`
- Test: `gamification/tests/test_ai_providers.py`

- [ ] **Step 1: Write test (using mocks; no real API call)**

```python
# gamification/tests/test_ai_providers.py
from unittest.mock import patch, MagicMock
from django.test import TestCase
from gamification.ai_providers import get_provider
from gamification.ai_providers.anthropic_provider import AnthropicProvider
from gamification.ai_providers.openai_provider import OpenAIProvider
from gamification.quest_settings_models import OrganizationQuestSettings


class ProviderFactoryTests(TestCase):
    def test_factory_returns_anthropic_by_default(self):
        OrganizationQuestSettings.load()
        self.assertIsInstance(get_provider(), AnthropicProvider)

    def test_factory_returns_openai_when_configured(self):
        s = OrganizationQuestSettings.load()
        s.ai_provider = "openai"; s.save()
        self.assertIsInstance(get_provider(), OpenAIProvider)


class AnthropicProviderTests(TestCase):
    @patch("gamification.ai_providers.anthropic_provider.anthropic.Anthropic")
    def test_generate_returns_dict(self, mock_cls):
        client = MagicMock()
        client.messages.create.return_value.content = [MagicMock(text='{"quests":[]}')]
        mock_cls.return_value = client
        p = AnthropicProvider()
        out = p.generate("some lesson text", n=3)
        self.assertIn("quests", out)
```

- [ ] **Step 2: Run, expect FAIL**

- [ ] **Step 3: Create base + prompt**

```python
# gamification/ai_providers/base.py
"""[Classedge LMS] Shared prompt + JSON contract for quest generation providers."""

SYSTEM_PROMPT = (
    "You generate learning quests from lesson text. Return ONLY valid JSON, no prose. "
    "Each quest must have 'kind' (quiz|reading_check|task), 'title' (<=200 chars), 'body', "
    "'payload', and 'source_chunk' (exact excerpt). "
    "quiz.payload = {options: [4 strings], correct_index: int}. "
    "reading_check.payload = {reading: str, question: str, expected_keywords: [str,...]}. "
    "task.payload = {rubric: str, self_check: bool}. "
    "Mix kinds across the set. Titles must be unique."
)


def user_prompt(text: str, n: int) -> str:
    return (
        f"Generate exactly {n} quests from this lesson. Return JSON: "
        f'{{"quests": [...]}}\n\nLESSON:\n{text}'
    )
```

```python
# gamification/ai_providers/__init__.py
from gamification.ai_providers.anthropic_provider import AnthropicProvider
from gamification.ai_providers.openai_provider import OpenAIProvider
from gamification.quest_settings_models import OrganizationQuestSettings

_REGISTRY = {"anthropic": AnthropicProvider, "openai": OpenAIProvider}


def get_provider():
    s = OrganizationQuestSettings.load()
    return _REGISTRY[s.ai_provider]()
```

- [ ] **Step 4: Anthropic provider**

```python
# gamification/ai_providers/anthropic_provider.py
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
```

- [ ] **Step 5: OpenAI provider**

```python
# gamification/ai_providers/openai_provider.py
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
```

Add to `requirements.txt` if absent: `openai`

- [ ] **Step 6: Tests pass & commit**

```bash
pip install openai
python manage.py test gamification.tests.test_ai_providers -v 2
git add gamification/ai_providers gamification/tests/test_ai_providers.py requirements.txt
git commit -m "feat(gamification): pluggable AI providers (Anthropic/OpenAI)"
```

---

### Task 9: JSON schema validator

**Files:**
- Create: `gamification/quest_schema.py`
- Test: `gamification/tests/test_quest_schema.py`

- [ ] **Step 1: Install `jsonschema`**

```bash
pip install jsonschema
```
Add `jsonschema` to `requirements.txt`.

- [ ] **Step 2: Write failing test**

```python
# gamification/tests/test_quest_schema.py
from django.test import TestCase
from gamification.quest_schema import validate_quest_set, QuestSchemaError, validate_single_quest


VALID_QUIZ = {
    "kind": "quiz", "title": "Q1", "body": "what?",
    "payload": {"options": ["a", "b", "c", "d"], "correct_index": 0},
    "source_chunk": "..."
}


class QuestSchemaTests(TestCase):
    def test_valid_passes(self):
        validate_quest_set({"quests": [VALID_QUIZ]}, expected_n=1)

    def test_wrong_n_fails(self):
        with self.assertRaises(QuestSchemaError):
            validate_quest_set({"quests": [VALID_QUIZ]}, expected_n=2)

    def test_duplicate_titles_fail(self):
        with self.assertRaises(QuestSchemaError):
            validate_quest_set({"quests": [VALID_QUIZ, dict(VALID_QUIZ)]}, expected_n=2)

    def test_quiz_missing_correct_index_fails(self):
        bad = {**VALID_QUIZ, "payload": {"options": ["a", "b", "c", "d"]}}
        with self.assertRaises(QuestSchemaError):
            validate_single_quest(bad)

    def test_unknown_kind_fails(self):
        bad = {**VALID_QUIZ, "kind": "weird"}
        with self.assertRaises(QuestSchemaError):
            validate_single_quest(bad)
```

- [ ] **Step 3: Implement**

```python
# gamification/quest_schema.py
"""[Classedge LMS] Validate AI/uploaded quest JSON against a strict schema."""
from jsonschema import validate, ValidationError


class QuestSchemaError(Exception):
    pass


_QUIZ_PAYLOAD = {
    "type": "object",
    "required": ["options", "correct_index"],
    "properties": {
        "options": {"type": "array", "minItems": 2, "maxItems": 6, "items": {"type": "string"}},
        "correct_index": {"type": "integer", "minimum": 0},
    },
}
_READING_PAYLOAD = {
    "type": "object",
    "required": ["reading", "question", "expected_keywords"],
    "properties": {
        "reading": {"type": "string"},
        "question": {"type": "string"},
        "expected_keywords": {"type": "array", "items": {"type": "string"}, "minItems": 1},
    },
}
_TASK_PAYLOAD = {
    "type": "object",
    "required": ["rubric", "self_check"],
    "properties": {"rubric": {"type": "string"}, "self_check": {"type": "boolean"}},
}

_QUEST = {
    "type": "object",
    "required": ["kind", "title", "body", "payload"],
    "properties": {
        "kind": {"enum": ["quiz", "reading_check", "task"]},
        "title": {"type": "string", "maxLength": 200, "minLength": 1},
        "body": {"type": "string", "minLength": 1},
        "payload": {"type": "object"},
        "source_chunk": {"type": "string"},
        "counts_toward_grade": {"type": "boolean"},
    },
}


def validate_single_quest(q: dict) -> None:
    try:
        validate(q, _QUEST)
        if q["kind"] == "quiz":
            validate(q["payload"], _QUIZ_PAYLOAD)
            opts = q["payload"]["options"]
            if q["payload"]["correct_index"] >= len(opts):
                raise QuestSchemaError("quiz.correct_index out of range")
        elif q["kind"] == "reading_check":
            validate(q["payload"], _READING_PAYLOAD)
        elif q["kind"] == "task":
            validate(q["payload"], _TASK_PAYLOAD)
    except ValidationError as e:
        raise QuestSchemaError(str(e))


def validate_quest_set(data: dict, expected_n: int) -> None:
    if not isinstance(data, dict) or "quests" not in data:
        raise QuestSchemaError("Top-level must be {'quests': [...]}.")
    quests = data["quests"]
    if not isinstance(quests, list):
        raise QuestSchemaError("'quests' must be a list.")
    if len(quests) != expected_n:
        raise QuestSchemaError(f"Expected {expected_n} quests, got {len(quests)}.")
    titles = set()
    for q in quests:
        validate_single_quest(q)
        if q["title"] in titles:
            raise QuestSchemaError(f"Duplicate title: {q['title']}")
        titles.add(q["title"])
```

- [ ] **Step 4: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_quest_schema -v 2
git add gamification/quest_schema.py gamification/tests/test_quest_schema.py requirements.txt
git commit -m "feat(gamification): strict JSON schema for quest sets"
```

---

## Phase 5 — Generation Pipeline & Importer

### Task 10: Generation service (threaded job runner)

**Files:**
- Create: `gamification/quest_generation.py`
- Test: `gamification/tests/test_quest_generation.py`

- [ ] **Step 1: Write failing test (mocked provider)**

```python
# gamification/tests/test_quest_generation.py
import io
from unittest.mock import patch
from django.test import TestCase
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestGenerationJob
from gamification.quest_generation import run_generation_job


FAKE_OUTPUT = {"quests": [
    {"kind": "quiz", "title": f"Q{i}", "body": "b",
     "payload": {"options": ["a", "b", "c", "d"], "correct_index": 0},
     "source_chunk": "..."} for i in range(3)
]}


class GenerationTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="S", quest_count_per_lesson=3)
        self.module = Module.objects.create(file_name="L", subject=self.subject)

    @patch("gamification.quest_generation.extract_text", return_value="A" * 500)
    @patch("gamification.quest_generation.get_provider")
    def test_happy_path(self, mock_prov, _):
        mock_prov.return_value.generate.return_value = FAKE_OUTPUT
        job = QuestGenerationJob.objects.create(module=self.module)
        run_generation_job(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, "complete")
        self.assertEqual(Quest.objects.filter(module=self.module).count(), 3)
        self.assertTrue(all(q.status == "draft" for q in Quest.objects.all()))

    @patch("gamification.quest_generation.extract_text", side_effect=Exception("unsupported"))
    def test_extraction_failure_marks_job_failed(self, _):
        job = QuestGenerationJob.objects.create(module=self.module)
        run_generation_job(job.id)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIn("unsupported", job.error)
```

- [ ] **Step 2: Implement**

```python
# gamification/quest_generation.py
"""[Classedge LMS] Background-thread quest generation job runner."""
import threading
from django.utils import timezone
from django.db import transaction
from gamification.ai_providers import get_provider
from gamification.lesson_text import extract_text
from gamification.quest_models import Quest, QuestGenerationJob
from gamification.quest_schema import validate_quest_set, QuestSchemaError
from gamification.quest_settings_models import OrganizationQuestSettings


def start_generation(module) -> QuestGenerationJob:
    """Create job + spawn worker thread. Returns job (status='queued')."""
    existing = QuestGenerationJob.objects.filter(module=module, status__in=["queued", "running"]).exists()
    if existing:
        raise RuntimeError("A generation job is already running for this module.")
    job = QuestGenerationJob.objects.create(module=module)
    t = threading.Thread(target=run_generation_job, args=(job.id,), daemon=True)
    t.start()
    return job


def run_generation_job(job_id: int) -> None:
    """Synchronous body of the worker thread (also directly callable in tests)."""
    job = QuestGenerationJob.objects.select_related("module__subject").get(pk=job_id)
    job.status = "running"; job.save(update_fields=["status"])
    try:
        n = job.module.subject.quest_count_per_lesson
        text = extract_text(job.module.file)
        provider = get_provider()
        provider_name = OrganizationQuestSettings.load().ai_provider
        try:
            data = provider.generate(text, n)
            validate_quest_set(data, expected_n=n)
        except QuestSchemaError as first_err:
            # one retry
            data = provider.generate(text + f"\n\nPrevious output invalid: {first_err}. Return valid JSON only.", n)
            validate_quest_set(data, expected_n=n)

        with transaction.atomic():
            # Overwrite drafts only
            Quest.objects.filter(module=job.module, status="draft").delete()
            for i, q in enumerate(data["quests"], start=1):
                Quest.objects.create(
                    module=job.module, order=i, kind=q["kind"], title=q["title"],
                    body=q["body"], payload=q["payload"], status="draft",
                    ai_provider=provider_name, source_chunk=q.get("source_chunk", ""),
                )
        job.status = "complete"
    except Exception as e:
        job.status = "failed"
        job.error = str(e)[:2000]
    finally:
        job.finished_at = timezone.now()
        job.save()
```

- [ ] **Step 3: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_quest_generation -v 2
git add gamification/quest_generation.py gamification/tests/test_quest_generation.py
git commit -m "feat(gamification): threaded quest generation job runner"
```

---

### Task 11: Bulk importer (CSV/JSON)

**Files:**
- Create: `gamification/quest_import.py`
- Test: `gamification/tests/test_quest_import.py`

- [ ] **Step 1: Write failing test**

```python
# gamification/tests/test_quest_import.py
import io, json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest
from gamification.quest_import import import_quests, ImportError as QuestImportError


CSV_OK = (
    'kind,title,body,payload_json,counts_toward_grade\n'
    'quiz,"Q1","b","{""options"":[""a"",""b"",""c"",""d""],""correct_index"":0}",true\n'
    'task,"T1","do it","{""rubric"":""r"",""self_check"":true}",false\n'
)


class ImportTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="S")
        self.module = Module.objects.create(file_name="L", subject=self.subject)

    def test_csv_happy_path(self):
        f = SimpleUploadedFile("q.csv", CSV_OK.encode("utf-8"))
        n = import_quests(self.module, f)
        self.assertEqual(n, 2)
        self.assertEqual(Quest.objects.filter(module=self.module).count(), 2)
        self.assertFalse(Quest.objects.get(title="T1").counts_toward_grade)

    def test_json_happy_path(self):
        items = [{"kind": "quiz", "title": "JQ", "body": "b",
                  "payload": {"options": ["a", "b", "c", "d"], "correct_index": 0}}]
        f = SimpleUploadedFile("q.json", json.dumps(items).encode("utf-8"))
        n = import_quests(self.module, f)
        self.assertEqual(n, 1)

    def test_malformed_rejects_all(self):
        bad = CSV_OK + 'quiz,"badrow","b","NOT-JSON",true\n'
        f = SimpleUploadedFile("q.csv", bad.encode("utf-8"))
        with self.assertRaises(QuestImportError):
            import_quests(self.module, f)
        self.assertEqual(Quest.objects.filter(module=self.module).count(), 0)

    def test_oversize_rejected(self):
        big = SimpleUploadedFile("q.csv", b"x" * (2 * 1024 * 1024))
        with self.assertRaises(QuestImportError):
            import_quests(self.module, big)
```

- [ ] **Step 2: Implement**

```python
# gamification/quest_import.py
"""[Classedge LMS] CSV/JSON bulk import of teacher-authored quests."""
import csv
import io
import json
import os
from django.db import transaction
from gamification.quest_models import Quest
from gamification.quest_schema import validate_single_quest, QuestSchemaError

MAX_BYTES = 1 * 1024 * 1024
MAX_ROWS = 200


class ImportError(Exception):
    pass


def _read(file_obj) -> bytes:
    data = file_obj.read()
    if len(data) > MAX_BYTES:
        raise ImportError(f"File too large (>{MAX_BYTES} bytes).")
    return data


def _parse_csv(data: bytes) -> list[dict]:
    text = data.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    items = []
    for i, row in enumerate(reader, start=2):
        try:
            payload = json.loads(row["payload_json"])
        except (json.JSONDecodeError, KeyError) as e:
            raise ImportError(f"Row {i}: invalid payload_json ({e})")
        counts = (row.get("counts_toward_grade", "true").strip().lower() in ("1", "true", "yes"))
        items.append({
            "kind": row.get("kind", "").strip(),
            "title": row.get("title", "").strip(),
            "body": row.get("body", "").strip(),
            "payload": payload,
            "counts_toward_grade": counts,
        })
    return items


def _parse_json(data: bytes) -> list[dict]:
    try:
        parsed = json.loads(data.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError as e:
        raise ImportError(f"Invalid JSON: {e}")
    if not isinstance(parsed, list):
        raise ImportError("JSON root must be a list of quests.")
    return parsed


def import_quests(module, file_obj) -> int:
    name = getattr(file_obj, "name", "")
    ext = os.path.splitext(name)[1].lower()
    data = _read(file_obj)
    if ext == ".csv":
        items = _parse_csv(data)
    elif ext == ".json":
        items = _parse_json(data)
    else:
        raise ImportError("File must be .csv or .json")

    if len(items) > MAX_ROWS:
        raise ImportError(f"Too many quests ({len(items)}); cap is {MAX_ROWS}.")
    if not items:
        raise ImportError("No quests found in file.")

    for i, q in enumerate(items, start=1):
        try:
            validate_single_quest(q)
        except QuestSchemaError as e:
            raise ImportError(f"Item {i} invalid: {e}")

    start_order = (Quest.objects.filter(module=module).order_by("-order").values_list("order", flat=True).first() or 0) + 1
    with transaction.atomic():
        for offset, q in enumerate(items):
            Quest.objects.create(
                module=module, order=start_order + offset,
                kind=q["kind"], title=q["title"], body=q["body"],
                payload=q["payload"], status="draft", ai_provider="upload",
                counts_toward_grade=q.get("counts_toward_grade", True),
            )
    return len(items)
```

- [ ] **Step 3: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_quest_import -v 2
git add gamification/quest_import.py gamification/tests/test_quest_import.py
git commit -m "feat(gamification): bulk CSV/JSON quest importer"
```

---

## Phase 6 — Teacher Views & URLs

### Task 12: Teacher quest views (mode-gated entry points + review/publish)

**Files:**
- Create: `gamification/quest_views.py`
- Create: `gamification/urls_quests.py`
- Modify: `gamification/urls.py` (include the new url module)
- Create: `templates/teacher/quests/mode_select.html`
- Create: `templates/teacher/quests/review.html`
- Create: `templates/teacher/quests/upload.html`
- Test: `gamification/tests/test_quest_views.py`

- [ ] **Step 1: Write failing test (covering 403 on disabled mode)**

```python
# gamification/tests/test_quest_views.py
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest
from gamification.quest_settings_models import OrganizationQuestSettings

User = get_user_model()


class QuestViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("t", password="x")
        self.subject = Subject.objects.create(subject_name="S", quest_count_per_lesson=3)
        self.module = Module.objects.create(file_name="L", subject=self.subject)
        self.c = Client(); self.c.force_login(self.user)

    def test_mode_select_shows_enabled_modes(self):
        s = OrganizationQuestSettings.load()
        s.ai_mode_enabled = True; s.manual_mode_enabled = False; s.upload_mode_enabled = True; s.save()
        r = self.c.get(reverse("quest_mode_select", args=[self.module.id]))
        self.assertContains(r, "Generate with AI")
        self.assertNotContains(r, "Create manually")
        self.assertContains(r, "Upload from file")

    def test_generate_403_when_ai_disabled(self):
        s = OrganizationQuestSettings.load(); s.ai_mode_enabled = False; s.save()
        r = self.c.post(reverse("quest_generate", args=[self.module.id]))
        self.assertEqual(r.status_code, 403)

    def test_manual_create_makes_empty_draft_quest(self):
        s = OrganizationQuestSettings.load(); s.manual_mode_enabled = True; s.save()
        r = self.c.post(reverse("quest_manual_init", args=[self.module.id]))
        self.assertEqual(r.status_code, 302)

    def test_publish_flips_drafts(self):
        Quest.objects.create(module=self.module, order=1, kind="quiz", title="q",
                             body="b", payload={"options": ["a","b","c","d"], "correct_index": 0})
        r = self.c.post(reverse("quest_publish_all", args=[self.module.id]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Quest.objects.filter(module=self.module, status="published").count(), 1)
```

- [ ] **Step 2: Implement views**

```python
# gamification/quest_views.py
"""[Classedge LMS] Teacher views for quest authoring (AI / manual / upload)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from module.models.module import Module
from gamification.quest_generation import start_generation
from gamification.quest_import import import_quests, ImportError as QuestImportError
from gamification.quest_models import Quest, QuestGenerationJob
from gamification.quest_settings_models import OrganizationQuestSettings


def _settings():
    return OrganizationQuestSettings.load()


@login_required
def quest_mode_select(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    s = _settings()
    existing = Quest.objects.filter(module=module).exists()
    return render(request, "teacher/quests/mode_select.html", {
        "module": module, "settings": s, "has_quests": existing,
    })


@login_required
@require_POST
def quest_generate(request, module_id):
    if not _settings().ai_mode_enabled:
        return HttpResponseForbidden("AI mode is disabled by the administrator.")
    module = get_object_or_404(Module, pk=module_id)
    try:
        job = start_generation(module)
    except RuntimeError as e:
        messages.error(request, str(e))
        return redirect("quest_mode_select", module_id=module.id)
    return redirect("quest_review", module_id=module.id)


@login_required
def quest_job_status(request, job_id):
    job = get_object_or_404(QuestGenerationJob, pk=job_id)
    return JsonResponse({"status": job.status, "error": job.error})


@login_required
@require_POST
def quest_manual_init(request, module_id):
    if not _settings().manual_mode_enabled:
        return HttpResponseForbidden("Manual mode is disabled.")
    module = get_object_or_404(Module, pk=module_id)
    return redirect("quest_review", module_id=module.id)


@login_required
def quest_upload(request, module_id):
    if not _settings().upload_mode_enabled:
        return HttpResponseForbidden("Upload mode is disabled.")
    module = get_object_or_404(Module, pk=module_id)
    if request.method == "POST" and request.FILES.get("file"):
        try:
            n = import_quests(module, request.FILES["file"])
        except QuestImportError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Imported {n} quests as drafts.")
            return redirect("quest_review", module_id=module.id)
    return render(request, "teacher/quests/upload.html", {"module": module})


@login_required
def quest_review(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    drafts = Quest.objects.filter(module=module, status="draft").order_by("order")
    published = Quest.objects.filter(module=module, status="published").order_by("order")
    return render(request, "teacher/quests/review.html", {
        "module": module, "drafts": drafts, "published": published,
    })


@login_required
@require_POST
def quest_publish_all(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    Quest.objects.filter(module=module, status="draft").update(status="published")
    messages.success(request, "Drafts published.")
    return redirect("quest_review", module_id=module.id)


@login_required
@require_POST
def quest_toggle_grade(request, quest_id):
    q = get_object_or_404(Quest, pk=quest_id)
    q.counts_toward_grade = not q.counts_toward_grade
    q.save(update_fields=["counts_toward_grade"])
    return redirect("quest_review", module_id=q.module_id)


@login_required
@require_POST
def quest_delete(request, quest_id):
    q = get_object_or_404(Quest, pk=quest_id)
    mid = q.module_id; q.delete()
    return redirect("quest_review", module_id=mid)
```

- [ ] **Step 3: URLs**

```python
# gamification/urls_quests.py
from django.urls import path
from gamification import quest_views as v

urlpatterns = [
    path("quests/module/<int:module_id>/", v.quest_mode_select, name="quest_mode_select"),
    path("quests/module/<int:module_id>/generate/", v.quest_generate, name="quest_generate"),
    path("quests/job/<int:job_id>/", v.quest_job_status, name="quest_job_status"),
    path("quests/module/<int:module_id>/manual/", v.quest_manual_init, name="quest_manual_init"),
    path("quests/module/<int:module_id>/upload/", v.quest_upload, name="quest_upload"),
    path("quests/module/<int:module_id>/review/", v.quest_review, name="quest_review"),
    path("quests/module/<int:module_id>/publish/", v.quest_publish_all, name="quest_publish_all"),
    path("quests/<int:quest_id>/toggle-grade/", v.quest_toggle_grade, name="quest_toggle_grade"),
    path("quests/<int:quest_id>/delete/", v.quest_delete, name="quest_delete"),
]
```

In `gamification/urls.py`, append:
```python
from django.urls import include
urlpatterns += [path("", include("gamification.urls_quests"))]
```

- [ ] **Step 4: Templates**

```html
<!-- templates/teacher/quests/mode_select.html -->
{% extends 'base.html' %}{% block content %}
<div class="container" style="max-width:720px;padding:24px;">
  <h2>Add quests to {{ module.file_name }}</h2>
  {% if has_quests %}
    <p><a href="{% url 'quest_review' module.id %}">Manage existing quests →</a></p>
  {% endif %}
  <div style="display:flex;gap:16px;margin-top:16px;flex-wrap:wrap;">
    {% if settings.ai_mode_enabled %}
    <form method="post" action="{% url 'quest_generate' module.id %}">{% csrf_token %}
      <button type="submit" class="btn btn-primary">Generate with AI</button>
    </form>{% endif %}
    {% if settings.manual_mode_enabled %}
    <form method="post" action="{% url 'quest_manual_init' module.id %}">{% csrf_token %}
      <button type="submit" class="btn btn-secondary">Create manually</button>
    </form>{% endif %}
    {% if settings.upload_mode_enabled %}
    <a class="btn btn-secondary" href="{% url 'quest_upload' module.id %}">Upload from file</a>
    {% endif %}
  </div>
</div>{% endblock %}
```

```html
<!-- templates/teacher/quests/upload.html -->
{% extends 'base.html' %}{% block content %}
<div class="container" style="max-width:640px;padding:24px;">
  <h2>Upload quests for {{ module.file_name }}</h2>
  <p>Accepted: .csv or .json (max 1 MB, 200 quests).</p>
  {% if messages %}{% for m in messages %}<div class="alert">{{ m }}</div>{% endfor %}{% endif %}
  <form method="post" enctype="multipart/form-data">{% csrf_token %}
    <input type="file" name="file" accept=".csv,.json" required>
    <button type="submit" class="btn btn-primary">Upload</button>
  </form>
  <p style="margin-top:24px;"><a href="{% url 'quest_mode_select' module.id %}">← Back</a></p>
</div>{% endblock %}
```

```html
<!-- templates/teacher/quests/review.html -->
{% extends 'base.html' %}{% block content %}
<div class="container" style="max-width:960px;padding:24px;">
  <h2>Review quests — {{ module.file_name }}</h2>
  {% if drafts %}
    <h3>Drafts ({{ drafts.count }})</h3>
    <form method="post" action="{% url 'quest_publish_all' module.id %}">{% csrf_token %}
      <button type="submit" class="btn btn-success">Publish all drafts</button>
    </form>
    <ul>{% for q in drafts %}<li>
      <strong>{{ q.order }}. [{{ q.kind }}] {{ q.title }}</strong> — {{ q.body|truncatechars:100 }}
      <form style="display:inline" method="post" action="{% url 'quest_toggle_grade' q.id %}">{% csrf_token %}
        <button type="submit">{{ q.counts_toward_grade|yesno:"Graded ✓,Practice only" }}</button>
      </form>
      <form style="display:inline" method="post" action="{% url 'quest_delete' q.id %}">{% csrf_token %}
        <button type="submit" onclick="return confirm('Delete?')">Delete</button>
      </form>
    </li>{% endfor %}</ul>
  {% endif %}
  {% if published %}
    <h3>Published ({{ published.count }})</h3>
    <ul>{% for q in published %}<li>{{ q.order }}. [{{ q.kind }}] {{ q.title }}</li>{% endfor %}</ul>
  {% endif %}
  {% if not drafts and not published %}<p>No quests yet. <a href="{% url 'quest_mode_select' module.id %}">Add some →</a></p>{% endif %}
</div>{% endblock %}
```

- [ ] **Step 5: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_quest_views -v 2
git add gamification/quest_views.py gamification/urls_quests.py gamification/urls.py templates/teacher/quests gamification/tests/test_quest_views.py
git commit -m "feat(gamification): teacher quest views with mode gating"
```

---

## Phase 7 — Student Player & Progress

### Task 13: Quest player + auto-grade + StudentProgress signal

**Files:**
- Create: `gamification/quest_player_views.py`
- Create: `gamification/quest_autograde.py`
- Create: `gamification/signals_quest.py`
- Modify: `gamification/apps.py` (import signals on ready)
- Create: `templates/student/quests/play.html`
- Modify: `gamification/urls_quests.py` (add student routes)
- Test: `gamification/tests/test_quest_player.py`

- [ ] **Step 1: Failing test**

```python
# gamification/tests/test_quest_player.py
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from module.models.module import Module
from module.models.student_progress import StudentProgress
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt

User = get_user_model()


class QuestPlayerTests(TestCase):
    def setUp(self):
        self.s = User.objects.create_user("s", password="x")
        self.subject = Subject.objects.create(subject_name="S")
        self.module = Module.objects.create(file_name="L", subject=self.subject)
        self.q = Quest.objects.create(module=self.module, order=1, kind="quiz",
                                      title="t", body="2+2?", status="published",
                                      payload={"options": ["3", "4", "5", "6"], "correct_index": 1})
        self.c = Client(); self.c.force_login(self.s)

    def test_submit_correct_quiz(self):
        r = self.c.post(reverse("quest_play_submit", args=[self.q.id]), {"answer": "1"})
        self.assertEqual(r.status_code, 302)
        a = QuestAttempt.objects.get(quest=self.q, student=self.s)
        self.assertTrue(a.is_correct); self.assertEqual(a.score, 1.0)

    def test_completing_all_marks_module_complete(self):
        self.c.post(reverse("quest_play_submit", args=[self.q.id]), {"answer": "1"})
        sp = StudentProgress.objects.get(student=self.s, module=self.module)
        self.assertTrue(sp.completed)
```

- [ ] **Step 2: Auto-grade**

```python
# gamification/quest_autograde.py
"""[Classedge LMS] Grade a single student submission against a Quest's payload."""


def grade(quest, submitted_answer) -> tuple[bool, float]:
    """Return (is_correct, score 0..1)."""
    kind = quest.kind
    p = quest.payload or {}
    if kind == "quiz":
        try:
            idx = int(submitted_answer)
        except (TypeError, ValueError):
            return False, 0.0
        ok = idx == p.get("correct_index")
        return ok, (1.0 if ok else 0.0)
    if kind == "reading_check":
        text = (submitted_answer or "").lower()
        keywords = [k.lower() for k in p.get("expected_keywords", [])]
        if not keywords:
            return False, 0.0
        hits = sum(1 for k in keywords if k in text)
        ratio = hits / len(keywords)
        return ratio >= 0.5, round(ratio, 2)
    if kind == "task":
        # self_check tasks: the student's "yes I did this" is the score
        if p.get("self_check") and submitted_answer == "done":
            return True, 1.0
        # teacher-reviewed: record attempt but score stays 0 until teacher grades (out of scope here)
        return False, 0.0
    return False, 0.0
```

- [ ] **Step 3: Signal**

```python
# gamification/signals_quest.py
"""[Classedge LMS] Recompute StudentProgress.completed when quest attempts change."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from gamification.quest_models import Quest, QuestAttempt
from module.models.student_progress import StudentProgress


@receiver(post_save, sender=QuestAttempt)
def recompute_module_progress(sender, instance, **kwargs):
    module = instance.quest.module
    student = instance.student
    published = Quest.objects.filter(module=module, status="published")
    if not published.exists():
        return
    correct_ids = set(QuestAttempt.objects.filter(
        quest__in=published, student=student, is_correct=True
    ).values_list("quest_id", flat=True))
    all_done = set(published.values_list("id", flat=True)) == correct_ids
    sp, _ = StudentProgress.objects.get_or_create(student=student, module=module)
    if sp.completed != all_done:
        sp.completed = all_done
        sp.save(update_fields=["completed"])
```

In `gamification/apps.py`:
```python
class GamificationConfig(AppConfig):
    # ... existing fields ...
    def ready(self):
        from gamification import signals_quest  # noqa: F401
        # keep any other existing imports here
```

If `signals` is already imported elsewhere in `ready`, just append the new import line.

- [ ] **Step 4: Player views**

```python
# gamification/quest_player_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from gamification.quest_autograde import grade
from gamification.quest_models import Quest, QuestAttempt


@login_required
def quest_play(request, module_id):
    quests = Quest.objects.filter(module_id=module_id, status="published").order_by("order")
    attempted = set(QuestAttempt.objects.filter(
        quest__in=quests, student=request.user, is_correct=True
    ).values_list("quest_id", flat=True))
    next_q = next((q for q in quests if q.id not in attempted), None)
    return render(request, "student/quests/play.html", {
        "quest": next_q, "module_id": module_id,
        "remaining": quests.count() - len(attempted),
    })


@login_required
@require_POST
def quest_play_submit(request, quest_id):
    quest = get_object_or_404(Quest, pk=quest_id, status="published")
    answer = request.POST.get("answer", "")
    ok, score = grade(quest, answer)
    QuestAttempt.objects.update_or_create(
        quest=quest, student=request.user,
        defaults={"submitted_answer": {"raw": answer}, "is_correct": ok, "score": score},
    )
    return redirect("quest_play", module_id=quest.module_id)
```

- [ ] **Step 5: Template**

```html
<!-- templates/student/quests/play.html -->
{% extends 'student_base.html' %}{% block content %}
<div class="container" style="max-width:640px;padding:24px;">
  {% if quest %}
    <p style="color:#888;">{{ remaining }} quests remaining</p>
    <h2>{{ quest.title }}</h2>
    <p>{{ quest.body }}</p>
    <form method="post" action="{% url 'quest_play_submit' quest.id %}">{% csrf_token %}
      {% if quest.kind == 'quiz' %}
        {% for opt in quest.payload.options %}
          <label style="display:block;"><input type="radio" name="answer" value="{{ forloop.counter0 }}" required> {{ opt }}</label>
        {% endfor %}
      {% elif quest.kind == 'reading_check' %}
        <div style="background:#f5f5f5;padding:12px;margin:12px 0;">{{ quest.payload.reading }}</div>
        <p>{{ quest.payload.question }}</p>
        <textarea name="answer" rows="4" required style="width:100%;"></textarea>
      {% elif quest.kind == 'task' %}
        <div style="background:#f5f5f5;padding:12px;margin:12px 0;">Rubric: {{ quest.payload.rubric }}</div>
        {% if quest.payload.self_check %}
          <label><input type="checkbox" name="answer" value="done" required> I have completed this task</label>
        {% else %}
          <textarea name="answer" rows="4" required style="width:100%;" placeholder="Describe your work"></textarea>
        {% endif %}
      {% endif %}
      <button type="submit" class="btn btn-primary" style="margin-top:12px;">Submit</button>
    </form>
  {% else %}
    <h2>All quests complete!</h2>
    <p><a href="{% url 'quest_map_picker' %}">Back to quest map</a></p>
  {% endif %}
</div>{% endblock %}
```

- [ ] **Step 6: URLs**

Append to `gamification/urls_quests.py`:
```python
from gamification import quest_player_views as pv
urlpatterns += [
    path("quests/module/<int:module_id>/play/", pv.quest_play, name="quest_play"),
    path("quests/<int:quest_id>/submit/", pv.quest_play_submit, name="quest_play_submit"),
]
```

- [ ] **Step 7: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_quest_player -v 2
git add gamification/quest_player_views.py gamification/quest_autograde.py gamification/signals_quest.py gamification/apps.py gamification/urls_quests.py templates/student/quests gamification/tests/test_quest_player.py
git commit -m "feat(gamification): student quest player + autograde + progress signal"
```

---

## Phase 8 — Student Surfaces Polish

### Task 14: Quest map node state from quest completion + quest-level badge

**Files:**
- Modify: `gamification/views.py` (the `quest_map` view, around line 426)
- Modify: `templates/student/gamification/quest_map.html` (add level badge)
- Test: `gamification/tests/test_quest_map_node_state.py`

- [ ] **Step 1: Read current view**

Run: `grep -n "def quest_map" gamification/views.py`. Note current state-derivation logic.

- [ ] **Step 2: Write failing test**

```python
# gamification/tests/test_quest_map_node_state.py
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest, QuestAttempt

User = get_user_model()


class QuestMapNodeStateTests(TestCase):
    def setUp(self):
        self.s = User.objects.create_user("s", password="x")
        self.subj = Subject.objects.create(subject_name="S")
        self.m1 = Module.objects.create(file_name="L1", subject=self.subj)
        self.m2 = Module.objects.create(file_name="L2", subject=self.subj)
        # m1 has one published quest, student completed it
        q = Quest.objects.create(module=self.m1, order=1, kind="quiz", title="t",
                                 body="b", status="published",
                                 payload={"options": ["a","b","c","d"], "correct_index": 0})
        QuestAttempt.objects.create(quest=q, student=self.s, is_correct=True, score=1.0)
        # m2 has a published quest, not attempted
        Quest.objects.create(module=self.m2, order=1, kind="quiz", title="u",
                             body="b", status="published",
                             payload={"options": ["a","b","c","d"], "correct_index": 0})

    def test_state_reflects_quest_completion(self):
        c = Client(); c.force_login(self.s)
        r = c.get(reverse("quest_map", args=[self.subj.id]))
        ctx_nodes = r.context["nodes"]
        states = {n["name"]: n["state"] for n in ctx_nodes}
        self.assertEqual(states["L1"], "done")
        self.assertIn(states["L2"], ("active", "locked"))
```

- [ ] **Step 3: Adjust `quest_map` view**

In `gamification/views.py`, replace the state-derivation block inside `quest_map` so a module is `done` only when **all** its published quests have correct attempts by the student (use the same logic as the signal). If the module has no published quests, fall back to the existing `StudentProgress.completed` value so legacy modules without quests still work.

```python
# at top of gamification/views.py
from gamification.quest_models import Quest, QuestAttempt
from gamification.quest_grading import get_student_quest_score

# inside quest_map(request, subject_id), where you build per-module state:
def _module_done(student, module):
    published = Quest.objects.filter(module=module, status="published")
    if not published.exists():
        # legacy fallback
        from module.models.student_progress import StudentProgress
        sp = StudentProgress.objects.filter(student=student, module=module).first()
        return bool(sp and sp.completed)
    correct = QuestAttempt.objects.filter(
        quest__in=published, student=student, is_correct=True
    ).values_list("quest_id", flat=True)
    return set(published.values_list("id", flat=True)) == set(correct)
```

Use `_module_done` to set `node.state = "done"` and to find the first not-done module as `active` (rest `locked`). Also compute `quest_level_pct = get_student_quest_score(student, subject, term)` (term inferred from the existing view; if not, pick the student's current term) and pass to template context.

- [ ] **Step 4: Add badge to template**

In `templates/student/gamification/quest_map.html`, just after the `<div class="qm-head">` block (around line 82), insert:
```html
{% if quest_level_pct is not None %}
<div class="qm-stat" style="margin-bottom:16px;">
  <div class="qm-stat-icon total"><i class="fas fa-star"></i></div>
  <div><div class="qm-stat-val">{{ quest_level_pct }}%</div><div class="qm-stat-lbl">Quest Level</div></div>
</div>
{% endif %}
```

- [ ] **Step 5: Tests pass & commit**

```bash
python manage.py test gamification.tests.test_quest_map_node_state -v 2
git add gamification/views.py templates/student/gamification/quest_map.html gamification/tests/test_quest_map_node_state.py
git commit -m "feat(quest-map): drive node state from quest completion + show quest level"
```

---

### Task 15: Add lesson-detail "Add quests" entry button

**Files:**
- Modify: `module/templates/lesson_detail.html` (or whatever template is used; verify with `grep -rn "module" templates/teacher/`)

- [ ] **Step 1: Locate template**

Run: `grep -rln "module.file_name\|Module Detail" module/templates templates 2>/dev/null | head -5`

- [ ] **Step 2: Add button**

In the located template, near the existing teacher action area, insert:
```html
{% if user.profile.role.name == 'Teacher' %}
<a class="btn btn-outline-primary" href="{% url 'quest_mode_select' module.id %}">
  <i class="fas fa-puzzle-piece"></i> Add quests
</a>
{% endif %}
```

- [ ] **Step 3: Smoke test manually**

Run dev server:
```bash
python manage.py runserver
```
Log in as a teacher, navigate to a lesson detail page, confirm the button appears and routes to the mode-select page.

- [ ] **Step 4: Commit**

```bash
git add <the template path>
git commit -m "feat(module): add 'Add quests' button to lesson detail"
```

---

## Phase 9 — Verification

### Task 16: End-to-end smoke + final commit

- [ ] **Step 1: Run entire gamification test module**

```bash
python manage.py test gamification gradebookcomponent.tests.test_grades_quest_branch subject.tests.test_quest_count_field -v 2
```
Expected: all tests pass.

- [ ] **Step 2: Manual smoke through three modes**

For each enabled mode (AI, manual, upload):
1. Log in as Registrar → `/accounts/registrar/quest-settings/` → confirm only the modes you want enabled.
2. Log in as Teacher → open a lesson → "Add quests" → see only the enabled buttons.
3. AI: upload a small PDF lesson, click "Generate with AI", watch for the redirect to review page with N drafts.
4. Manual: open review (empty), add a quest manually via a follow-up edit UI if available, publish.
5. Upload: upload `sample_quests.csv` matching the template; confirm drafts appear.
6. Publish all drafts.
7. Log in as Student → quest map → click subject → click lesson node → play through all quests.
8. Verify the module node turns `done` and `quest_level_pct` reflects performance.

- [ ] **Step 3: Gradebook smoke**

As Teacher: gradebook editor → add a component with `gradebook_category="quest_completion"` and `percentage=25` → view a student's grade page → confirm subtotal matches `quest_level_pct` and contributes 25% to the final grade.

- [ ] **Step 4: Final commit (only if anything changed during smoke)**

```bash
git status
# only commit if anything was fixed during smoke
```

---

## Self-Review Notes

- **Spec coverage:** all eight major spec sections (data model, gradebook integration, generation pipeline, manual & upload modes, UI surfaces, error handling, testing, rollout) have at least one task each.
- **Quest payload `counts_toward_grade` in schema:** added as optional property in schema; respected by importer; teacher can flip in review UI.
- **Decimal/float:** `get_student_quest_score` returns `float` (Task 5), `compute_component_subtotal` already returns float (Task 6 unchanged math).
- **Org gating enforcement:** server-side `HttpResponseForbidden` in each entry view (Task 12) + UI hide in template; test_quest_views exercises both.
- **Edit-published quests:** spec says allowed with warning; deferred to a future task (not blocking for v1). Open Question retained.
- **Manual entry "Add quest" inline editor:** Task 12 review template lists drafts; a follow-up sub-task may be needed for actual inline edit form. For v1, manual quests are added via the same upload flow OR by future inline form. Acceptable to ship as-is; document follow-up.
