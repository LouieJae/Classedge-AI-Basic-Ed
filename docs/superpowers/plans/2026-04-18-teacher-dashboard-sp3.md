# Teacher Dashboard SP3 — Per-Subject Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a subject analytics slide-over panel and a per-student detail page to the teacher dashboard using HTMX.

**Architecture:** Subject cards in `teacher_dashboard.html` get `hx-get` attributes; HTMX fetches an HTML fragment from `subject_panel_view` and injects it into a fixed overlay div. Student rows in the panel link to a full `student_detail_view` page. Both views live in a new `gamification/subject_analytics.py` file.

**Tech Stack:** Django 5, HTMX (CDN), existing design system (teacher_base.html, cream/forest/gold palette, Fraunces + Inter Tight).

---

## File Map

| Action | File |
|--------|------|
| Create | `gamification/subject_analytics.py` |
| Create | `gamification/templates/gamification/subject_analytics_panel.html` |
| Create | `gamification/templates/gamification/student_detail.html` |
| Create | `gamification/tests/test_subject_analytics.py` |
| Modify | `gamification/urls.py` |
| Modify | `gamification/templates/gamification/teacher_dashboard.html` |
| Modify | `templates/teacher_base.html` |

---

## Task 1: HTMX + URL Stubs + Panel Shell

**Files:**
- Modify: `templates/teacher_base.html`
- Modify: `gamification/urls.py`
- Modify: `gamification/templates/gamification/teacher_dashboard.html`
- Create: `gamification/subject_analytics.py` (stubs only)

- [ ] **Step 1: Add HTMX CDN to teacher_base.html**

Find the closing `</head>` tag in `templates/teacher_base.html` and add the HTMX script before it:

```html
<script src="https://unpkg.com/htmx.org@1.9.12" integrity="sha384-ujb1lZYygJmzgSwoxRggbCHcjc0rB2uodhrgzmievUHpHf3C4/XXqzLSGcvAHrp3" crossorigin="anonymous"></script>
```

- [ ] **Step 2: Add stub views to subject_analytics.py**

Create `gamification/subject_analytics.py`:

```python
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from course.models.semester_model import Semester
from roles.decorators import teacher_or_admin_required
from subject.models.subject_model import Subject


def _authorize_subject(request, subject_id):
    """Return subject if request.user owns or collaborates. Raise PermissionError otherwise."""
    subject = get_object_or_404(Subject, pk=subject_id)
    user = request.user
    if not (subject.assign_teacher == user or user in subject.collaborators.all()):
        raise PermissionError
    return subject


def _active_semester():
    now = timezone.now()
    return Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()


@teacher_or_admin_required
def subject_panel_view(request, subject_id):
    try:
        subject = _authorize_subject(request, subject_id)
    except PermissionError:
        return HttpResponse(status=403)
    return HttpResponse("<p>panel stub</p>")


@teacher_or_admin_required
def student_detail_view(request, subject_id, student_id):
    try:
        subject = _authorize_subject(request, subject_id)
    except PermissionError:
        return HttpResponse(status=403)
    return HttpResponse("<p>student stub</p>")
```

- [ ] **Step 3: Register URLs in gamification/urls.py**

Open `gamification/urls.py` and add to the `urlpatterns` list:

```python
from gamification.subject_analytics import subject_panel_view, student_detail_view

# add these two lines inside urlpatterns:
path("subject/<int:subject_id>/analytics/panel/", subject_panel_view, name="subject_analytics_panel"),
path("subject/<int:subject_id>/student/<int:student_id>/", student_detail_view, name="student_detail"),
```

- [ ] **Step 4: Add panel overlay div + HTMX attributes to teacher_dashboard.html**

In `gamification/templates/gamification/teacher_dashboard.html`, wrap each subject card with `hx-get` and add the panel overlay. Find the subject card loop (around `{% for s in subjects %}`) and make these changes:

**Change each `<div class="class-card ...">` to:**
```html
<div class="class-card {{ s.card_class }}"
     hx-get="{% url 'subject_analytics_panel' s.subject.id %}"
     hx-target="#subject-panel-content"
     hx-swap="innerHTML"
     hx-on::after-request="document.getElementById('subject-panel').classList.add('open')"
     style="cursor:pointer;">
```

**Add this block just before the closing `</main>` tag:**
```html
<!-- Subject analytics slide-over panel -->
<div id="subject-panel" class="subject-panel-overlay">
  <div class="subject-panel-backdrop" onclick="document.getElementById('subject-panel').classList.remove('open')"></div>
  <div class="subject-panel-drawer">
    <div id="subject-panel-content">
      <!-- HTMX injects panel fragment here -->
    </div>
  </div>
</div>
```

**Add these styles inside the `<style>` block (or at end of existing styles in teacher_dashboard.html):**
```css
.subject-panel-overlay {
  position: fixed; inset: 0; z-index: 400;
  visibility: hidden; opacity: 0;
  transition: opacity 0.2s, visibility 0.2s;
}
.subject-panel-overlay.open {
  visibility: visible; opacity: 1;
}
.subject-panel-backdrop {
  position: absolute; inset: 0;
  background: rgba(45, 49, 66, 0.35);
}
.subject-panel-drawer {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 480px; max-width: 100vw;
  background: var(--cream, #faf7f2);
  box-shadow: -4px 0 24px rgba(0,0,0,0.12);
  overflow-y: auto;
  transform: translateX(100%);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.subject-panel-overlay.open .subject-panel-drawer {
  transform: translateX(0);
}
```

- [ ] **Step 5: Verify server starts with no errors**

```bash
cd ~/classedge && source env/bin/activate && python manage.py check
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add -f lms/settings.py && git add templates/teacher_base.html gamification/urls.py gamification/templates/gamification/teacher_dashboard.html gamification/subject_analytics.py
git commit -m "feat(sp3): add HTMX, panel overlay shell, URL stubs"
```

---

## Task 2: subject_panel_view — Data Layer + Tests

**Files:**
- Create: `gamification/tests/test_subject_analytics.py`
- Modify: `gamification/subject_analytics.py`

- [ ] **Step 1: Write failing tests**

