# Teacher Dashboard SP3 — Per-Subject Analytics

**Date:** 2026-04-18
**Status:** Approved
**Builds on:** SP1 (design system + analytics dashboard), SP2 (teacher gamification)

---

## What This Is

SP3 adds two new surfaces to the teacher dashboard:

1. **Subject analytics panel** — a slide-over panel that opens when a teacher clicks a subject card, showing 8 subject-level metrics + a full student roster table.
2. **Per-student detail page** — a full page showing every data point the teacher needs for one student in one subject.

---

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `gamification/subject_analytics.py` | Two views: `subject_panel_view` (HTMX fragment) + `student_detail_view` (full page) |
| `gamification/templates/gamification/subject_analytics_panel.html` | Panel HTML fragment returned by HTMX |
| `gamification/templates/gamification/student_detail.html` | Full student detail page, extends `teacher_base.html` |

### Modified Files

| File | Change |
|------|--------|
| `gamification/urls.py` | 2 new URL patterns |
| `gamification/templates/gamification/teacher_dashboard.html` | Subject cards get `hx-get` attributes; panel overlay div added |
| `teacher_base.html` | HTMX CDN script tag added |

### New URLs

```
gamification/subject/<int:subject_id>/analytics/panel/   → subject_panel_view   (HTMX fragment)
gamification/subject/<int:subject_id>/student/<int:student_id>/  → student_detail_view  (full page)
```

Both views require `@teacher_or_admin_required`.

### HTMX Flow

1. Each subject card in `teacher_dashboard.html` gets:
   ```html
   hx-get="/gamification/subject/{{ s.id }}/analytics/panel/"
   hx-target="#subject-panel"
   hx-swap="innerHTML"
   ```
2. A `<div id="subject-panel">` (fixed overlay, right side, hidden by default) lives at the bottom of `teacher_dashboard.html`.
3. On click, HTMX fetches the fragment and injects it — CSS transition slides the panel in from the right.
4. Close button (×) and backdrop click hide the panel via `hx-on` or a small inline JS handler.
5. Student rows link normally to the full student detail page (no HTMX needed).

---

## Subject Analytics Panel

### Layout

```
┌──────────────────────────────────────────┐
│ Math 101 Analytics                     × │
├──────────────────────────────────────────┤
│ [Avg Score] [At-Risk] [Completion] [Streaks] │  ← 4 summary tiles
├──────────────────────────────────────────┤
│ XP Distribution  │  Avg Score by Type   │  ← 2 mini-charts
├──────────────────────────────────────────┤
│ Module Engagement Heatmap                │  ← CSS grid
├──────────────────────────────────────────┤
│ Student table (Name / Score / Risk / Streak / Badges) │
└──────────────────────────────────────────┘
```

**Panel chrome:** 480px wide, slides in from right, backdrop overlay. Close via × button or backdrop click.

### Summary Tiles (4)

| Tile | Source |
|------|--------|
| Avg Score % | `StudentActivity` scores for this subject's enrolled students |
| At-Risk count | `at_risk.calculator.calculate_risk_scores(subject, semester)` |
| Completion rate % | submitted graded activities / total assigned graded activities |
| Active Streaks count | enrolled students with `StudentGamification.login_streak > 0` |

### Mini-Charts (CSS bar charts, no JS library)

**XP Distribution:** Bar chart with 4 buckets (0–200, 200–400, 400–600, 600+ XP). Bar height = % of students in that bucket. Data from `XPTransaction.objects.filter(student__in=enrolled_students)` aggregated per student (platform-wide XP — subject-scoped XP would require joining through source_id which varies by type).

**Avg Score by Activity Type:** One bar per activity type (Quiz, Assignment, Lab, Side Activity). Average of `StudentActivity.total_score / Activity.max_score` grouped by `Activity.activity_type`. Empty bar if no activities of that type.

### Module Engagement Heatmap

- CSS grid: rows = modules in this subject (max 10), columns = enrolled students (max 20, truncated name, horizontal scroll beyond that)
- Each cell = `StudentProgress.progress` for that module/student combination (0–100)
- Color scale: 0% = cream (`#faf7f2`), 50% = gold (`#b7925a`), 100% = forest (`#1b4332`)
- Missing `StudentProgress` row treated as 0%
- Module names truncated to 16 chars

