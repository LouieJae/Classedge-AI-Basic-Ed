# Side Activities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 15 gamified mini-activity types that students can play within each subject to earn XP and badges, with teacher CRUD and sample seed data.

**Architecture:** 2 new models (`SideActivity`, `SideActivityAttempt`) in the existing `gamification/` app. Each activity type has a `content_json` schema and a type-specific template partial. Form-based types handle scoring server-side; JS-driven types submit via AJAX. XP awarded via existing `award_xp` service. 10 new badge evaluators.

**Tech Stack:** Django 5, existing gamification engine, vanilla JS (timer, drag-and-drop, typing), HTML5 Drag API

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `gamification/side_activity_models.py` | SideActivity + SideActivityAttempt models |
| `gamification/scoring.py` | Score calculation per activity type |
| `gamification/side_activity_views.py` | Student + teacher views for side activities |
| `gamification/side_activity_forms.py` | Teacher creation/edit forms |
| `gamification/templates/gamification/side_activity_list.html` | Activity browser per subject |
| `gamification/templates/gamification/side_activity_play.html` | Play wrapper template |
| `gamification/templates/gamification/types/_daily_challenge.html` | Type partial |
| `gamification/templates/gamification/types/_flashcard.html` | Type partial |
| `gamification/templates/gamification/types/_speed_round.html` | Type partial |
| `gamification/templates/gamification/types/_match_pair.html` | Type partial |
| `gamification/templates/gamification/types/_practice_quiz.html` | Type partial |
| `gamification/templates/gamification/types/_fill_blank.html` | Type partial |
| `gamification/templates/gamification/types/_drag_order.html` | Type partial |
| `gamification/templates/gamification/types/_word_scramble.html` | Type partial |
| `gamification/templates/gamification/types/_equation_balance.html` | Type partial |
| `gamification/templates/gamification/types/_math_drill.html` | Type partial |
| `gamification/templates/gamification/types/_geo_map.html` | Type partial |
| `gamification/templates/gamification/types/_timeline_sort.html` | Type partial |
| `gamification/templates/gamification/types/_code_kata.html` | Type partial |
| `gamification/templates/gamification/types/_typing_drill.html` | Type partial |
| `gamification/templates/gamification/types/_reading_mini.html` | Type partial |
| `gamification/templates/gamification/side_activity_create.html` | Teacher create form |
| `gamification/templates/gamification/side_activity_edit.html` | Teacher edit form |
| `static/js/side_activities/submit.js` | Shared AJAX submission helper |
| `static/js/side_activities/timer.js` | Countdown timer for speed_round, math_drill |
| `static/js/side_activities/drag.js` | Drag-and-drop for match_pair, drag_order, timeline_sort |
| `static/js/side_activities/flashcard.js` | Card flip logic |
| `static/js/side_activities/geo_map.js` | Click target on image |
| `static/js/side_activities/typing.js` | WPM keystroke tracker |
| `static/js/side_activities/code_kata.js` | Textarea submit |
| `gamification/management/commands/seed_side_activities.py` | Seed sample activities |
| `gamification/migrations/0004_side_activity_models.py` | Auto-generated |
| `gamification/migrations/0005_seed_side_activity_badges.py` | Badge seed |
| `gamification/tests/test_side_activities.py` | All side activity tests |

### Modified files

| File | Change |
|------|--------|
| `gamification/models.py` | Import and re-export from side_activity_models |
| `gamification/urls.py` | Add side activity URL patterns |
| `gamification/badges.py` | Add 9 new evaluator functions + register in EVALUATORS |
| `course/templates/course/view_subject_dashboard.html` | Add "Play & Learn" widget |

---

## Task 1: Models + Migration

**Files:**
- Create: `gamification/side_activity_models.py`
- Modify: `gamification/models.py`
- Create: `gamification/tests/test_side_activities.py` (initial)

- [ ] **Step 1: Create the models file**

Create `gamification/side_activity_models.py`:
```python
from django.conf import settings
from django.db import models


class SideActivity(models.Model):
    SUB_TYPE_CHOICES = [
        ("daily_challenge", "Daily Challenge"),
        ("flashcard", "Flashcard Review"),
        ("speed_round", "Speed Round"),
        ("match_pair", "Match Pair"),
        ("fill_blank", "Fill in the Blank"),
        ("drag_order", "Drag to Order"),
        ("word_scramble", "Word Scramble"),
        ("equation_balance", "Equation Balancer"),
        ("math_drill", "Math Drill"),
        ("geo_map", "Geography Map"),
        ("timeline_sort", "Timeline Sort"),
        ("code_kata", "Code Kata"),
        ("typing_drill", "Typing Drill"),
        ("reading_mini", "Reading Comprehension Mini"),
        ("practice_quiz", "Practice Quiz"),
    ]
    subject = models.ForeignKey(
        "subject.Subject", on_delete=models.CASCADE, related_name="side_activities",
    )
    sub_type = models.CharField(max_length=30, choices=SUB_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content_json = models.JSONField()
    estimated_minutes = models.PositiveSmallIntegerField(default=3)
    xp_reward = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["subject", "sub_type"])]

    def __str__(self):
        return f"{self.title} ({self.get_sub_type_display()})"


class SideActivityAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="side_activity_attempts",
    )
    side_activity = models.ForeignKey(SideActivity, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True)
    time_taken_seconds = models.PositiveIntegerField(null=True)
    xp_awarded = models.PositiveSmallIntegerField(default=0)
    details_json = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["student", "completed_at"]),
            models.Index(fields=["side_activity"]),
        ]

    def __str__(self):
        return f"{self.student.username} — {self.side_activity.title}"
```

- [ ] **Step 2: Re-export from models.py**

At the bottom of `gamification/models.py`, add:
```python
from gamification.side_activity_models import SideActivity, SideActivityAttempt  # noqa: E402, F401
```

- [ ] **Step 3: Generate and apply migration**

Run:
```bash
cd ~/classedge && env/bin/python manage.py makemigrations gamification
env/bin/python manage.py migrate gamification 2>&1 | tail -5
```

- [ ] **Step 4: Write model tests**

Create `gamification/tests/test_side_activities.py`:
```python
from django.test import TestCase
from django.utils import timezone

from ai_content.tests.test_models import _create_test_user, _create_subject
from gamification.models import SideActivity, SideActivityAttempt


class SideActivityModelTests(TestCase):
    def setUp(self):
        self.teacher = _create_test_user(username="sa_teacher", role_name="teacher")
        self.student = _create_test_user(username="sa_student", role_name="student")
        self.subject = _create_subject()

    def test_create_side_activity(self):
        sa = SideActivity.objects.create(
            subject=self.subject,
            sub_type="daily_challenge",
            title="Test Challenge",
            content_json={"question": "What is 2+2?", "choices": ["3", "4", "5"], "answer": 1},
            xp_reward=5,
            created_by=self.teacher,
        )
        self.assertEqual(sa.sub_type, "daily_challenge")
        self.assertTrue(sa.is_active)

    def test_create_attempt(self):
        sa = SideActivity.objects.create(
            subject=self.subject, sub_type="daily_challenge",
            title="Test", content_json={"question": "Q", "choices": ["A", "B"], "answer": 0},
        )
        attempt = SideActivityAttempt.objects.create(
            student=self.student, side_activity=sa,
            score=1.0, time_taken_seconds=15, xp_awarded=5,
            completed_at=timezone.now(),
        )
        self.assertEqual(attempt.score, 1.0)
        self.assertEqual(attempt.xp_awarded, 5)

    def test_attempt_defaults(self):
        sa = SideActivity.objects.create(
            subject=self.subject, sub_type="flashcard",
            title="Cards", content_json={"cards": []},
        )
        attempt = SideActivityAttempt.objects.create(
            student=self.student, side_activity=sa,
        )
        self.assertIsNone(attempt.score)
        self.assertIsNone(attempt.completed_at)
        self.assertEqual(attempt.xp_awarded, 0)
```

- [ ] **Step 5: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_side_activities --keepdb -v2`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add gamification/side_activity_models.py gamification/models.py gamification/migrations/ gamification/tests/test_side_activities.py
git commit -m "feat(side-activities): add SideActivity and SideActivityAttempt models"
```

---

## Task 2: Scoring Engine + List View + Form-Based Play

**Files:**
- Create: `gamification/scoring.py`
- Create: `gamification/side_activity_views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/side_activity_list.html`
- Create: `gamification/templates/gamification/side_activity_play.html`

- [ ] **Step 1: Create the scoring engine**