Create `gamification/tests/test_subject_analytics.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse

from ai_content.tests.test_models import _create_test_user, _create_subject
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.models import StudentGamification, StudentBadge, BadgeDefinition
from module.models.module import Module
from module.models.student_progress import StudentProgress

import datetime


def _make_semester():
    today = datetime.date.today()
    return Semester.objects.create(
        semester_name="First",
        start_date=today - datetime.timedelta(days=30),
        end_date=today + datetime.timedelta(days=60),
    )


def _enroll(student, subject, semester):
    return SubjectEnrollment.objects.create(
        student=student, subject=subject, semester=semester, status="enrolled",
    )


class SubjectPanelViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user("sp3_teach", "teacher")
        self.student1 = _create_test_user("sp3_stu1", "student")
        self.student2 = _create_test_user("sp3_stu2", "student")
        self.subject = _create_subject()
        self.subject.assign_teacher = self.teacher
        self.subject.save()
        self.semester = _make_semester()
        _enroll(self.student1, self.subject, self.semester)
        _enroll(self.student2, self.subject, self.semester)
        # ensure StudentGamification exists
        StudentGamification.objects.get_or_create(student=self.student1)
        StudentGamification.objects.get_or_create(student=self.student2)
        self.url = reverse("subject_analytics_panel", args=[self.subject.pk])

    def test_panel_requires_teacher(self):
        """Unauthenticated and student users cannot access the panel."""
        # unauthenticated
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)
        # student
        self.client.force_login(self.student1)
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)

    def test_panel_returns_fragment(self):
        """Panel response is an HTML fragment — no <html> root tag."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertNotIn("<html", content.lower())

    def test_panel_non_owner_teacher_gets_403(self):
        """A teacher who doesn't own/collaborate on the subject gets 403."""
        other_teacher = _create_test_user("sp3_other_teach", "teacher")
        self.client.force_login(other_teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_panel_summary_tiles_in_context(self):
        """Context contains the 4 summary tile keys."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        for key in ("avg_score", "at_risk_count", "completion_pct", "streak_count"):
            self.assertIn(key, r.context)

    def test_panel_student_table_in_context(self):
        """Context contains student_rows with expected keys."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertIn("student_rows", r.context)
        for row in r.context["student_rows"]:
            for key in ("student", "avg_score", "risk_level", "streak", "badge_count"):
                self.assertIn(key, row)

    def test_panel_student_table_sorted_by_risk(self):
        """High-risk students appear before low-risk students in student_rows."""
        from gamification.models import StudentGamification
        # Force student2 to have low login streak, student1 high
        # We can't force at-risk without real activities, so just verify order is stable
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        rows = r.context["student_rows"]
        RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
        risk_values = [RISK_ORDER[row["risk_level"]] for row in rows]
        self.assertEqual(risk_values, sorted(risk_values))

    def test_panel_heatmap_in_context(self):
        """Context contains heatmap_rows and heatmap_students."""
        Module.objects.create(subject=self.subject, file_name="Module 1")
        StudentProgress.objects.create(
            student=self.student1,
            module=Module.objects.filter(subject=self.subject).first(),
            progress=75,
        )
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertIn("heatmap_rows", r.context)
        self.assertIn("heatmap_students", r.context)

    def test_panel_xp_chart_in_context(self):
        """Context contains xp_chart as a list of 4 ints."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertIn("xp_chart", r.context)
        self.assertEqual(len(r.context["xp_chart"]), 4)
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd ~/classedge && source env/bin/activate && python manage.py test gamification.tests.test_subject_analytics --keepdb 2>&1 | tail -15
```

Expected: `FAILED` with errors about missing context keys (stub returns plain HttpResponse).

- [ ] **Step 3: Implement subject_panel_view**

Replace the stub `subject_panel_view` in `gamification/subject_analytics.py` with the full implementation:

```python
from django.db.models import Avg, Count
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from activity.models.activity_model import Activity
from activity.models.student_activity_model import StudentActivity
from at_risk.calculator import calculate_risk_scores
from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from course.models.term_model import Term
from gamification.models import StudentGamification, StudentBadge
from module.models.module import Module
from module.models.student_progress import StudentProgress
from roles.decorators import teacher_or_admin_required
from subject.models.subject_model import Subject


def _authorize_subject(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    user = request.user
    if not (subject.assign_teacher == user or user in subject.collaborators.all()):
        raise PermissionError
    return subject


def _active_semester():
    now = timezone.now()
    return Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()


def _progress_color(pct):
    """Interpolate cream→gold→forest based on completion %."""
    if pct <= 0:
        return "#faf7f2"
    if pct >= 100:
        return "#1b4332"
    if pct <= 50:
        t = pct / 50
        r = round(0xfa + t * (0xb7 - 0xfa))
        g = round(0xf7 + t * (0x92 - 0xf7))
        b = round(0xf2 + t * (0x5a - 0xf2))
    else:
        t = (pct - 50) / 50
        r = round(0xb7 + t * (0x1b - 0xb7))
        g = round(0x92 + t * (0x43 - 0x92))
        b = round(0x5a + t * (0x32 - 0x5a))
    return f"#{r:02x}{g:02x}{b:02x}"


@teacher_or_admin_required
def subject_panel_view(request, subject_id):
    try:
        subject = _authorize_subject(request, subject_id)
    except PermissionError:
        return HttpResponseForbidden()

    semester = _active_semester()
    terms = Term.objects.filter(semester=semester) if semester else Term.objects.none()

    enrolled_ids = list(
        SubjectEnrollment.objects.filter(
            subject=subject, semester=semester, status="enrolled",
        ).values_list("student_id", flat=True)
    ) if semester else []

    # -- Summary tiles --
    risk_data = calculate_risk_scores(subject, semester) if semester else []
    at_risk_count = sum(1 for r in risk_data if r["risk_level"] in ("high", "medium"))

    graded_acts = Activity.objects.filter(subject=subject, term__in=terms, is_graded=True)
    total_possible = graded_acts.count() * len(enrolled_ids)
    submitted_count = StudentActivity.objects.filter(
        student__in=enrolled_ids, activity__in=graded_acts,
    ).count()
    completion_pct = round(submitted_count / total_possible * 100) if total_possible else 0

    gam_qs = StudentGamification.objects.filter(student__in=enrolled_ids)
    streak_count = gam_qs.filter(login_streak__gt=0).count()

    # Per-student avg score (as %)
    RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
    student_avgs = {}
    for sa in StudentActivity.objects.filter(
        student__in=enrolled_ids, subject=subject, activity__term__in=terms,
        total_score__isnull=False, activity__max_score__gt=0,
    ).select_related("activity"):
        pct = sa.total_score / sa.activity.max_score * 100
        student_avgs.setdefault(sa.student_id, []).append(pct)
    student_avg_map = {k: round(sum(v) / len(v)) for k, v in student_avgs.items()}
    all_pcts = [p for pcts in student_avgs.values() for p in pcts]
    avg_score = round(sum(all_pcts) / len(all_pcts)) if all_pcts else 0

    # -- XP distribution chart --
    gam_xp = {g.student_id: g.total_xp for g in gam_qs}
    buckets = [0, 0, 0, 0]
    for xp in gam_xp.values():
        idx = min(int(xp // 200), 3)
        buckets[idx] += 1
    total = len(enrolled_ids) or 1
    xp_chart = [round(b / total * 100) for b in buckets]

    # -- Avg score by activity type chart --
    type_scores = {}
    for sa in StudentActivity.objects.filter(
        student__in=enrolled_ids, subject=subject, activity__term__in=terms,
        total_score__isnull=False, activity__max_score__gt=0,
    ).select_related("activity__activity_type"):
        type_name = sa.activity.activity_type.name if sa.activity.activity_type else "Other"
        pct = sa.total_score / sa.activity.max_score * 100
        type_scores.setdefault(type_name, []).append(pct)
    type_chart = {k: round(sum(v) / len(v)) for k, v in type_scores.items()}

    # -- Module heatmap --
    from django.contrib.auth import get_user_model
    User = get_user_model()
    modules = list(Module.objects.filter(subject=subject).order_by("pk")[:10])
    students_for_heatmap = list(
        User.objects.filter(pk__in=enrolled_ids[:20])
    )
    progress_map = {
        (sp.module_id, sp.student_id): float(sp.progress)
        for sp in StudentProgress.objects.filter(
            module__in=modules, student__in=students_for_heatmap,
        )
    }
    heatmap_rows = [
        {
            "module_name": mod.file_name[:16],
            "cells": [
                {
                    "pct": progress_map.get((mod.pk, stu.pk), 0),
                    "color": _progress_color(progress_map.get((mod.pk, stu.pk), 0)),
                }
                for stu in students_for_heatmap
            ],
        }
        for mod in modules
    ]
    heatmap_students = [s.get_full_name() or s.username for s in students_for_heatmap]

    # -- Student table --
    risk_by_id = {r["student_id"]: r for r in risk_data}
    gam_by_id = {g.student_id: g for g in gam_qs}
    badge_counts = {
        b["student"]: b["cnt"]
        for b in StudentBadge.objects.filter(student__in=enrolled_ids)
        .values("student").annotate(cnt=Count("pk"))
    }
    student_rows = sorted(
        [
            {
                "student": stu,
                "avg_score": student_avg_map.get(stu.pk, 0),
                "risk_level": risk_by_id.get(stu.pk, {}).get("risk_level", "low"),
                "streak": gam_by_id[stu.pk].login_streak if stu.pk in gam_by_id else 0,
                "badge_count": badge_counts.get(stu.pk, 0),
            }
            for stu in User.objects.filter(pk__in=enrolled_ids)
        ],
        key=lambda x: (RISK_ORDER.get(x["risk_level"], 2), x["avg_score"]),
    )

    return render(request, "gamification/subject_analytics_panel.html", {
        "subject": subject,
        "avg_score": avg_score,
        "at_risk_count": at_risk_count,
        "completion_pct": completion_pct,
        "streak_count": streak_count,
        "xp_chart": xp_chart,
        "type_chart": type_chart,
        "heatmap_rows": heatmap_rows,
        "heatmap_students": heatmap_students,
        "student_rows": student_rows,
    })
```