### Student Table

| Column | Source | Notes |
|--------|--------|-------|
| Name | `CustomUser.get_full_name()` | Link to student detail page |
| Avg Score | `StudentActivity` avg for this subject | Formatted as `82%` |
| Risk | `calculate_risk_scores()` result | Color-coded badge: red=High, amber=Medium, green=Low |
| Streak | `StudentGamification.login_streak` | Shows `🔥N` or `—` if 0 |
| Badges | `StudentBadge.objects.filter(student=...).count()` | Integer |

Default sort: risk descending (High → Medium → Low → none), then avg score ascending within each tier.

---

## Per-Student Detail Page

**URL:** `/gamification/subject/<id>/student/<id>/`
**Template:** extends `teacher_base.html`

### Header

Student avatar (initials circle, forest green), full name, subject name + semester tag, risk badge (color-coded). Back link → `/dashboard/` (teacher dashboard).

### Summary Tiles (4)

Avg Score (this subject), Total XP (platform-wide from `XPTransaction`), Login Streak (`StudentGamification.login_streak`), Risk Level (from `calculate_risk_scores`).

### Section 1: Activity Score History

Table of all `StudentActivity` records for this student in this subject:
- Columns: Activity name, Type, Score / Max, %, Submitted date, On-time / Late tag
- On-time = submission timestamp ≤ `Activity.end_time` (verify exact submission timestamp field name on `StudentActivity` during implementation; null `end_time` = no deadline, always on-time)
- Sorted by submitted date descending
- Unsubmitted activities shown as `—` with Pending tag

### Section 2: Risk Breakdown

Three horizontal progress bars using the component scores from `calculate_risk_scores()`:
- Grade Score, Completion Score, Attendance Score
- Bar color: green if score ≥ 65, amber if 40–64, red if < 40
- Brief label explaining what each component measures

### Section 3: Module Progress

List of all `Module` objects for this subject. Each row:
- Module name
- Progress bar (0–100% from `StudentProgress.progress`)
- Status label: Completed (100%), In Progress (1–99%), Not Started (0% or missing)

### Section 4: XP & Streak Stats

Stat grid: Total XP, Current Level, Login Streak, Submission Streak, Accuracy Streak, Last Active Date. All from `StudentGamification` + `XPTransaction`.

### Section 5: Badges Earned

Icon grid of all `StudentBadge` records for this student (platform-wide, not subject-filtered). Shows badge name + tier on hover. Empty state: "No badges yet."

### Section 6: Recognition History

List of `TeacherRecognition` records where `teacher=request.user` and `student=student`. Shows message, XP awarded, date. Gold "Recognize" button at top → fires existing `send_recognition` AJAX endpoint (`/gamification/recognition/send/`) with pre-filled student ID.

---

## Data Access Patterns

All panel and student detail queries filter by:
- `semester` = current active semester (`Semester.objects.filter(is_active=True).first()`)
- `subject` = URL param `subject_id`, validated as belonging to `request.user` (teacher owns or collaborates)

Security: both views check `subject.assign_teacher == request.user or request.user in subject.collaborators.all()` before returning data. Return 403 if not authorized.

---

## Tests

**`gamification/tests/test_subject_analytics.py`** — new test file:

| Test | What it covers |
|------|---------------|
| `test_panel_requires_teacher` | Student/anon gets 403 |
| `test_panel_returns_fragment` | Response is partial HTML (no `<html>` tag) |
| `test_panel_summary_tiles` | Correct values in context |
| `test_panel_heatmap_data` | Correct module × student matrix |
| `test_panel_student_table_sorted` | High-risk students appear first |
| `test_student_detail_requires_teacher` | 403 for non-owner teacher |
| `test_student_detail_activity_history` | All activities present, sorted |
| `test_student_detail_risk_breakdown` | Component scores present |
| `test_student_detail_module_progress` | All modules listed |
| `test_student_detail_recognition_button` | Button present, links to correct endpoint |

Target: ~15 tests.

---

## What's Out of Scope

- Charts with a JS charting library (Chart.js, D3) — CSS bars only for now
- Filtering/sorting the student table client-side
- Exporting data to CSV
- Per-activity-type drill-down beyond the mini-chart
- Email or push notifications from this page