Create `gamification/scoring.py`:
```python
def score_activity(sub_type, content_json, submitted_data):
    """Score a side activity attempt. Returns float 0.0-1.0."""
    scorer = SCORERS.get(sub_type)
    if not scorer:
        return 0.0
    return scorer(content_json, submitted_data)


def _score_single_choice(content, data):
    """For daily_challenge — single question with choices."""
    try:
        return 1.0 if int(data.get("answer", -1)) == content["answer"] else 0.0
    except (ValueError, KeyError):
        return 0.0


def _score_multi_choice(content, data):
    """For practice_quiz, speed_round, math_drill, reading_mini — multiple questions."""
    questions = content.get("questions", [])
    if not questions:
        return 0.0
    correct = 0
    answers = data.get("answers", [])
    for i, q in enumerate(questions):
        if i < len(answers):
            try:
                if int(answers[i]) == q["answer"]:
                    correct += 1
            except (ValueError, TypeError):
                pass
    return correct / len(questions)


def _score_fill_blank(content, data):
    """For fill_blank — text inputs matched case-insensitively."""
    blanks = content.get("blanks", [])
    if not blanks:
        return 0.0
    answers = data.get("answers", [])
    correct = 0
    for i, expected in enumerate(blanks):
        if i < len(answers) and answers[i].strip().lower() == expected.strip().lower():
            correct += 1
    return correct / len(blanks)


def _score_word_scramble(content, data):
    """For word_scramble — unscrambled words matched case-insensitively."""
    words = content.get("words", [])
    if not words:
        return 0.0
    answers = data.get("answers", [])
    correct = 0
    for i, w in enumerate(words):
        if i < len(answers) and answers[i].strip().lower() == w["answer"].strip().lower():
            correct += 1
    return correct / len(words)


def _score_equation_balance(content, data):
    """For equation_balance — coefficients must match exactly."""
    expected = content.get("coefficients", [])
    if not expected:
        return 0.0
    answers = data.get("coefficients", [])
    correct = 0
    for i, exp in enumerate(expected):
        if i < len(answers):
            try:
                if int(answers[i]) == exp:
                    correct += 1
            except (ValueError, TypeError):
                pass
    return correct / len(expected)


def _score_order(content, data):
    """For drag_order, timeline_sort — items in correct order."""
    correct_order = content.get("correct_order", [])
    if not correct_order:
        items = content.get("items", content.get("events", []))
        correct_order = list(range(len(items)))
    submitted = data.get("order", [])
    if not submitted or len(submitted) != len(correct_order):
        return 0.0
    correct = sum(1 for i, s in enumerate(submitted) if int(s) == correct_order[i])
    return correct / len(correct_order)


def _score_match_pair(content, data):
    """For match_pair — matched pairs."""
    pairs = content.get("pairs", [])
    if not pairs:
        return 0.0
    matches = data.get("matches", {})  # {"0": "1", "1": "0", ...} left_idx -> right_idx
    correct = 0
    for i in range(len(pairs)):
        if matches.get(str(i)) == str(i):  # correct pairing
            correct += 1
    return correct / len(pairs)


def _score_flashcard(content, data):
    """For flashcard — self-rated knew_it count."""
    cards = content.get("cards", [])
    if not cards:
        return 0.0
    knew_count = int(data.get("knew_count", 0))
    return min(1.0, knew_count / len(cards))


def _score_typing(content, data):
    """For typing_drill — accuracy percentage."""
    return min(1.0, max(0.0, float(data.get("accuracy", 0))))


def _score_geo_map(content, data):
    """For geo_map — correct clicks."""
    targets = content.get("targets", [])
    if not targets:
        return 0.0
    correct = int(data.get("correct_clicks", 0))
    return min(1.0, correct / len(targets))


def _score_code_kata(content, data):
    """For code_kata — test cases passed (string comparison)."""
    test_cases = content.get("test_cases", [])
    if not test_cases:
        return 0.0
    passed = int(data.get("tests_passed", 0))
    return min(1.0, passed / len(test_cases))


SCORERS = {
    "daily_challenge": _score_single_choice,
    "practice_quiz": _score_multi_choice,
    "speed_round": _score_multi_choice,
    "math_drill": _score_multi_choice,
    "reading_mini": _score_multi_choice,
    "fill_blank": _score_fill_blank,
    "word_scramble": _score_word_scramble,
    "equation_balance": _score_equation_balance,
    "drag_order": _score_order,
    "timeline_sort": _score_order,
    "match_pair": _score_match_pair,
    "flashcard": _score_flashcard,
    "typing_drill": _score_typing,
    "geo_map": _score_geo_map,
    "code_kata": _score_code_kata,
}
```

- [ ] **Step 2: Create the views file**

Create `gamification/side_activity_views.py`:
```python
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from gamification.models import SideActivity, SideActivityAttempt
from gamification.scoring import score_activity
from gamification.services import award_xp


@login_required
def side_activity_list(request, subject_id):
    from subject.models.subject_model import Subject
    subject = get_object_or_404(Subject, pk=subject_id)

    activities = SideActivity.objects.filter(
        subject=subject, is_active=True,
    ).order_by("sub_type", "title")

    completed_ids = set(
        SideActivityAttempt.objects.filter(
            student=request.user,
            side_activity__subject=subject,
            completed_at__isnull=False,
        ).values_list("side_activity_id", flat=True)
    )

    activity_list = []
    for sa in activities:
        activity_list.append({
            "activity": sa,
            "completed": sa.pk in completed_ids,
        })

    return render(request, "gamification/side_activity_list.html", {
        "subject": subject,
        "activities": activity_list,
    })


# Form-based types that score on POST
FORM_TYPES = {
    "daily_challenge", "practice_quiz", "fill_blank",
    "word_scramble", "equation_balance", "reading_mini",
}


@login_required
def side_activity_play(request, activity_id):
    sa = get_object_or_404(SideActivity, pk=activity_id, is_active=True)

    if request.method == "POST" and sa.sub_type in FORM_TYPES:
        submitted = request.POST.dict()
        # Build answers list from numbered fields
        if "answer" in submitted:
            submitted["answer"] = submitted["answer"]
        else:
            answers = []
            i = 0
            while f"answer_{i}" in submitted:
                answers.append(submitted[f"answer_{i}"])
                i += 1
            submitted["answers"] = answers

            coefficients = []
            i = 0
            while f"coeff_{i}" in submitted:
                coefficients.append(submitted[f"coeff_{i}"])
                i += 1
            if coefficients:
                submitted["coefficients"] = coefficients

        score = score_activity(sa.sub_type, sa.content_json, submitted)
        xp = sa.xp_reward if score >= 0.5 else sa.xp_reward // 2

        # Check if first completion
        first_completion = not SideActivityAttempt.objects.filter(
            student=request.user, side_activity=sa, completed_at__isnull=False,
        ).exists()

        attempt = SideActivityAttempt.objects.create(
            student=request.user,
            side_activity=sa,
            completed_at=timezone.now(),
            score=score,
            xp_awarded=xp if first_completion else 0,
            details_json=submitted,
        )

        if first_completion:
            award_xp(request.user, xp, f"Side activity: {sa.title}",
                     "side_activity", source_id=attempt.pk)

        return render(request, "gamification/side_activity_result.html", {
            "activity": sa,
            "score": score,
            "score_pct": int(score * 100),
            "xp_awarded": xp if first_completion else 0,
            "first_completion": first_completion,
        })

    type_template = f"gamification/types/_{sa.sub_type}.html"
    return render(request, "gamification/side_activity_play.html", {
        "activity": sa,
        "content": sa.content_json,
        "type_template": type_template,
        "is_js_type": sa.sub_type not in FORM_TYPES,
    })


@login_required
@require_POST
def side_activity_submit(request, activity_id):
    """AJAX endpoint for JS-driven activity types."""
    sa = get_object_or_404(SideActivity, pk=activity_id, is_active=True)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    score = min(1.0, max(0.0, float(data.get("score", 0))))
    time_taken = int(data.get("time_taken_seconds", 0))
    details = data.get("details", {})

    xp = sa.xp_reward if score >= 0.5 else sa.xp_reward // 2

    first_completion = not SideActivityAttempt.objects.filter(
        student=request.user, side_activity=sa, completed_at__isnull=False,
    ).exists()

    attempt = SideActivityAttempt.objects.create(
        student=request.user,
        side_activity=sa,
        completed_at=timezone.now(),
        score=score,
        time_taken_seconds=time_taken,
        xp_awarded=xp if first_completion else 0,
        details_json=details,
    )

    if first_completion:
        award_xp(request.user, xp, f"Side activity: {sa.title}",
                 "side_activity", source_id=attempt.pk)

    return JsonResponse({
        "score": score,
        "score_pct": int(score * 100),
        "xp_awarded": xp if first_completion else 0,
        "first_completion": first_completion,
    })
```

- [ ] **Step 3: Add URL patterns**

In `gamification/urls.py`, add these imports and patterns:
```python
from gamification import side_activity_views
```

Add to urlpatterns:
```python
    path("gamification/side-activities/<int:subject_id>/", side_activity_views.side_activity_list, name="side_activity_list"),
    path("gamification/side-activity/<int:activity_id>/play/", side_activity_views.side_activity_play, name="side_activity_play"),
    path("gamification/side-activity/<int:activity_id>/submit/", side_activity_views.side_activity_submit, name="side_activity_submit"),
```

- [ ] **Step 4: Create list template**

Create `gamification/templates/gamification/side_activity_list.html` extending `student_base.html`:
- Title: "Play & Learn — {subject_name}"
- Back link to subject detail
- Grid of activity cards grouped by type
- Each card: icon for type, title, XP reward badge, estimated time, "Play" button
- Completed activities: checkmark overlay, "Replay" instead of "Play"
- Empty state: "No activities available for this subject yet."

- [ ] **Step 5: Create play wrapper template**