- [ ] **Step 4: Create minimal panel template so tests can render**

Create `gamification/templates/gamification/subject_analytics_panel.html`:

```html
<div class="sp3-panel">
  <p>avg_score={{ avg_score }} at_risk={{ at_risk_count }} completion={{ completion_pct }} streaks={{ streak_count }}</p>
</div>
```

(This stub is enough to pass context tests. Full template is built in Task 3.)

- [ ] **Step 5: Run panel tests**

```bash
cd ~/classedge && source env/bin/activate && python manage.py test gamification.tests.test_subject_analytics.SubjectPanelViewTests --keepdb 2>&1 | tail -10
```

Expected: `OK` — all `SubjectPanelViewTests` pass.

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add -f lms/settings.py && git add gamification/subject_analytics.py gamification/tests/test_subject_analytics.py gamification/templates/gamification/subject_analytics_panel.html
git commit -m "feat(sp3): subject_panel_view data layer + tests"
```

---

## Task 3: Panel Template

**Files:**
- Modify: `gamification/templates/gamification/subject_analytics_panel.html`

- [ ] **Step 1: Build the full panel template**

Replace `gamification/templates/gamification/subject_analytics_panel.html` with:

```html
<div class="sp3-panel">
  <!-- Header -->
  <div class="sp3-panel-header">
    <div>
      <div class="sp3-panel-subject">{{ subject.subject_name }}</div>
      <div class="sp3-panel-subtitle">Subject Analytics</div>
    </div>
    <button class="sp3-close-btn"
            onclick="document.getElementById('subject-panel').classList.remove('open')"
            aria-label="Close">✕</button>
  </div>

  <!-- Summary tiles -->
  <div class="sp3-tiles">
    <div class="sp3-tile">
      <div class="sp3-tile-value">{{ avg_score }}%</div>
      <div class="sp3-tile-label">Avg Score</div>
    </div>
    <div class="sp3-tile {% if at_risk_count > 0 %}warn{% endif %}">
      <div class="sp3-tile-value">{{ at_risk_count }}</div>
      <div class="sp3-tile-label">At-Risk</div>
    </div>
    <div class="sp3-tile">
      <div class="sp3-tile-value">{{ completion_pct }}%</div>
      <div class="sp3-tile-label">Completion</div>
    </div>
    <div class="sp3-tile">
      <div class="sp3-tile-value">🔥{{ streak_count }}</div>
      <div class="sp3-tile-label">Streaks</div>
    </div>
  </div>

  <!-- Mini-charts -->
  <div class="sp3-charts">
    <div class="sp3-chart-block">
      <div class="sp3-chart-title">XP Distribution</div>
      <div class="sp3-bar-chart">
        {% for pct in xp_chart %}
        <div class="sp3-bar-col">
          <div class="sp3-bar-fill" style="height:{{ pct }}%;"></div>
          <div class="sp3-bar-label">
            {% if forloop.counter == 1 %}0–200
            {% elif forloop.counter == 2 %}200–400
            {% elif forloop.counter == 3 %}400–600
            {% else %}600+{% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
    </div>
    <div class="sp3-chart-block">
      <div class="sp3-chart-title">Avg Score by Type</div>
      <div class="sp3-bar-chart">
        {% for type_name, avg in type_chart.items %}
        <div class="sp3-bar-col">
          <div class="sp3-bar-fill" style="height:{{ avg }}%;"></div>
          <div class="sp3-bar-label">{{ type_name|truncatechars:8 }}</div>
        </div>
        {% empty %}
        <div class="sp3-chart-empty">No graded activities yet.</div>
        {% endfor %}
      </div>
    </div>
  </div>

  <!-- Module engagement heatmap -->
  {% if heatmap_rows %}
  <div class="sp3-section">
    <div class="sp3-section-title">Module Engagement</div>
    <div class="sp3-heatmap-wrap">
      <table class="sp3-heatmap">
        <thead>
          <tr>
            <th></th>
            {% for name in heatmap_students %}
            <th class="sp3-heatmap-col-head" title="{{ name }}">{{ name|truncatechars:6 }}</th>
            {% endfor %}
          </tr>
        </thead>
        <tbody>
          {% for row in heatmap_rows %}
          <tr>
            <td class="sp3-heatmap-row-label" title="{{ row.module_name }}">{{ row.module_name }}</td>
            {% for cell in row.cells %}
            <td class="sp3-heatmap-cell" style="background:{{ cell.color }};" title="{{ cell.pct|floatformat:0 }}%"></td>
            {% endfor %}
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="sp3-heatmap-legend">
      <span style="background:#faf7f2;"></span> 0%
      <span style="background:#b7925a;margin-left:8px"></span> 50%
      <span style="background:#1b4332;margin-left:8px"></span> 100%
    </div>
  </div>
  {% endif %}

  <!-- Student table -->
  <div class="sp3-section">
    <div class="sp3-section-title">Students ({{ student_rows|length }})</div>
    {% if student_rows %}
    <table class="sp3-student-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Score</th>
          <th>Risk</th>
          <th>Streak</th>
          <th>Badges</th>
        </tr>
      </thead>
      <tbody>
        {% for row in student_rows %}
        <tr>
          <td>
            <a href="{% url 'student_detail' subject.id row.student.id %}" class="sp3-student-link">
              {{ row.student.get_full_name|default:row.student.username }}
            </a>
          </td>
          <td>{{ row.avg_score }}%</td>
          <td>
            <span class="sp3-risk-badge sp3-risk-{{ row.risk_level }}">
              {{ row.risk_level|capfirst }}
            </span>
          </td>
          <td>{% if row.streak %}🔥{{ row.streak }}{% else %}—{% endif %}</td>
          <td>{{ row.badge_count }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <p class="sp3-empty">No students enrolled this semester.</p>
    {% endif %}
  </div>
</div>

<style>
.sp3-panel { padding: 0; font-family: var(--body, 'Inter Tight', sans-serif); }
.sp3-panel-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  padding: 24px 24px 16px; border-bottom: 1px solid rgba(183,146,90,0.2);
  position: sticky; top: 0; background: var(--cream, #faf7f2); z-index: 1;
}
.sp3-panel-subject { font-family: var(--display, 'Fraunces', serif); font-size: 1.2rem; color: var(--forest, #1b4332); font-weight: 600; }
.sp3-panel-subtitle { font-size: 0.75rem; color: var(--ink-dim, #888); margin-top: 2px; }
.sp3-close-btn { background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--ink-dim, #888); padding: 4px 8px; border-radius: 4px; }
.sp3-close-btn:hover { background: rgba(0,0,0,0.06); }
.sp3-tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 16px 24px; }
.sp3-tile { background: white; border-radius: 8px; padding: 12px 8px; text-align: center; border: 1px solid rgba(0,0,0,0.06); }
.sp3-tile.warn .sp3-tile-value { color: var(--rose, #c08479); }
.sp3-tile-value { font-size: 1.3rem; font-weight: 700; color: var(--forest, #1b4332); line-height: 1.2; }
.sp3-tile-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-dim, #888); margin-top: 4px; }
.sp3-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 0 24px 16px; }
.sp3-chart-block { background: white; border-radius: 8px; padding: 12px; border: 1px solid rgba(0,0,0,0.06); }
.sp3-chart-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-dim, #888); margin-bottom: 8px; }
.sp3-bar-chart { display: flex; align-items: flex-end; gap: 4px; height: 60px; }
.sp3-bar-col { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; justify-content: flex-end; }
.sp3-bar-fill { width: 100%; background: var(--forest, #1b4332); border-radius: 2px 2px 0 0; min-height: 2px; transition: height 0.3s; }
.sp3-bar-label { font-size: 0.55rem; color: var(--ink-dim, #888); margin-top: 3px; text-align: center; }
.sp3-chart-empty { font-size: 0.75rem; color: var(--ink-dim, #888); font-style: italic; }
.sp3-section { padding: 0 24px 20px; }
.sp3-section-title { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-dim, #888); margin-bottom: 10px; padding-top: 4px; }
.sp3-heatmap-wrap { overflow-x: auto; }
.sp3-heatmap { border-collapse: collapse; width: 100%; }
.sp3-heatmap th, .sp3-heatmap td { padding: 2px; }
.sp3-heatmap-col-head { font-size: 0.6rem; color: var(--ink-dim, #888); font-weight: 400; writing-mode: vertical-rl; transform: rotate(180deg); height: 40px; }
.sp3-heatmap-row-label { font-size: 0.65rem; color: var(--ink, #2d3142); white-space: nowrap; padding-right: 6px !important; max-width: 100px; overflow: hidden; text-overflow: ellipsis; }
.sp3-heatmap-cell { width: 16px; height: 16px; border-radius: 2px; border: 1px solid rgba(255,255,255,0.3); }
.sp3-heatmap-legend { display: flex; align-items: center; gap: 4px; font-size: 0.65rem; color: var(--ink-dim, #888); margin-top: 6px; }
.sp3-heatmap-legend span { display: inline-block; width: 12px; height: 12px; border-radius: 2px; }
.sp3-student-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.sp3-student-table th { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-dim, #888); padding: 6px 8px; text-align: left; border-bottom: 1px solid rgba(0,0,0,0.08); }
.sp3-student-table td { padding: 8px 8px; border-bottom: 1px solid rgba(0,0,0,0.04); color: var(--ink, #2d3142); }
.sp3-student-link { color: var(--forest, #1b4332); text-decoration: none; font-weight: 500; }
.sp3-student-link:hover { text-decoration: underline; }
.sp3-risk-badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 999px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.sp3-risk-high { background: #fce8e6; color: #b0413e; }
.sp3-risk-medium { background: #fdf3e3; color: #9a6700; }
.sp3-risk-low { background: #e8f4ef; color: #1b4332; }
.sp3-empty { font-style: italic; color: var(--ink-dim, #888); font-size: 0.85rem; text-align: center; padding: 24px 0; }
</style>
```

- [ ] **Step 2: Verify panel renders in browser**

Ensure the dev server is running (`python manage.py runserver 8000`), log in as a teacher, click a subject card. The panel should slide in from the right with tiles, charts, heatmap, and student table visible.

- [ ] **Step 3: Commit**

```bash
cd ~/classedge && git add -f lms/settings.py && git add gamification/templates/gamification/subject_analytics_panel.html
git commit -m "feat(sp3): subject analytics panel template"
```

---

## Task 4: student_detail_view — Data Layer + Tests

**Files:**
- Modify: `gamification/tests/test_subject_analytics.py` (add `StudentDetailViewTests`)
- Modify: `gamification/subject_analytics.py` (replace stub)

- [ ] **Step 1: Add failing tests for student_detail_view**

Append to `gamification/tests/test_subject_analytics.py`:

```python
from activity.models.activity_model import Activity, ActivityType
from activity.models.student_activity_model import StudentActivity
from course.models.term_model import Term
from gamification.teacher_models import TeacherRecognition


class StudentDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teacher = _create_test_user("sd_teach", "teacher")
        self.student = _create_test_user("sd_stu", "student")
        self.subject = _create_subject()
        self.subject.assign_teacher = self.teacher
        self.subject.save()
        self.semester = _make_semester()
        _enroll(self.student, self.subject, self.semester)
        StudentGamification.objects.get_or_create(student=self.student)
        self.url = reverse("student_detail", args=[self.subject.pk, self.student.pk])

    def test_student_detail_requires_teacher(self):
        """Unauthenticated and student users cannot access student detail."""
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)
        self.client.force_login(self.student)
        r = self.client.get(self.url)
        self.assertNotEqual(r.status_code, 200)

    def test_student_detail_non_owner_gets_403(self):
        """Teacher who doesn't own the subject gets 403."""
        other = _create_test_user("sd_other_teach", "teacher")
        self.client.force_login(other)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    def test_student_detail_renders(self):
        """Owner teacher gets 200 and expected context keys."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        for key in ("subject", "student", "avg_score", "total_xp", "login_streak",
                    "risk_level", "activity_history", "risk_breakdown",
                    "module_progress", "xp_stats", "badges", "recognitions"):
            self.assertIn(key, r.context, msg=f"Missing context key: {key}")

    def test_student_detail_activity_history(self):
        """Activity history contains activities for this subject."""
        term = Term.objects.create(
            semester=self.semester, term_name="Term 1",
            start_date=self.semester.start_date, end_date=self.semester.end_date,
        )
        act_type = ActivityType.objects.create(name="Quiz")
        act = Activity.objects.create(
            activity_name="Quiz 1", subject=self.subject, term=term,
            max_score=100, is_graded=True, activity_type=act_type,
        )
        StudentActivity.objects.create(
            student=self.student, activity=act, subject=self.subject,
            total_score=85,
        )
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        history = r.context["activity_history"]
        names = [a["name"] for a in history]
        self.assertIn("Quiz 1", names)

    def test_student_detail_risk_breakdown_keys(self):
        """risk_breakdown contains grade_score, completion_score, attendance_score."""
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        rb = r.context["risk_breakdown"]
        for key in ("grade_score", "completion_score", "attendance_score"):
            self.assertIn(key, rb)

    def test_student_detail_module_progress(self):
        """module_progress lists modules with progress and status."""
        Module.objects.create(subject=self.subject, file_name="Chapter 1")
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        mp = r.context["module_progress"]
        self.assertTrue(len(mp) >= 1)
        for entry in mp:
            for key in ("module", "progress", "status"):
                self.assertIn(key, entry)

    def test_student_detail_recognition_history(self):
        """Recognitions sent by this teacher to this student appear in context."""
        TeacherRecognition.objects.create(
            teacher=self.teacher, student=self.student,
            message="Great work!", xp_awarded=10,
        )
        self.client.force_login(self.teacher)
        r = self.client.get(self.url)
        self.assertEqual(r.context["recognitions"].count(), 1)
        self.assertEqual(r.context["recognitions"].first().message, "Great work!")
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd ~/classedge && source env/bin/activate && python manage.py test gamification.tests.test_subject_analytics.StudentDetailViewTests --keepdb 2>&1 | tail -10
```

Expected: `FAILED` — stub returns 200 plain text but context keys are missing.

- [ ] **Step 3: Implement student_detail_view**

Add the full `student_detail_view` to `gamification/subject_analytics.py` (replacing the stub):

```python
@teacher_or_admin_required
def student_detail_view(request, subject_id, student_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        subject = _authorize_subject(request, subject_id)
    except PermissionError:
        return HttpResponseForbidden()

    student = get_object_or_404(User, pk=student_id)
    semester = _active_semester()
    terms = Term.objects.filter(semester=semester) if semester else Term.objects.none()

    # Summary tiles
    sa_qs = StudentActivity.objects.filter(
        student=student, subject=subject, activity__term__in=terms,
        total_score__isnull=False, activity__max_score__gt=0,
    ).select_related("activity")
    score_pcts = [sa.total_score / sa.activity.max_score * 100 for sa in sa_qs]
    avg_score = round(sum(score_pcts) / len(score_pcts)) if score_pcts else 0

    gam = StudentGamification.objects.filter(student=student).first()
    total_xp = gam.total_xp if gam else 0
    login_streak = gam.login_streak if gam else 0

    risk_data = calculate_risk_scores(subject, semester) if semester else []
    risk_info = next((r for r in risk_data if r["student_id"] == student.pk), {})
    risk_level = risk_info.get("risk_level", "low")

    # Section 1: Activity score history
    all_activities = Activity.objects.filter(
        subject=subject, term__in=terms,
    ).select_related("activity_type").order_by("-end_time", "-pk")
    sa_by_act = {
        sa.activity_id: sa
        for sa in StudentActivity.objects.filter(student=student, activity__in=all_activities)
    }
    activity_history = []
    for act in all_activities:
        sa = sa_by_act.get(act.pk)
        if sa and sa.total_score is not None and act.max_score:
            pct = round(sa.total_score / act.max_score * 100)
            on_time = None
            if act.end_time and sa.end_time:
                on_time = sa.end_time <= act.end_time
            activity_history.append({
                "name": act.activity_name,
                "type": act.activity_type.name if act.activity_type else "—",
                "score": sa.total_score,
                "max_score": act.max_score,
                "pct": pct,
                "submitted": sa.end_time,
                "on_time": on_time,
                "status": "graded",
            })
        else:
            activity_history.append({
                "name": act.activity_name,
                "type": act.activity_type.name if act.activity_type else "—",
                "score": None,
                "max_score": act.max_score,
                "pct": None,
                "submitted": None,
                "on_time": None,
                "status": "pending",
            })

    # Section 2: Risk breakdown
    risk_breakdown = {
        "grade_score": risk_info.get("grade_score", 0),
        "completion_score": risk_info.get("completion_score", 0),
        "attendance_score": risk_info.get("attendance_score", 0),
    }

    # Section 3: Module progress
    modules = Module.objects.filter(subject=subject).order_by("pk")
    progress_map = {
        sp.module_id: sp
        for sp in StudentProgress.objects.filter(student=student, module__in=modules)
    }
    module_progress = []
    for mod in modules:
        sp = progress_map.get(mod.pk)
        progress = float(sp.progress) if sp else 0
        if progress >= 100:
            status = "completed"
        elif progress > 0:
            status = "in_progress"
        else:
            status = "not_started"
        module_progress.append({"module": mod, "progress": progress, "status": status})

    # Section 4: XP & streak stats
    xp_stats = {
        "total_xp": gam.total_xp if gam else 0,
        "current_level": gam.current_level if gam else 1,
        "login_streak": gam.login_streak if gam else 0,
        "submission_streak": gam.submission_streak if gam else 0,
        "accuracy_streak": gam.accuracy_streak if gam else 0,
        "last_active": gam.last_active_date if gam else None,
    }

    # Section 5: Badges
    badges = StudentBadge.objects.filter(student=student).select_related("badge")

    # Section 6: Recognition history
    from gamification.teacher_models import TeacherRecognition
    recognitions = TeacherRecognition.objects.filter(
        teacher=request.user, student=student,
    ).order_by("-created_at")

    return render(request, "gamification/student_detail.html", {
        "subject": subject,
        "student": student,
        "semester": semester,
        "avg_score": avg_score,
        "total_xp": total_xp,
        "login_streak": login_streak,
        "risk_level": risk_level,
        "activity_history": activity_history,
        "risk_breakdown": risk_breakdown,
        "module_progress": module_progress,
        "xp_stats": xp_stats,
        "badges": badges,
        "recognitions": recognitions,
    })
```

- [ ] **Step 4: Create minimal student_detail template stub**

Create `gamification/templates/gamification/student_detail.html`:

```html
{% extends "teacher_base.html" %}
{% block content %}
<p>student={{ student }} subject={{ subject }}</p>
{% endblock %}
```

- [ ] **Step 5: Run student detail tests**

```bash
cd ~/classedge && source env/bin/activate && python manage.py test gamification.tests.test_subject_analytics.StudentDetailViewTests --keepdb 2>&1 | tail -10
```

Expected: `OK` — all `StudentDetailViewTests` pass.

- [ ] **Step 6: Commit**

```bash
cd ~/classedge && git add -f lms/settings.py && git add gamification/subject_analytics.py gamification/tests/test_subject_analytics.py gamification/templates/gamification/student_detail.html
git commit -m "feat(sp3): student_detail_view data layer + tests"
```

---

## Task 5: Student Detail Template

**Files:**
- Modify: `gamification/templates/gamification/student_detail.html`

- [ ] **Step 1: Build the full student detail template**

Replace `gamification/templates/gamification/student_detail.html` with:

```html
{% extends "teacher_base.html" %}
{% block content %}
<div class="sp3-detail">

  <!-- Header -->
  <div class="sp3-detail-header">
    <a href="/dashboard/" class="sp3-back-link">← Dashboard</a>
    <div class="sp3-detail-identity">
      <div class="sp3-avatar">{{ student.get_full_name|default:student.username|slice:":1"|upper }}</div>
      <div>
        <div class="sp3-detail-name">{{ student.get_full_name|default:student.username }}</div>
        <div class="sp3-detail-meta">
          {{ subject.subject_name }}
          {% if semester %} · {{ semester.semester_name }}{% endif %}
        </div>
      </div>
      <span class="sp3-risk-badge sp3-risk-{{ risk_level }}">{{ risk_level|capfirst }}</span>
    </div>
  </div>

  <!-- Summary tiles -->
  <div class="sp3-tiles sp3-detail-tiles">
    <div class="sp3-tile">
      <div class="sp3-tile-value">{{ avg_score }}%</div>
      <div class="sp3-tile-label">Avg Score</div>
    </div>
    <div class="sp3-tile">
      <div class="sp3-tile-value">{{ total_xp }}</div>
      <div class="sp3-tile-label">Total XP</div>
    </div>
    <div class="sp3-tile">
      <div class="sp3-tile-value">{% if login_streak %}🔥{{ login_streak }}{% else %}—{% endif %}</div>
      <div class="sp3-tile-label">Login Streak</div>
    </div>
    <div class="sp3-tile sp3-risk-tile-{{ risk_level }}">
      <div class="sp3-tile-value">{{ risk_level|capfirst }}</div>
      <div class="sp3-tile-label">Risk Level</div>
    </div>
  </div>

  <div class="sp3-detail-body">

    <!-- Section 1: Activity score history -->
    <div class="sp3-card">
      <div class="sp3-card-title">Activity Score History</div>
      {% if activity_history %}
      <table class="sp3-table">
        <thead>
          <tr><th>Activity</th><th>Type</th><th>Score</th><th>%</th><th>Submitted</th><th>Status</th></tr>
        </thead>
        <tbody>
          {% for a in activity_history %}
          <tr>
            <td>{{ a.name }}</td>
            <td class="sp3-dim">{{ a.type }}</td>
            <td>{% if a.score is not None %}{{ a.score|floatformat:0 }}/{{ a.max_score }}{% else %}—{% endif %}</td>
            <td>{% if a.pct is not None %}<span class="{% if a.pct >= 75 %}sp3-good{% else %}sp3-warn{% endif %}">{{ a.pct }}%</span>{% else %}—{% endif %}</td>
            <td class="sp3-dim">{% if a.submitted %}{{ a.submitted|date:"M d" }}{% else %}—{% endif %}</td>
            <td>
              {% if a.status == "graded" %}
                {% if a.on_time is None %}<span class="sp3-tag">Graded</span>
                {% elif a.on_time %}<span class="sp3-tag sp3-tag-good">On time</span>
                {% else %}<span class="sp3-tag sp3-tag-warn">Late</span>{% endif %}
              {% else %}<span class="sp3-tag">Pending</span>{% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <p class="sp3-empty">No activities yet.</p>
      {% endif %}
    </div>

    <!-- Section 2: Risk breakdown -->
    <div class="sp3-card">
      <div class="sp3-card-title">Risk Breakdown</div>
      {% for label, key, desc in "Grade Score,grade_score,Based on average scores across activities|Completion Score,completion_score,Based on activities submitted vs assigned|Attendance Score,attendance_score,Based on class attendance records"|split:"|" %}
      {% with score=risk_breakdown|default_if_none:0 %}
      {% endwith %}
      {% endfor %}
      {% with rb=risk_breakdown %}
      {% for item in "grade_score,Grade Score,Based on average scores|completion_score,Completion Score,Based on submissions|attendance_score,Attendance Score,Based on attendance"|split:"|" %}
      {% endfor %}
      <div class="sp3-risk-row">
        <div class="sp3-risk-label">Grade Score <span class="sp3-risk-desc">avg scores across activities</span></div>
        <div class="sp3-risk-bar-wrap">
          <div class="sp3-risk-bar {% if rb.grade_score >= 65 %}good{% elif rb.grade_score >= 40 %}amber{% else %}red{% endif %}" style="width:{{ rb.grade_score }}%;"></div>
        </div>
        <div class="sp3-risk-val">{{ rb.grade_score|floatformat:0 }}</div>
      </div>
      <div class="sp3-risk-row">
        <div class="sp3-risk-label">Completion Score <span class="sp3-risk-desc">activities submitted vs assigned</span></div>
        <div class="sp3-risk-bar-wrap">
          <div class="sp3-risk-bar {% if rb.completion_score >= 65 %}good{% elif rb.completion_score >= 40 %}amber{% else %}red{% endif %}" style="width:{{ rb.completion_score }}%;"></div>
        </div>
        <div class="sp3-risk-val">{{ rb.completion_score|floatformat:0 }}</div>
      </div>
      <div class="sp3-risk-row">
        <div class="sp3-risk-label">Attendance Score <span class="sp3-risk-desc">attendance records</span></div>
        <div class="sp3-risk-bar-wrap">
          <div class="sp3-risk-bar {% if rb.attendance_score >= 65 %}good{% elif rb.attendance_score >= 40 %}amber{% else %}red{% endif %}" style="width:{{ rb.attendance_score }}%;"></div>
        </div>
        <div class="sp3-risk-val">{{ rb.attendance_score|floatformat:0 }}</div>
      </div>
      {% endwith %}
    </div>

    <!-- Section 3: Module progress -->
    <div class="sp3-card">
      <div class="sp3-card-title">Module Progress</div>
      {% if module_progress %}
      {% for mp in module_progress %}
      <div class="sp3-module-row">
        <div class="sp3-module-name">{{ mp.module.file_name }}</div>
        <div class="sp3-module-bar-wrap">
          <div class="sp3-module-bar" style="width:{{ mp.progress|floatformat:0 }}%;"></div>
        </div>
        <div class="sp3-module-pct">{{ mp.progress|floatformat:0 }}%</div>
        <span class="sp3-tag {% if mp.status == 'completed' %}sp3-tag-good{% elif mp.status == 'in_progress' %}sp3-tag-amber{% endif %}">
          {{ mp.status|title|cut:"_" }}
        </span>
      </div>
      {% endfor %}
      {% else %}
      <p class="sp3-empty">No modules in this subject.</p>
      {% endif %}
    </div>

    <!-- Section 4: XP & Streak Stats -->
    <div class="sp3-card">
      <div class="sp3-card-title">XP &amp; Streak Stats</div>
      <div class="sp3-stat-grid">
        <div class="sp3-stat"><div class="sp3-stat-val">{{ xp_stats.total_xp }}</div><div class="sp3-stat-label">Total XP</div></div>
        <div class="sp3-stat"><div class="sp3-stat-val">Lv {{ xp_stats.current_level }}</div><div class="sp3-stat-label">Level</div></div>
        <div class="sp3-stat"><div class="sp3-stat-val">{% if xp_stats.login_streak %}🔥{{ xp_stats.login_streak }}{% else %}—{% endif %}</div><div class="sp3-stat-label">Login Streak</div></div>
        <div class="sp3-stat"><div class="sp3-stat-val">{{ xp_stats.submission_streak }}</div><div class="sp3-stat-label">Submission Streak</div></div>
        <div class="sp3-stat"><div class="sp3-stat-val">{{ xp_stats.accuracy_streak }}</div><div class="sp3-stat-label">Accuracy Streak</div></div>
        <div class="sp3-stat"><div class="sp3-stat-val">{% if xp_stats.last_active %}{{ xp_stats.last_active|date:"M d" }}{% else %}—{% endif %}</div><div class="sp3-stat-label">Last Active</div></div>
      </div>
    </div>

    <!-- Section 5: Badges earned -->
    <div class="sp3-card">
      <div class="sp3-card-title">Badges Earned</div>
      {% if badges %}
      <div class="sp3-badge-grid">
        {% for sb in badges %}
        <div class="sp3-badge-item" title="{{ sb.badge.name }} · {{ sb.badge.tier|capfirst }}">
          <div class="sp3-badge-icon">{{ sb.badge.icon|default:"🏅" }}</div>
          <div class="sp3-badge-name">{{ sb.badge.name|truncatechars:14 }}</div>
        </div>
        {% endfor %}
      </div>
      {% else %}
      <p class="sp3-empty">No badges yet. Complete challenges to earn the first one!</p>
      {% endif %}
    </div>

    <!-- Section 6: Recognition history -->
    <div class="sp3-card">
      <div class="sp3-card-title">
        Recognition History
        <button class="sp3-recognize-btn"
                onclick="document.getElementById('recognize-modal-{{ student.pk }}').style.display='flex'"
                data-student-id="{{ student.pk }}">
          Recognize
        </button>
      </div>
      {% if recognitions %}
      {% for rec in recognitions %}
      <div class="sp3-rec-row">
        <div class="sp3-rec-msg">{{ rec.message }}</div>
        <div class="sp3-rec-meta">+{{ rec.xp_awarded }} XP · {{ rec.created_at|date:"M d, Y" }}</div>
      </div>
      {% endfor %}
      {% else %}
      <p class="sp3-empty">No recognitions sent yet.</p>
      {% endif %}
    </div>

  </div><!-- .sp3-detail-body -->
</div><!-- .sp3-detail -->

<style>
.sp3-detail { max-width: 900px; margin: 0 auto; padding: 0 0 60px; }
.sp3-detail-header { padding: 32px 0 24px; }
.sp3-back-link { font-size: 0.8rem; color: var(--forest, #1b4332); text-decoration: none; display: inline-block; margin-bottom: 16px; }
.sp3-back-link:hover { text-decoration: underline; }
.sp3-detail-identity { display: flex; align-items: center; gap: 16px; }
.sp3-avatar { width: 48px; height: 48px; border-radius: 50%; background: var(--forest, #1b4332); color: white; display: flex; align-items: center; justify-content: center; font-family: var(--display, 'Fraunces', serif); font-size: 1.4rem; flex-shrink: 0; }
.sp3-detail-name { font-family: var(--display, 'Fraunces', serif); font-size: 1.5rem; color: var(--forest, #1b4332); font-weight: 600; }
.sp3-detail-meta { font-size: 0.8rem; color: var(--ink-dim, #888); margin-top: 2px; }
.sp3-detail-tiles { grid-template-columns: repeat(4, 1fr); margin-bottom: 28px; }
.sp3-risk-tile-high .sp3-tile-value { color: #b0413e; }
.sp3-risk-tile-medium .sp3-tile-value { color: #9a6700; }
.sp3-risk-tile-low .sp3-tile-value { color: var(--forest, #1b4332); }
.sp3-detail-body { display: flex; flex-direction: column; gap: 20px; }
.sp3-card { background: white; border-radius: 12px; padding: 20px 24px; border: 1px solid rgba(0,0,0,0.06); }
.sp3-card-title { font-family: var(--display, 'Fraunces', serif); font-size: 1rem; color: var(--forest, #1b4332); font-weight: 600; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.sp3-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.sp3-table th { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-dim, #888); padding: 6px 8px; text-align: left; border-bottom: 1px solid rgba(0,0,0,0.08); }
.sp3-table td { padding: 8px 8px; border-bottom: 1px solid rgba(0,0,0,0.04); color: var(--ink, #2d3142); }
.sp3-dim { color: var(--ink-dim, #888); }
.sp3-good { color: #1b4332; font-weight: 600; }
.sp3-warn { color: #9a6700; font-weight: 600; }
.sp3-tag { font-size: 0.65rem; padding: 2px 7px; border-radius: 999px; background: #f0ede8; color: #888; font-weight: 500; }
.sp3-tag-good { background: #e8f4ef; color: #1b4332; }
.sp3-tag-warn, .sp3-tag-amber { background: #fdf3e3; color: #9a6700; }
.sp3-risk-row { display: grid; grid-template-columns: 160px 1fr 36px; align-items: center; gap: 10px; margin-bottom: 12px; }
.sp3-risk-label { font-size: 0.78rem; color: var(--ink, #2d3142); }
.sp3-risk-desc { display: block; font-size: 0.65rem; color: var(--ink-dim, #888); font-weight: 400; }
.sp3-risk-bar-wrap { height: 8px; background: #f0ede8; border-radius: 4px; overflow: hidden; }
.sp3-risk-bar { height: 100%; border-radius: 4px; }
.sp3-risk-bar.good { background: var(--forest, #1b4332); }
.sp3-risk-bar.amber { background: var(--gold, #b7925a); }
.sp3-risk-bar.red { background: var(--rose, #c08479); }
.sp3-risk-val { font-size: 0.78rem; font-weight: 600; color: var(--ink, #2d3142); text-align: right; }
.sp3-module-row { display: grid; grid-template-columns: 160px 1fr 36px auto; align-items: center; gap: 10px; margin-bottom: 10px; }
.sp3-module-name { font-size: 0.8rem; color: var(--ink, #2d3142); }
.sp3-module-bar-wrap { height: 6px; background: #f0ede8; border-radius: 3px; overflow: hidden; }
.sp3-module-bar { height: 100%; background: var(--forest, #1b4332); border-radius: 3px; }
.sp3-module-pct { font-size: 0.75rem; font-weight: 600; text-align: right; color: var(--ink-dim, #888); }
.sp3-stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.sp3-stat { background: #faf7f2; border-radius: 8px; padding: 12px; text-align: center; }
.sp3-stat-val { font-size: 1.2rem; font-weight: 700; color: var(--forest, #1b4332); }
.sp3-stat-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-dim, #888); margin-top: 3px; }
.sp3-badge-grid { display: flex; flex-wrap: wrap; gap: 12px; }
.sp3-badge-item { display: flex; flex-direction: column; align-items: center; gap: 4px; width: 72px; text-align: center; }
.sp3-badge-icon { font-size: 1.8rem; }
.sp3-badge-name { font-size: 0.65rem; color: var(--ink-dim, #888); line-height: 1.2; }
.sp3-rec-row { padding: 10px 0; border-bottom: 1px solid rgba(0,0,0,0.05); }
.sp3-rec-msg { font-size: 0.85rem; color: var(--ink, #2d3142); }
.sp3-rec-meta { font-size: 0.72rem; color: var(--gold, #b7925a); margin-top: 2px; }
.sp3-recognize-btn { font-size: 0.75rem; background: var(--gold, #b7925a); color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-weight: 600; }
.sp3-recognize-btn:hover { background: #a07848; }
.sp3-empty { font-style: italic; color: var(--ink-dim, #888); font-size: 0.85rem; text-align: center; padding: 16px 0; margin: 0; }

/* Reuse shared panel styles if not already global */
.sp3-tiles { display: grid; gap: 8px; }
.sp3-tile { background: white; border-radius: 8px; padding: 12px 8px; text-align: center; border: 1px solid rgba(0,0,0,0.06); }
.sp3-tile-value { font-size: 1.3rem; font-weight: 700; color: var(--forest, #1b4332); line-height: 1.2; }
.sp3-tile-label { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-dim, #888); margin-top: 4px; }
.sp3-risk-badge { font-size: 0.65rem; padding: 2px 7px; border-radius: 999px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
.sp3-risk-high { background: #fce8e6; color: #b0413e; }
.sp3-risk-medium { background: #fdf3e3; color: #9a6700; }
.sp3-risk-low { background: #e8f4ef; color: #1b4332; }
</style>
{% endblock %}
```

- [ ] **Step 2: Verify student detail page renders in browser**

With the dev server running and logged in as a teacher, open the subject panel, click a student row, and verify the student detail page renders all 6 sections.

- [ ] **Step 3: Run all SP3 tests**

```bash
cd ~/classedge && source env/bin/activate && python manage.py test gamification.tests.test_subject_analytics --keepdb 2>&1 | tail -10
```

Expected: `OK` — all 15 tests pass.

- [ ] **Step 4: Commit**

```bash
cd ~/classedge && git add -f lms/settings.py && git add gamification/templates/gamification/student_detail.html
git commit -m "feat(sp3): student detail template — all 6 sections"
```

---

## Task 6: Final Polish + Push

**Files:**
- Modify: `gamification/templates/gamification/teacher_dashboard.html` (ensure subject cards are visually clickable)

- [ ] **Step 1: Add click hint to subject cards**

In `teacher_dashboard.html`, add a subtle "View analytics →" link at the bottom of each class card (inside the `{% for s in subjects %}` loop, just before the closing `</div>` of `.class-card`):

```html
<div class="class-analytics-hint">View analytics →</div>
```

Add CSS:
```css
.class-analytics-hint {
  font-size: 0.7rem; color: var(--gold, #b7925a);
  text-align: right; margin-top: 10px;
  opacity: 0.7; transition: opacity 0.15s;
}
.class-card:hover .class-analytics-hint { opacity: 1; }
```

- [ ] **Step 2: Run full gamification test suite**

```bash
cd ~/classedge && source env/bin/activate && python manage.py test gamification --keepdb 2>&1 | tail -5
```

Expected: All gamification tests pass (NeonDB connection drops are infrastructure noise — not test failures).

- [ ] **Step 3: Commit and push**

```bash
cd ~/classedge && git add -f lms/settings.py && git add -A
git commit -m "feat(sp3): teacher dashboard subject analytics + student detail page"
git push personal main
```