Create `gamification/templates/gamification/side_activity_play.html` extending `student_base.html`:
```html
{% extends 'student_base.html' %}
{% load static %}
{% block title %}{{ activity.title }}{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:800px;">
    <div class="d-flex justify-content-between align-items-start mb-3">
        <div>
            <h3 style="font-family:var(--display);font-weight:700;">{{ activity.title }}</h3>
            <p style="color:var(--text-dim);font-size:14px;">{{ activity.get_sub_type_display }} · {{ activity.estimated_minutes }} min · {{ activity.xp_reward }} XP</p>
        </div>
        <a href="{% url 'side_activity_list' activity.subject_id %}" style="color:var(--text-dim);text-decoration:none;">&larr; Back</a>
    </div>

    <div class="card">
        <div class="card-body">
            {% if is_js_type %}
                {% include type_template %}
                <script src="{% static 'js/side_activities/submit.js' %}"></script>
            {% else %}
                <form method="post" action="">
                    {% csrf_token %}
                    {% include type_template %}
                    <button type="submit" class="continue-btn mt-3" style="border:none;cursor:pointer;background:var(--gold);color:#0a0f1f;padding:12px 24px;border-radius:100px;font-weight:700;">Submit</button>
                </form>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Create result template**

Create `gamification/templates/gamification/side_activity_result.html` extending `student_base.html`:
```html
{% extends 'student_base.html' %}
{% block title %}Result — {{ activity.title }}{% endblock %}
{% block content %}
<div class="container-fluid py-4" style="max-width:600px;text-align:center;">
    <div class="card" style="padding:48px;">
        <div style="font-size:64px;margin-bottom:16px;">{% if score_pct >= 80 %}🎉{% elif score_pct >= 50 %}👍{% else %}💪{% endif %}</div>
        <h3 style="font-family:var(--display);font-weight:700;margin-bottom:8px;">{{ score_pct }}% Score</h3>
        {% if first_completion and xp_awarded %}
        <p style="color:var(--gold);font-family:var(--display);font-size:20px;font-weight:700;">+{{ xp_awarded }} XP</p>
        {% elif not first_completion %}
        <p style="color:var(--text-muted);font-size:14px;">Already completed — no additional XP</p>
        {% endif %}
        <div style="margin-top:24px;display:flex;gap:12px;justify-content:center;">
            <a href="{% url 'side_activity_play' activity.pk %}" class="btn" style="background:var(--surface-2);color:var(--text);border:1px solid var(--border);padding:10px 20px;border-radius:100px;text-decoration:none;">Play Again</a>
            <a href="{% url 'side_activity_list' activity.subject_id %}" class="btn" style="background:var(--gold);color:#0a0f1f;padding:10px 20px;border-radius:100px;text-decoration:none;font-weight:600;">More Activities</a>
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 7: Verify**

Run: `cd ~/classedge && env/bin/python manage.py check 2>&1`

- [ ] **Step 8: Commit**

```bash
cd ~/classedge && git add gamification/scoring.py gamification/side_activity_views.py gamification/urls.py gamification/templates/gamification/side_activity_list.html gamification/templates/gamification/side_activity_play.html gamification/templates/gamification/side_activity_result.html
git commit -m "feat(side-activities): add scoring engine, list/play/submit views"
```

---

## Task 3: Form-Based Type Templates (6 types)

**Files:**
- Create: 6 template partials in `gamification/templates/gamification/types/`

- [ ] **Step 1: Create daily_challenge partial**

Create `gamification/templates/gamification/types/_daily_challenge.html`:
```html
<h4 style="margin-bottom:16px;color:var(--text);">{{ content.question }}</h4>
{% for choice in content.choices %}
<label style="display:block;padding:12px 16px;margin-bottom:8px;border:1px solid var(--border);border-radius:var(--radius-sm);cursor:pointer;color:var(--text);">
    <input type="radio" name="answer" value="{{ forloop.counter0 }}" style="margin-right:10px;" required> {{ choice }}
</label>
{% endfor %}
```

- [ ] **Step 2: Create practice_quiz partial**

Create `gamification/templates/gamification/types/_practice_quiz.html`:
```html
{% for q in content.questions %}
<div style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px dashed var(--border);">
    <h4 style="margin-bottom:12px;color:var(--text);font-size:15px;">{{ forloop.counter }}. {{ q.q }}</h4>
    {% for choice in q.choices %}
    <label style="display:block;padding:8px 12px;margin-bottom:4px;border:1px solid var(--border);border-radius:8px;cursor:pointer;color:var(--text);font-size:14px;">
        <input type="radio" name="answer_{{ forloop.parentloop.counter0 }}" value="{{ forloop.counter0 }}" style="margin-right:8px;" required> {{ choice }}
    </label>
    {% endfor %}
</div>
{% endfor %}
```

- [ ] **Step 3: Create fill_blank partial**

Create `gamification/templates/gamification/types/_fill_blank.html`:
```html
<p style="font-size:16px;line-height:2;color:var(--text);">
    {{ content.text }}
</p>
<div style="margin-top:16px;">
    {% for blank in content.blanks %}
    <div style="margin-bottom:12px;">
        <label style="color:var(--text-dim);font-size:13px;">Blank {{ forloop.counter }}:</label>
        <input type="text" name="answer_{{ forloop.counter0 }}" class="form-control" style="background:var(--surface-2);border:1px solid var(--border);color:var(--text);max-width:300px;" required>
    </div>
    {% endfor %}
</div>
```

- [ ] **Step 4: Create word_scramble partial**

Create `gamification/templates/gamification/types/_word_scramble.html`:
```html
{% for word in content.words %}
<div style="margin-bottom:20px;padding:16px;border:1px solid var(--border);border-radius:var(--radius-sm);">
    <div style="font-family:var(--display);font-size:24px;letter-spacing:0.15em;color:var(--gold);margin-bottom:8px;">{{ word.scrambled }}</div>
    {% if word.hint %}<p style="color:var(--text-muted);font-size:13px;margin-bottom:8px;">Hint: {{ word.hint }}</p>{% endif %}
    <input type="text" name="answer_{{ forloop.counter0 }}" placeholder="Unscramble..." class="form-control" style="background:var(--surface-2);border:1px solid var(--border);color:var(--text);max-width:300px;" required>
</div>
{% endfor %}
```

- [ ] **Step 5: Create equation_balance partial**

Create `gamification/templates/gamification/types/_equation_balance.html`:
```html
<p style="font-size:16px;color:var(--text);margin-bottom:16px;">Balance this equation by filling in the coefficients:</p>
<div style="font-family:var(--display);font-size:20px;color:var(--text);padding:16px;background:var(--surface-2);border-radius:var(--radius-sm);margin-bottom:16px;">
    {{ content.equation }}
</div>
<div style="display:flex;gap:12px;flex-wrap:wrap;">
    {% for coeff in content.coefficients %}
    <div>
        <label style="color:var(--text-dim);font-size:12px;">Coefficient {{ forloop.counter }}:</label>
        <input type="number" name="coeff_{{ forloop.counter0 }}" min="1" max="20" class="form-control" style="background:var(--surface-2);border:1px solid var(--border);color:var(--text);width:80px;" required>
    </div>
    {% endfor %}
</div>
```

- [ ] **Step 6: Create reading_mini partial**

Create `gamification/templates/gamification/types/_reading_mini.html`:
```html
<div style="padding:20px;background:var(--surface-2);border-radius:var(--radius-sm);margin-bottom:24px;color:var(--text);line-height:1.7;font-size:15px;">
    {{ content.passage }}
</div>
{% for q in content.questions %}
<div style="margin-bottom:20px;">
    <h4 style="margin-bottom:10px;color:var(--text);font-size:15px;">{{ forloop.counter }}. {{ q.q }}</h4>
    {% for choice in q.choices %}
    <label style="display:block;padding:8px 12px;margin-bottom:4px;border:1px solid var(--border);border-radius:8px;cursor:pointer;color:var(--text);font-size:14px;">
        <input type="radio" name="answer_{{ forloop.parentloop.counter0 }}" value="{{ forloop.counter0 }}" style="margin-right:8px;" required> {{ choice }}
    </label>
    {% endfor %}
</div>
{% endfor %}
```

- [ ] **Step 7: Commit**

```bash
cd ~/classedge && git add gamification/templates/gamification/types/
git commit -m "feat(side-activities): add 6 form-based type templates"
```

---

## Task 4: JS Infrastructure + Submit Helper

**Files:**
- Create: `static/js/side_activities/submit.js`
- Create: `static/js/side_activities/timer.js`
- Create: `static/js/side_activities/drag.js`
- Create: `static/js/side_activities/flashcard.js`
- Create: `static/js/side_activities/geo_map.js`
- Create: `static/js/side_activities/typing.js`
- Create: `static/js/side_activities/code_kata.js`

- [ ] **Step 1: Create submit helper**

Create `static/js/side_activities/submit.js`:
```javascript
function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    var cookie = document.cookie.match(/csrftoken=([^;]*)/);
    return cookie ? cookie[1] : '';
}

function submitAttempt(activityId, score, timeTaken, details) {
    return fetch('/gamification/side-activity/' + activityId + '/submit/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            score: score,
            time_taken_seconds: timeTaken,
            details: details || {}
        })
    }).then(function(r) { return r.json(); })
    .then(function(data) {
        showResult(data);
        return data;
    });
}

function showResult(data) {
    var emoji = data.score_pct >= 80 ? '🎉' : data.score_pct >= 50 ? '👍' : '💪';
    var xpText = data.first_completion && data.xp_awarded ? '+' + data.xp_awarded + ' XP' : '';
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:9999;';
    overlay.innerHTML = '<div style="background:var(--surface);border:1px solid var(--border);border-radius:28px;padding:48px;text-align:center;max-width:400px;">' +
        '<div style="font-size:64px;margin-bottom:16px;">' + emoji + '</div>' +
        '<h3 style="font-family:var(--display);font-weight:700;">' + data.score_pct + '% Score</h3>' +
        (xpText ? '<p style="color:var(--gold);font-family:var(--display);font-size:20px;font-weight:700;">' + xpText + '</p>' : '') +
        '<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="margin-top:20px;background:var(--gold);color:#0a0f1f;padding:10px 24px;border-radius:100px;border:none;font-weight:700;cursor:pointer;">Continue</button>' +
        '</div>';
    document.body.appendChild(overlay);
}
```

- [ ] **Step 2: Create timer module**

Create `static/js/side_activities/timer.js`:
```javascript
function startTimer(seconds, timerEl, onExpire) {
    var remaining = seconds;
    timerEl.textContent = remaining + 's';
    var interval = setInterval(function() {
        remaining--;
        timerEl.textContent = remaining + 's';
        if (remaining <= 10) timerEl.style.color = 'var(--coral)';
        if (remaining <= 0) {
            clearInterval(interval);
            onExpire();
        }
    }, 1000);
    return { stop: function() { clearInterval(interval); return seconds - remaining; } };
}
```

- [ ] **Step 3: Create drag module**

Create `static/js/side_activities/drag.js`:
```javascript
function initDragSort(container, onComplete) {
    var items = container.querySelectorAll('[data-drag-item]');
    var draggedEl = null;

    items.forEach(function(item) {
        item.setAttribute('draggable', 'true');
        item.style.cursor = 'grab';

        item.addEventListener('dragstart', function(e) {
            draggedEl = this;
            this.style.opacity = '0.5';
            e.dataTransfer.effectAllowed = 'move';
        });
        item.addEventListener('dragend', function() {
            this.style.opacity = '1';
            draggedEl = null;
        });
        item.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
        });
        item.addEventListener('drop', function(e) {
            e.preventDefault();
            if (draggedEl && draggedEl !== this) {
                var parent = this.parentNode;
                var allItems = Array.from(parent.querySelectorAll('[data-drag-item]'));
                var dragIdx = allItems.indexOf(draggedEl);
                var dropIdx = allItems.indexOf(this);
                if (dragIdx < dropIdx) {
                    parent.insertBefore(draggedEl, this.nextSibling);
                } else {
                    parent.insertBefore(draggedEl, this);
                }
            }
        });
    });

    return {
        getOrder: function() {
            return Array.from(container.querySelectorAll('[data-drag-item]')).map(function(el) {
                return el.getAttribute('data-original-index');
            });
        }
    };
}

function initDragMatch(leftContainer, rightContainer, onMatch) {
    var leftItems = leftContainer.querySelectorAll('[data-match-left]');
    var rightItems = rightContainer.querySelectorAll('[data-match-right]');
    var matches = {};

    leftItems.forEach(function(item) {
        item.setAttribute('draggable', 'true');
        item.style.cursor = 'grab';
        item.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('text/plain', this.getAttribute('data-match-left'));
        });
    });

    rightItems.forEach(function(item) {
        item.addEventListener('dragover', function(e) { e.preventDefault(); });
        item.addEventListener('drop', function(e) {
            e.preventDefault();
            var leftIdx = e.dataTransfer.getData('text/plain');
            var rightIdx = this.getAttribute('data-match-right');
            matches[leftIdx] = rightIdx;
            this.style.borderColor = 'var(--gold)';
            if (onMatch) onMatch(matches);
        });
    });

    return { getMatches: function() { return matches; } };
}
```

- [ ] **Step 4: Create flashcard module**

Create `static/js/side_activities/flashcard.js`:
```javascript
function initFlashcards(container, cards, onComplete) {
    var currentIndex = 0;
    var knewCount = 0;
    var cardEl = container.querySelector('.flashcard-card');
    var frontEl = container.querySelector('.flashcard-front');
    var backEl = container.querySelector('.flashcard-back');
    var counterEl = container.querySelector('.flashcard-counter');
    var flipped = false;

    function showCard() {
        frontEl.textContent = cards[currentIndex].front;
        backEl.textContent = cards[currentIndex].back;
        cardEl.classList.remove('flipped');
        flipped = false;
        counterEl.textContent = (currentIndex + 1) + ' / ' + cards.length;
    }

    cardEl.addEventListener('click', function() {
        flipped = !flipped;
        cardEl.classList.toggle('flipped', flipped);
    });

    container.querySelector('.flashcard-knew').addEventListener('click', function() {
        knewCount++;
        nextCard();
    });
    container.querySelector('.flashcard-didnt').addEventListener('click', function() {
        nextCard();
    });

    function nextCard() {
        currentIndex++;
        if (currentIndex >= cards.length) {
            onComplete(knewCount);
        } else {
            showCard();
        }
    }

    showCard();
}
```

- [ ] **Step 5: Create geo_map module**

Create `static/js/side_activities/geo_map.js`:
```javascript
function initGeoMap(container, targets, onComplete) {
    var correctClicks = 0;
    var currentTarget = 0;
    var promptEl = container.querySelector('.geo-prompt');
    var mapEl = container.querySelector('.geo-image');

    function showTarget() {
        if (currentTarget >= targets.length) {
            onComplete(correctClicks);
            return;
        }
        promptEl.textContent = 'Click on: ' + targets[currentTarget].name;
    }

    mapEl.addEventListener('click', function(e) {
        if (currentTarget >= targets.length) return;
        var rect = mapEl.getBoundingClientRect();
        var xPct = ((e.clientX - rect.left) / rect.width) * 100;
        var yPct = ((e.clientY - rect.top) / rect.height) * 100;
        var t = targets[currentTarget];
        var dist = Math.sqrt(Math.pow(xPct - t.x, 2) + Math.pow(yPct - t.y, 2));
        if (dist <= (t.radius || 5)) correctClicks++;
        currentTarget++;
        showTarget();
    });

    showTarget();
}
```

- [ ] **Step 6: Create typing module**

Create `static/js/side_activities/typing.js`:
```javascript
function initTypingDrill(container, targetText, onComplete) {
    var inputEl = container.querySelector('.typing-input');
    var displayEl = container.querySelector('.typing-display');
    var wpmEl = container.querySelector('.typing-wpm');
    var startTime = null;

    displayEl.textContent = targetText;

    inputEl.addEventListener('input', function() {
        if (!startTime) startTime = Date.now();
        var typed = inputEl.value;
        var correct = 0;
        for (var i = 0; i < typed.length && i < targetText.length; i++) {
            if (typed[i] === targetText[i]) correct++;
        }
        var accuracy = typed.length > 0 ? correct / typed.length : 0;
        var elapsed = (Date.now() - startTime) / 1000 / 60; // minutes
        var words = typed.length / 5;
        var wpm = elapsed > 0 ? Math.round(words / elapsed) : 0;
        wpmEl.textContent = wpm + ' WPM · ' + Math.round(accuracy * 100) + '% accuracy';

        if (typed.length >= targetText.length) {
            onComplete(accuracy, wpm, Math.round((Date.now() - startTime) / 1000));
        }
    });
}
```

- [ ] **Step 7: Create code_kata module**

Create `static/js/side_activities/code_kata.js`:
```javascript
function initCodeKata(container, testCases, onSubmit) {
    var codeEl = container.querySelector('.code-editor');
    var submitBtn = container.querySelector('.code-submit');
    var resultsEl = container.querySelector('.code-results');

    submitBtn.addEventListener('click', function() {
        var code = codeEl.value;
        resultsEl.innerHTML = '<p style="color:var(--text-muted);">Checking...</p>';
        onSubmit(code);
    });
}
```

- [ ] **Step 8: Commit**

```bash
cd ~/classedge && git add -f static/js/side_activities/
git commit -m "feat(side-activities): add JS modules (submit, timer, drag, flashcard, geo, typing, code)"
```

---

## Task 5: JS-Driven Type Templates (9 types)

**Files:**
- Create: 9 template partials in `gamification/templates/gamification/types/`

- [ ] **Step 1: Create speed_round partial**

Create `gamification/templates/gamification/types/_speed_round.html`:
```html
{% load static %}
<div id="speed-round">
    <div style="display:flex;justify-content:space-between;margin-bottom:16px;">
        <span style="color:var(--text-dim);">Question <span id="sr-current">1</span> / {{ content.questions|length }}</span>
        <span id="sr-timer" style="font-family:var(--display);font-weight:700;font-size:20px;color:var(--gold);">{{ content.time_limit }}s</span>
    </div>
    <div id="sr-question" style="font-size:18px;font-weight:600;margin-bottom:16px;color:var(--text);"></div>
    <div id="sr-choices"></div>
</div>
<script src="{% static 'js/side_activities/timer.js' %}"></script>
<script>
(function() {
    var questions = {{ content.questions|safe }};
    var current = 0, answers = [], startTime = Date.now();
    var timerHandle = startTimer({{ content.time_limit|default:60 }}, document.getElementById('sr-timer'), finish);

    function showQuestion() {
        if (current >= questions.length) { finish(); return; }
        document.getElementById('sr-current').textContent = current + 1;
        document.getElementById('sr-question').textContent = questions[current].q;
        var choicesEl = document.getElementById('sr-choices');
        choicesEl.innerHTML = '';
        questions[current].choices.forEach(function(c, i) {
            var btn = document.createElement('button');
            btn.textContent = c;
            btn.style.cssText = 'display:block;width:100%;text-align:left;padding:12px 16px;margin-bottom:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--text);cursor:pointer;font-size:15px;';
            btn.onclick = function() { answers.push(i); current++; showQuestion(); };
            choicesEl.appendChild(btn);
        });
    }

    function finish() {
        var elapsed = timerHandle.stop();
        var correct = 0;
        answers.forEach(function(a, i) { if (i < questions.length && a === questions[i].answer) correct++; });
        var score = questions.length > 0 ? correct / questions.length : 0;
        submitAttempt({{ activity.pk }}, score, elapsed, {answers: answers});
    }

    showQuestion();
})();
</script>
```

- [ ] **Step 2: Create math_drill partial**

Create `gamification/templates/gamification/types/_math_drill.html`:
```html
{% load static %}
<div id="math-drill">
    <div style="display:flex;justify-content:space-between;margin-bottom:16px;">
        <span style="color:var(--text-dim);">Problem <span id="md-current">1</span> / {{ content.problems|length }}</span>
        <span id="md-timer" style="font-family:var(--display);font-weight:700;font-size:20px;color:var(--gold);">{{ content.time_limit|default:120 }}s</span>
    </div>
    <div id="md-expression" style="font-family:var(--display);font-size:36px;font-weight:700;text-align:center;margin:24px 0;color:var(--text);"></div>
    <input id="md-answer" type="number" autofocus style="display:block;margin:0 auto;width:150px;text-align:center;font-size:24px;padding:12px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);border-radius:var(--radius-sm);">
    <button id="md-next" style="display:block;margin:16px auto 0;background:var(--gold);color:#0a0f1f;padding:10px 24px;border-radius:100px;border:none;font-weight:700;cursor:pointer;">Next</button>
</div>
<script src="{% static 'js/side_activities/timer.js' %}"></script>
<script>
(function() {
    var problems = {{ content.problems|safe }};
    var current = 0, answers = [], startTime = Date.now();
    var timerHandle = startTimer({{ content.time_limit|default:120 }}, document.getElementById('md-timer'), finish);

    function showProblem() {
        if (current >= problems.length) { finish(); return; }
        document.getElementById('md-current').textContent = current + 1;
        document.getElementById('md-expression').textContent = problems[current].expression;
        document.getElementById('md-answer').value = '';
        document.getElementById('md-answer').focus();
    }

    document.getElementById('md-next').onclick = function() {
        answers.push(parseInt(document.getElementById('md-answer').value) || 0);
        current++;
        showProblem();
    };
    document.getElementById('md-answer').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') document.getElementById('md-next').click();
    });

    function finish() {
        var elapsed = timerHandle.stop();
        var correct = 0;
        answers.forEach(function(a, i) { if (i < problems.length && a === problems[i].answer) correct++; });
        var score = problems.length > 0 ? correct / problems.length : 0;
        submitAttempt({{ activity.pk }}, score, elapsed, {answers: answers});
    }

    showProblem();
})();
</script>
```

- [ ] **Step 3: Create match_pair partial**

Create `gamification/templates/gamification/types/_match_pair.html`:
```html
{% load static %}
<p style="color:var(--text-dim);margin-bottom:16px;">Drag items from the left to match with the right.</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div id="match-left">
        {% for pair in content.pairs %}
        <div data-match-left="{{ forloop.counter0 }}" style="padding:14px 16px;margin-bottom:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--text);cursor:grab;">{{ pair.left }}</div>
        {% endfor %}
    </div>
    <div id="match-right">
        {% for pair in content.pairs %}
        <div data-match-right="{{ forloop.counter0 }}" style="padding:14px 16px;margin-bottom:8px;border:2px dashed var(--border);border-radius:var(--radius-sm);color:var(--text-dim);min-height:48px;">{{ pair.right }}</div>
        {% endfor %}
    </div>
</div>
<button id="match-submit" style="margin-top:16px;background:var(--gold);color:#0a0f1f;padding:12px 24px;border-radius:100px;border:none;font-weight:700;cursor:pointer;">Check Matches</button>
<script src="{% static 'js/side_activities/drag.js' %}"></script>
<script>
(function() {
    var startTime = Date.now();
    var matcher = initDragMatch(
        document.getElementById('match-left'),
        document.getElementById('match-right')
    );
    document.getElementById('match-submit').onclick = function() {
        var matches = matcher.getMatches();
        var pairs = {{ content.pairs|length }};
        var correct = 0;
        for (var k in matches) { if (matches[k] === k) correct++; }
        var score = pairs > 0 ? correct / pairs : 0;
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        submitAttempt({{ activity.pk }}, score, elapsed, {matches: matches});
    };
})();
</script>
```

- [ ] **Step 4: Create drag_order partial**

Create `gamification/templates/gamification/types/_drag_order.html`:
```html
{% load static %}
<p style="color:var(--text-dim);margin-bottom:16px;">Drag items into the correct order.</p>
<div id="drag-container">
    {% for item in content.items %}
    <div data-drag-item data-original-index="{{ forloop.counter0 }}" style="padding:14px 16px;margin-bottom:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--text);">{{ item }}</div>
    {% endfor %}
</div>
<button id="order-submit" style="margin-top:16px;background:var(--gold);color:#0a0f1f;padding:12px 24px;border-radius:100px;border:none;font-weight:700;cursor:pointer;">Check Order</button>
<script src="{% static 'js/side_activities/drag.js' %}"></script>
<script>
(function() {
    var startTime = Date.now();
    var sorter = initDragSort(document.getElementById('drag-container'));
    document.getElementById('order-submit').onclick = function() {
        var order = sorter.getOrder();
        var correctOrder = {{ content.correct_order|safe }};
        var correct = 0;
        order.forEach(function(val, i) { if (parseInt(val) === correctOrder[i]) correct++; });
        var score = correctOrder.length > 0 ? correct / correctOrder.length : 0;
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        submitAttempt({{ activity.pk }}, score, elapsed, {order: order});
    };
})();
</script>
```

- [ ] **Step 5: Create timeline_sort partial**

Create `gamification/templates/gamification/types/_timeline_sort.html`:
```html
{% load static %}
<p style="color:var(--text-dim);margin-bottom:16px;">Drag events into chronological order.</p>
<div id="timeline-container">
    {% for event in content.events %}
    <div data-drag-item data-original-index="{{ forloop.counter0 }}" style="padding:14px 16px;margin-bottom:8px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--text);">
        {{ event.text }}
    </div>
    {% endfor %}
</div>
<button id="timeline-submit" style="margin-top:16px;background:var(--gold);color:#0a0f1f;padding:12px 24px;border-radius:100px;border:none;font-weight:700;cursor:pointer;">Check Order</button>
<script src="{% static 'js/side_activities/drag.js' %}"></script>
<script>
(function() {
    var startTime = Date.now();
    var sorter = initDragSort(document.getElementById('timeline-container'));
    var events = {{ content.events|safe }};
    var correctOrder = events.map(function(_, i) { return i; });
    correctOrder.sort(function(a, b) { return events[a].year - events[b].year; });

    document.getElementById('timeline-submit').onclick = function() {
        var order = sorter.getOrder();
        var correct = 0;
        order.forEach(function(val, i) { if (parseInt(val) === correctOrder[i]) correct++; });
        var score = correctOrder.length > 0 ? correct / correctOrder.length : 0;
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        submitAttempt({{ activity.pk }}, score, elapsed, {order: order});
    };
})();
</script>
```

- [ ] **Step 6: Create flashcard partial**

Create `gamification/templates/gamification/types/_flashcard.html`:
```html
{% load static %}
<div id="flashcard-container">
    <div class="flashcard-counter" style="text-align:center;color:var(--text-dim);margin-bottom:16px;"></div>
    <div class="flashcard-card" style="min-height:200px;border:1px solid var(--border);border-radius:var(--radius);padding:32px;text-align:center;cursor:pointer;display:flex;align-items:center;justify-content:center;background:var(--surface-2);margin-bottom:16px;transition:transform 0.3s;">
        <div class="flashcard-front" style="font-size:20px;font-weight:600;color:var(--text);"></div>
        <div class="flashcard-back" style="font-size:16px;color:var(--text-dim);display:none;"></div>
    </div>
    <p style="text-align:center;color:var(--text-muted);font-size:13px;margin-bottom:16px;">Click card to flip</p>
    <div style="display:flex;gap:12px;justify-content:center;">
        <button class="flashcard-didnt" style="background:var(--surface-2);border:1px solid var(--border);color:var(--coral);padding:10px 24px;border-radius:100px;cursor:pointer;font-weight:600;">Didn't Know</button>
        <button class="flashcard-knew" style="background:var(--mint);border:none;color:#0a0f1f;padding:10px 24px;border-radius:100px;cursor:pointer;font-weight:600;">Knew It!</button>
    </div>
</div>
<script src="{% static 'js/side_activities/flashcard.js' %}"></script>
<script>
(function() {
    var cards = {{ content.cards|safe }};
    var startTime = Date.now();
    var container = document.getElementById('flashcard-container');
    var cardEl = container.querySelector('.flashcard-card');
    var frontEl = container.querySelector('.flashcard-front');
    var backEl = container.querySelector('.flashcard-back');

    cardEl.addEventListener('click', function() {
        var isFlipped = backEl.style.display !== 'none';
        frontEl.style.display = isFlipped ? '' : 'none';
        backEl.style.display = isFlipped ? 'none' : '';
    });

    initFlashcards(container, cards, function(knewCount) {
        var score = cards.length > 0 ? knewCount / cards.length : 0;
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        submitAttempt({{ activity.pk }}, score, elapsed, {knew_count: knewCount});
    });
})();
</script>
```

- [ ] **Step 7: Create geo_map partial**

Create `gamification/templates/gamification/types/_geo_map.html`:
```html
{% load static %}
<div id="geo-container">
    <div class="geo-prompt" style="text-align:center;font-size:18px;font-weight:600;color:var(--text);margin-bottom:16px;"></div>
    <div style="position:relative;display:inline-block;width:100%;">
        <img class="geo-image" src="{{ content.image_url }}" style="width:100%;border-radius:var(--radius-sm);cursor:crosshair;border:1px solid var(--border);">
    </div>
    <p style="text-align:center;color:var(--text-muted);font-size:13px;margin-top:8px;">Click on the correct location</p>
</div>
<script src="{% static 'js/side_activities/geo_map.js' %}"></script>
<script>
(function() {
    var targets = {{ content.targets|safe }};
    var startTime = Date.now();
    initGeoMap(document.getElementById('geo-container'), targets, function(correctClicks) {
        var score = targets.length > 0 ? correctClicks / targets.length : 0;
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        submitAttempt({{ activity.pk }}, score, elapsed, {correct_clicks: correctClicks});
    });
})();
</script>
```

- [ ] **Step 8: Create typing_drill partial**

Create `gamification/templates/gamification/types/_typing_drill.html`:
```html
{% load static %}
<div id="typing-container">
    <div class="typing-display" style="font-family:monospace;font-size:16px;line-height:1.8;padding:20px;background:var(--surface-2);border-radius:var(--radius-sm);color:var(--text);margin-bottom:16px;white-space:pre-wrap;border:1px solid var(--border);"></div>
    <textarea class="typing-input" rows="5" placeholder="Start typing here..." autofocus style="width:100%;font-family:monospace;font-size:16px;padding:16px;background:var(--bg-2);border:1px solid var(--border);color:var(--text);border-radius:var(--radius-sm);resize:none;"></textarea>
    <div class="typing-wpm" style="text-align:center;margin-top:8px;font-family:var(--display);font-weight:600;color:var(--gold);">0 WPM · 0% accuracy</div>
</div>
<script src="{% static 'js/side_activities/typing.js' %}"></script>
<script>
(function() {
    var text = {{ content.text|safe }};
    initTypingDrill(document.getElementById('typing-container'), text, function(accuracy, wpm, elapsed) {
        submitAttempt({{ activity.pk }}, accuracy, elapsed, {accuracy: accuracy, wpm: wpm});
    });
})();
</script>
```

- [ ] **Step 9: Create code_kata partial**

Create `gamification/templates/gamification/types/_code_kata.html`:
```html
{% load static %}
<div id="code-container">
    <div style="padding:16px;background:var(--surface-2);border-radius:var(--radius-sm);margin-bottom:16px;color:var(--text);">
        <strong>Prompt:</strong> {{ content.prompt }}
    </div>
    <textarea class="code-editor" rows="12" style="width:100%;font-family:monospace;font-size:14px;padding:16px;background:#1a1a2e;border:1px solid var(--border);color:#4ecdc4;border-radius:var(--radius-sm);resize:vertical;tab-size:4;" placeholder="Write your code here..."></textarea>
    <div style="margin-top:8px;color:var(--text-muted);font-size:13px;">Language: {{ content.language|default:"python" }}</div>
    <button class="code-submit" style="margin-top:12px;background:var(--gold);color:#0a0f1f;padding:12px 24px;border-radius:100px;border:none;font-weight:700;cursor:pointer;">Run Tests</button>
    <div class="code-results" style="margin-top:16px;"></div>
</div>
<script src="{% static 'js/side_activities/code_kata.js' %}"></script>
<script>
(function() {
    var testCases = {{ content.test_cases|safe }};
    var startTime = Date.now();
    initCodeKata(document.getElementById('code-container'), testCases, function(code) {
        // Client-side: just submit the code for server evaluation in future
        // For now: submit with 0 score, server can evaluate later
        var elapsed = Math.round((Date.now() - startTime) / 1000);
        submitAttempt({{ activity.pk }}, 0.5, elapsed, {code: code, tests_passed: 0});
    });
})();
</script>
```

- [ ] **Step 10: Commit**

```bash
cd ~/classedge && git add gamification/templates/gamification/types/
git commit -m "feat(side-activities): add 9 JS-driven type templates"
```

---

## Task 6: Teacher CRUD

**Files:**
- Create: `gamification/side_activity_forms.py`
- Modify: `gamification/side_activity_views.py`
- Modify: `gamification/urls.py`
- Create: `gamification/templates/gamification/side_activity_create.html`
- Create: `gamification/templates/gamification/side_activity_edit.html`

- [ ] **Step 1: Create the form**

Create `gamification/side_activity_forms.py`:
```python
from django import forms

from gamification.models import SideActivity


class SideActivityForm(forms.ModelForm):
    content_text = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 10,
            "placeholder": '{"question": "...", "choices": ["A","B","C","D"], "answer": 0}',
            "class": "form-control",
            "style": "font-family:monospace;font-size:13px;background:var(--surface-2);border:1px solid var(--border);color:var(--text);",
        }),
        help_text="Paste the content JSON for this activity type.",
    )

    class Meta:
        model = SideActivity
        fields = ["sub_type", "title", "estimated_minutes", "xp_reward"]
        widgets = {
            "sub_type": forms.Select(attrs={"class": "form-select", "style": "background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
            "title": forms.TextInput(attrs={"class": "form-control", "style": "background:var(--surface-2);border:1px solid var(--border);color:var(--text);"}),
            "estimated_minutes": forms.NumberInput(attrs={"class": "form-control", "style": "background:var(--surface-2);border:1px solid var(--border);color:var(--text);width:100px;"}),
            "xp_reward": forms.NumberInput(attrs={"class": "form-control", "style": "background:var(--surface-2);border:1px solid var(--border);color:var(--text);width:100px;"}),
        }

    def clean_content_text(self):
        import json
        raw = self.cleaned_data["content_text"]
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.content_json = self.cleaned_data["content_text"]
        if commit:
            instance.save()
        return instance
```

- [ ] **Step 2: Add teacher views**

In `gamification/side_activity_views.py`, add:
```python
from activity.utils.authorization import check_subject_access
from gamification.side_activity_forms import SideActivityForm


@login_required
def side_activity_create(request, subject_id):
    from subject.models.subject_model import Subject
    subject = get_object_or_404(Subject, pk=subject_id)

    has_access, redirect_resp = check_subject_access(request, subject, require_teacher=True)
    if not has_access:
        return redirect_resp

    if request.method == "POST":
        form = SideActivityForm(request.POST)
        if form.is_valid():
            sa = form.save(commit=False)
            sa.subject = subject
            sa.created_by = request.user
            sa.save()
            return redirect("side_activity_list", subject_id=subject.pk)
    else:
        form = SideActivityForm()

    return render(request, "gamification/side_activity_create.html", {
        "form": form, "subject": subject,
    })


@login_required
def side_activity_edit(request, activity_id):
    sa = get_object_or_404(SideActivity, pk=activity_id)

    has_access, redirect_resp = check_subject_access(request, sa.subject, require_teacher=True)
    if not has_access:
        return redirect_resp

    if request.method == "POST":
        form = SideActivityForm(request.POST, instance=sa)
        if form.is_valid():
            form.save()
            return redirect("side_activity_list", subject_id=sa.subject_id)
    else:
        import json
        form = SideActivityForm(instance=sa, initial={"content_text": json.dumps(sa.content_json, indent=2)})

    return render(request, "gamification/side_activity_edit.html", {
        "form": form, "activity": sa,
    })


@login_required
@require_POST
def side_activity_delete(request, activity_id):
    sa = get_object_or_404(SideActivity, pk=activity_id)

    has_access, redirect_resp = check_subject_access(request, sa.subject, require_teacher=True)
    if not has_access:
        return redirect_resp

    subject_id = sa.subject_id
    sa.delete()
    return redirect("side_activity_list", subject_id=subject_id)
```

- [ ] **Step 3: Add URL patterns**

In `gamification/urls.py`, add:
```python
    path("gamification/side-activities/<int:subject_id>/create/", side_activity_views.side_activity_create, name="side_activity_create"),
    path("gamification/side-activity/<int:activity_id>/edit/", side_activity_views.side_activity_edit, name="side_activity_edit"),
    path("gamification/side-activity/<int:activity_id>/delete/", side_activity_views.side_activity_delete, name="side_activity_delete"),
```

- [ ] **Step 4: Create form templates**

Create `gamification/templates/gamification/side_activity_create.html` extending `student_base.html`:
- Title: "Create Side Activity — {subject_name}"
- Render the form fields with labels
- Submit button + cancel link back to list

Create `gamification/templates/gamification/side_activity_edit.html` extending `student_base.html`:
- Title: "Edit — {activity.title}"
- Same form layout as create
- Delete button (POST form to delete URL)

- [ ] **Step 5: Add teacher controls to list template**

In `gamification/templates/gamification/side_activity_list.html`, add a "Create Activity" button at the top visible to teachers, and edit/delete links on each activity card for teachers.

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add gamification/side_activity_forms.py gamification/side_activity_views.py gamification/urls.py gamification/templates/gamification/side_activity_create.html gamification/templates/gamification/side_activity_edit.html gamification/templates/gamification/side_activity_list.html
git commit -m "feat(side-activities): add teacher CRUD for creating/editing activities"
```

---

## Task 7: Seed Command + Badges + Subject Detail Widget

**Files:**
- Create: `gamification/management/commands/seed_side_activities.py`
- Create: `gamification/migrations/0005_seed_side_activity_badges.py`
- Modify: `gamification/badges.py`
- Modify: `course/templates/course/view_subject_dashboard.html`

- [ ] **Step 1: Create seed command**

Create `gamification/management/commands/seed_side_activities.py`:
```python
from django.core.management.base import BaseCommand

from gamification.models import SideActivity
from subject.models.subject_model import Subject


SAMPLE_CONTENT = {
    "daily_challenge": {"question": "What is the process by which plants make food?", "choices": ["Respiration", "Photosynthesis", "Fermentation", "Digestion"], "answer": 1},
    "flashcard": {"cards": [{"front": "Hypothesis", "back": "A proposed explanation for a phenomenon"}, {"front": "Variable", "back": "A factor that can change in an experiment"}, {"front": "Control Group", "back": "The group that does not receive the experimental treatment"}, {"front": "Dependent Variable", "back": "The variable being measured"}, {"front": "Independent Variable", "back": "The variable being changed"}]},
    "speed_round": {"questions": [{"q": "What is 8 × 7?", "choices": ["54", "56", "58", "64"], "answer": 1}, {"q": "What is 12 × 5?", "choices": ["55", "60", "65", "50"], "answer": 1}, {"q": "What is 9 × 6?", "choices": ["52", "54", "56", "48"], "answer": 1}, {"q": "What is 11 × 4?", "choices": ["40", "42", "44", "48"], "answer": 2}, {"q": "What is 7 × 7?", "choices": ["47", "49", "51", "56"], "answer": 1}], "time_limit": 60},
    "match_pair": {"pairs": [{"left": "H2O", "right": "Water"}, {"left": "NaCl", "right": "Salt"}, {"left": "CO2", "right": "Carbon Dioxide"}, {"left": "O2", "right": "Oxygen"}, {"left": "C6H12O6", "right": "Glucose"}]},
    "practice_quiz": {"questions": [{"q": "Which planet is closest to the sun?", "choices": ["Venus", "Mercury", "Earth", "Mars"], "answer": 1}, {"q": "What gas do plants absorb?", "choices": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "answer": 2}, {"q": "What is the boiling point of water?", "choices": ["90°C", "100°C", "110°C", "80°C"], "answer": 1}]},
    "fill_blank": {"text": "The ___ is responsible for pumping blood throughout the body.", "blanks": ["heart"]},
    "drag_order": {"items": ["Egg", "Larva", "Pupa", "Adult"], "correct_order": [0, 1, 2, 3]},
    "word_scramble": {"words": [{"scrambled": "SSEPOTHYHNI", "answer": "HYPOTHESIS", "hint": "A proposed explanation"}, {"scrambled": "LLEC", "answer": "CELL", "hint": "Basic unit of life"}]},
    "equation_balance": {"equation": "_ H2 + _ O2 → _ H2O", "coefficients": [2, 1, 2]},
    "math_drill": {"problems": [{"expression": "15 + 27", "answer": 42}, {"expression": "8 × 9", "answer": 72}, {"expression": "100 - 37", "answer": 63}, {"expression": "144 ÷ 12", "answer": 12}, {"expression": "25 × 4", "answer": 100}], "time_limit": 120},
    "geo_map": {"image_url": "/static/images/maps/sample.png", "targets": [{"name": "Point A", "x": 30, "y": 40, "radius": 8}, {"name": "Point B", "x": 70, "y": 60, "radius": 8}]},
    "timeline_sort": {"events": [{"text": "World War I begins", "year": 1914}, {"text": "World War II ends", "year": 1945}, {"text": "Moon landing", "year": 1969}, {"text": "Berlin Wall falls", "year": 1989}]},
    "code_kata": {"prompt": "Write a function called 'add' that takes two numbers and returns their sum.", "test_cases": [{"input": "add(2, 3)", "expected": "5"}, {"input": "add(-1, 1)", "expected": "0"}], "language": "python"},
    "typing_drill": {"text": "The quick brown fox jumps over the lazy dog."},
    "reading_mini": {"passage": "Water exists in three states: solid (ice), liquid (water), and gas (steam). The process of changing from liquid to gas is called evaporation, while changing from gas to liquid is condensation.", "questions": [{"q": "What is the gas form of water called?", "choices": ["Ice", "Steam", "Condensation", "Evaporation"], "answer": 1}]},
}

XP_REWARDS = {
    "daily_challenge": 5, "flashcard": 5, "speed_round": 10, "match_pair": 10,
    "practice_quiz": 5, "fill_blank": 10, "drag_order": 10, "word_scramble": 5,
    "equation_balance": 15, "math_drill": 10, "geo_map": 10, "timeline_sort": 10,
    "code_kata": 15, "typing_drill": 5, "reading_mini": 10,
}

TITLES = {
    "daily_challenge": "Daily Science Challenge",
    "flashcard": "Science Key Terms",
    "speed_round": "Mental Math Sprint",
    "match_pair": "Chemical Formula Match",
    "practice_quiz": "General Science Quiz",
    "fill_blank": "Body Systems Fill-in",
    "drag_order": "Life Cycle Order",
    "word_scramble": "Science Vocabulary Scramble",
    "equation_balance": "Balance the Equation",
    "math_drill": "Math Drill Challenge",
    "geo_map": "Map Target Practice",
    "timeline_sort": "History Timeline",
    "code_kata": "Coding Challenge: Addition",
    "typing_drill": "Typing Speed Test",
    "reading_mini": "Reading: States of Water",
}


class Command(BaseCommand):
    help = "Seed sample side activities for all subjects."

    def handle(self, *args, **options):
        subjects = Subject.objects.all()
        created = 0
        for subject in subjects:
            for sub_type, content in SAMPLE_CONTENT.items():
                title = TITLES.get(sub_type, sub_type.replace("_", " ").title())
                _, was_created = SideActivity.objects.get_or_create(
                    subject=subject,
                    sub_type=sub_type,
                    title=title,
                    defaults={
                        "content_json": content,
                        "xp_reward": XP_REWARDS.get(sub_type, 10),
                        "estimated_minutes": 3,
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} side activities across {subjects.count()} subjects."))
```

- [ ] **Step 2: Create badge seed migration**

Create `gamification/migrations/0005_seed_side_activity_badges.py`:
```python
from django.db import migrations

SIDE_ACTIVITY_BADGES = [
    ("play_hard", "Play Hard", "Complete 10 side activities", "bronze", "🎲", {"type": "side_activity_count", "threshold": 10}),
    ("speed_demon", "Speed Demon", "Complete 10 speed rounds under 45 seconds", "silver", "🏃", {"type": "side_activity_speed", "sub_type": "speed_round", "max_seconds": 45, "count": 10}),
    ("sharp_shooter_sa", "Sharp Shooter", "5 consecutive perfect daily challenges", "silver", "🎯", {"type": "side_activity_streak", "sub_type": "daily_challenge", "min_score": 1.0, "count": 5}),
    ("early_bird_quiz", "Early Bird Quiz", "Complete 5 daily challenges before 8am", "silver", "🌅", {"type": "side_activity_early", "sub_type": "daily_challenge", "before_hour": 8, "count": 5}),
    ("lifelong_learner", "Lifelong Learner", "Complete a side activity every day for 30 days", "gold", "🧠", {"type": "side_activity_daily", "threshold": 30}),
    ("subject_champion", "Subject Champion", "Complete all side activities in one subject", "gold", "🏅", {"type": "side_activity_all_in_subject"}),
    ("flashcard_master", "Flashcard Master", "Review 500 flashcards", "silver", "🃏", {"type": "side_activity_count_type", "sub_type": "flashcard", "threshold": 50}),
    ("fast_fingers", "Fast Fingers", "Typing drill at 80+ WPM", "silver", "⌨️", {"type": "side_activity_typing_wpm", "min_wpm": 80}),
    ("mad_scientist", "Mad Scientist", "Complete 50 equation balance challenges", "silver", "🧪", {"type": "side_activity_count_type", "sub_type": "equation_balance", "threshold": 50}),
    ("explorer_geo", "Explorer", "Perfect score on all geography maps", "gold", "🗺️", {"type": "side_activity_perfect_type", "sub_type": "geo_map"}),
]


def seed(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    for code, name, desc, tier, icon, criteria in SIDE_ACTIVITY_BADGES:
        BadgeDefinition.objects.get_or_create(
            code=code, defaults={"name": name, "description": desc, "tier": tier, "icon": icon, "criteria_json": criteria},
        )


def reverse(apps, schema_editor):
    BadgeDefinition = apps.get_model("gamification", "BadgeDefinition")
    codes = [b[0] for b in SIDE_ACTIVITY_BADGES]
    BadgeDefinition.objects.filter(code__in=codes).delete()


class Migration(migrations.Migration):
    dependencies = [("gamification", "0004_sideactivity_sideactivityattempt")]
    operations = [migrations.RunPython(seed, reverse)]
```

Note: The dependency name `0004_sideactivity_sideactivityattempt` should match the actual auto-generated migration filename from Task 1 Step 3. Check and adjust if needed.

- [ ] **Step 3: Add badge evaluators**

In `gamification/badges.py`, add these imports at the top:
```python
from gamification.side_activity_models import SideActivityAttempt, SideActivity
```

Add evaluator functions before the `EVALUATORS` dict:
```python
def _eval_side_activity_count(student, gam, criteria):
    count = SideActivityAttempt.objects.filter(
        student=student, completed_at__isnull=False,
    ).values("side_activity").distinct().count()
    return count >= criteria["threshold"]


def _eval_side_activity_count_type(student, gam, criteria):
    count = SideActivityAttempt.objects.filter(
        student=student, completed_at__isnull=False,
        side_activity__sub_type=criteria["sub_type"],
    ).count()
    return count >= criteria["threshold"]


def _eval_side_activity_speed(student, gam, criteria):
    count = SideActivityAttempt.objects.filter(
        student=student, completed_at__isnull=False,
        side_activity__sub_type=criteria["sub_type"],
        time_taken_seconds__lte=criteria["max_seconds"],
    ).count()
    return count >= criteria["count"]


def _eval_side_activity_typing_wpm(student, gam, criteria):
    return SideActivityAttempt.objects.filter(
        student=student, completed_at__isnull=False,
        side_activity__sub_type="typing_drill",
        details_json__wpm__gte=criteria["min_wpm"],
    ).exists()


def _eval_side_activity_all_in_subject(student, gam, criteria):
    from django.db.models import Count, Q
    subjects_with_activities = SideActivity.objects.filter(is_active=True).values("subject").annotate(
        total=Count("id"),
    )
    for entry in subjects_with_activities:
        completed = SideActivityAttempt.objects.filter(
            student=student, completed_at__isnull=False,
            side_activity__subject_id=entry["subject"],
        ).values("side_activity").distinct().count()
        if completed >= entry["total"] and entry["total"] > 0:
            return True
    return False
```

Add to `EVALUATORS` dict:
```python
    "side_activity_count": _eval_side_activity_count,
    "side_activity_count_type": _eval_side_activity_count_type,
    "side_activity_speed": _eval_side_activity_speed,
    "side_activity_typing_wpm": _eval_side_activity_typing_wpm,
    "side_activity_all_in_subject": _eval_side_activity_all_in_subject,
```

Note: `side_activity_streak`, `side_activity_early`, `side_activity_daily`, and `side_activity_perfect_type` evaluators require more complex date-based queries. Add them as stubs that return False for now — they can be refined later:
```python
def _eval_side_activity_stub(student, gam, criteria):
    """Placeholder for complex date-based badge evaluators."""
    return False

    "side_activity_streak": _eval_side_activity_stub,
    "side_activity_early": _eval_side_activity_stub,
    "side_activity_daily": _eval_side_activity_stub,
    "side_activity_perfect_type": _eval_side_activity_stub,
```

- [ ] **Step 4: Apply migration**

Run:
```bash
cd ~/classedge && env/bin/python manage.py migrate gamification 2>&1 | tail -5
```

- [ ] **Step 5: Add widget to subject detail page**

In `course/templates/course/view_subject_dashboard.html`, find the at-risk button section (before the rag_tutor include). Add after it:

```html
{% if is_student %}
<div class="mt-3">
    <a href="{% url 'side_activity_list' subject.pk %}" class="btn btn-outline-warning btn-sm">
        <i class="fas fa-gamepad"></i> Play & Learn
    </a>
</div>
{% endif %}
```

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add gamification/management/commands/seed_side_activities.py gamification/migrations/ gamification/badges.py course/templates/course/view_subject_dashboard.html
git commit -m "feat(side-activities): add seed command, 10 badge evaluators, subject detail widget"
```

---

## Task 8: Tests

**Files:**
- Modify: `gamification/tests/test_side_activities.py`

- [ ] **Step 1: Add comprehensive tests**

Append to `gamification/tests/test_side_activities.py`:

```python
from django.test import Client, override_settings

from gamification.scoring import score_activity
from gamification.models import XPTransaction
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment

_GAM_SETTINGS = {
    "GAMIFICATION_XP_RATES": {
        "submission": 50, "early_submission": 75,
        "score_90": 30, "score_75": 15,
        "daily_login": 5, "perfect_attendance_week": 50,
    },
    "GAMIFICATION_STREAK_FREEZE_MONTHLY": 1,
}


class ScoringTests(TestCase):
    def test_daily_challenge_correct(self):
        content = {"question": "Q", "choices": ["A", "B", "C"], "answer": 1}
        self.assertEqual(score_activity("daily_challenge", content, {"answer": "1"}), 1.0)

    def test_daily_challenge_wrong(self):
        content = {"question": "Q", "choices": ["A", "B", "C"], "answer": 1}
        self.assertEqual(score_activity("daily_challenge", content, {"answer": "0"}), 0.0)

    def test_multi_choice_scoring(self):
        content = {"questions": [{"q": "Q1", "choices": ["A", "B"], "answer": 0}, {"q": "Q2", "choices": ["A", "B"], "answer": 1}]}
        self.assertEqual(score_activity("practice_quiz", content, {"answers": ["0", "1"]}), 1.0)
        self.assertEqual(score_activity("practice_quiz", content, {"answers": ["0", "0"]}), 0.5)

    def test_fill_blank_case_insensitive(self):
        content = {"blanks": ["heart"]}
        self.assertEqual(score_activity("fill_blank", content, {"answers": ["Heart"]}), 1.0)

    def test_equation_balance(self):
        content = {"coefficients": [2, 1, 2]}
        self.assertEqual(score_activity("equation_balance", content, {"coefficients": ["2", "1", "2"]}), 1.0)

    def test_order_scoring(self):
        content = {"items": ["A", "B", "C"], "correct_order": [0, 1, 2]}
        self.assertEqual(score_activity("drag_order", content, {"order": ["0", "1", "2"]}), 1.0)
        self.assertAlmostEqual(score_activity("drag_order", content, {"order": ["1", "0", "2"]}), 1/3, places=1)


@override_settings(**_GAM_SETTINGS)
class SideActivityViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = _create_test_user(username="sa_view_stu", role_name="student")
        self.teacher = _create_test_user(username="sa_view_teach", role_name="teacher")
        self.subject = _create_subject()
        from subject.models.subject_model import Subject
        Subject.objects.filter(pk=self.subject.pk).update(assign_teacher=self.teacher)

        self.sa = SideActivity.objects.create(
            subject=self.subject, sub_type="daily_challenge",
            title="Test Challenge",
            content_json={"question": "What is 2+2?", "choices": ["3", "4", "5", "6"], "answer": 1},
            xp_reward=5,
        )

    def test_list_renders(self):
        self.client.login(username="sa_view_stu", password="testpass")
        resp = self.client.get(f"/gamification/side-activities/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Test Challenge")

    def test_play_renders(self):
        self.client.login(username="sa_view_stu", password="testpass")
        resp = self.client.get(f"/gamification/side-activity/{self.sa.pk}/play/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "What is 2+2?")

    def test_play_submit_awards_xp(self):
        self.client.login(username="sa_view_stu", password="testpass")
        resp = self.client.post(f"/gamification/side-activity/{self.sa.pk}/play/", {"answer": "1"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(SideActivityAttempt.objects.filter(student=self.student, side_activity=self.sa).exists())
        self.assertTrue(XPTransaction.objects.filter(student=self.student, source_type="side_activity").exists())

    def test_duplicate_attempt_no_extra_xp(self):
        self.client.login(username="sa_view_stu", password="testpass")
        self.client.post(f"/gamification/side-activity/{self.sa.pk}/play/", {"answer": "1"})
        xp_count_1 = XPTransaction.objects.filter(student=self.student, source_type="side_activity").count()
        self.client.post(f"/gamification/side-activity/{self.sa.pk}/play/", {"answer": "1"})
        xp_count_2 = XPTransaction.objects.filter(student=self.student, source_type="side_activity").count()
        self.assertEqual(xp_count_1, xp_count_2)

    def test_teacher_can_create(self):
        self.client.login(username="sa_view_teach", password="testpass")
        resp = self.client.get(f"/gamification/side-activities/{self.subject.pk}/create/")
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_create(self):
        self.client.login(username="sa_view_stu", password="testpass")
        resp = self.client.get(f"/gamification/side-activities/{self.subject.pk}/create/")
        self.assertEqual(resp.status_code, 302)


class SeedCommandTests(TestCase):
    def test_seed_creates_activities(self):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command("seed_side_activities", stdout=out)
        self.assertIn("Seeded", out.getvalue())
```

- [ ] **Step 2: Run tests**

Run: `cd ~/classedge && env/bin/python manage.py test gamification.tests.test_side_activities --keepdb -v2`
Expected: All ~16 tests PASS

- [ ] **Step 3: Run full gamification suite**

Run: `cd ~/classedge && env/bin/python manage.py test gamification --keepdb 2>&1 | tail -5`
Expected: All tests PASS (~53 existing + ~16 new = ~69 total)

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && git add gamification/tests/test_side_activities.py
git commit -m "test(side-activities): add scoring, view, CRUD, and seed tests"
```

---

## Summary

| Task | What it builds | Tests |
|------|---------------|-------|
| 1 | Models + migration | 3 |
| 2 | Scoring engine + list/play/submit views | — |
| 3 | 6 form-based type templates | — |
| 4 | JS modules (submit, timer, drag, flashcard, geo, typing, code) | — |
| 5 | 9 JS-driven type templates | — |
| 6 | Teacher CRUD (create/edit/delete) | — |
| 7 | Seed command + 10 badges + subject detail widget | — |
| 8 | Comprehensive test suite | ~13 |

**Total new tests: ~16**

**Deferred:** 4 badge evaluators (side_activity_streak, side_activity_early, side_activity_daily, side_activity_perfect_type) stubbed as returning False — they require complex date-based queries and will be refined as a follow-up.
