# Teacher Gradebook Design Alignment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle four daily-use teacher gradebook templates so they consume the design tokens already defined in `templates/teacher_base.html`, mirroring the visual language of `templates/teacher/subject_list.html`.

**Architecture:** Each template inlines its CSS inside `{% block extra_css %}<style>…</style>{% endblock %}` — same pattern subject pages use. No new files, no JS frameworks, no DataTables/Bootstrap/Select2. Hardcoded hex values are replaced with token references (`var(--forest)`, `var(--gold)`, `var(--cream)`, `var(--paper)`, `var(--ink)`, `var(--radius)`, etc.).

**Tech Stack:** Django templates, vanilla CSS (custom properties already defined on `:root` in `teacher_base.html`), FontAwesome (loaded by `templates/base.html`). No JavaScript added.

**Reference spec:** `docs/superpowers/specs/2026-04-29-teacher-gradebook-design-alignment-design.md`

**Reference template (the visual target):** `templates/teacher/subject_list.html`

**Verification approach:** This is presentation-only work. The project has no visual-regression tests. Each task ends with running the dev server and manually confirming the page renders correctly in a browser. Do not skip the browser check — type-checking won't catch CSS regressions.

---

## File inventory (all changes)

- Modify: `gradebookcomponent/templates/gradebookcomponent/gradebook_home.html` (Task 1)
- Modify: `gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html` (Task 2)
- Modify: `gradebookcomponent/templates/gradebookcomponent/grading_queue.html` (Task 3)
- Modify: `gradebookcomponent/templates/gradebookcomponent/grade_submission.html` (Task 4)

No other files are touched. Views, URLs, and base templates remain untouched.

---

## Context view-by-view (do NOT change — these are the variables each template receives)

| Template | View function | Context |
|---|---|---|
| `gradebook_home.html` | `gradebookcomponent/views/instructor_grading.py:gradebook_home` | `tiles` — list of `{ "subject": Subject, "pending": int }` |
| `subject_gradebook.html` | `…:subject_gradebook` | `subject`, `term`, `activities` (list of Activity), `rows` (list of `{ "student": User, "cells": [{ "activity": Activity, "sa": StudentActivity or None }], "final": float }`) |
| `grading_queue.html` | `…:grading_queue` | `rows` — list of `{ "sa": StudentActivity, "quiz_type_name": str, "badge": "Needs grading" \| "Review auto-grade" }` |
| `grade_submission.html` | `…:grade_submission` | `sa` (StudentActivity, with `.student`, `.activity`, `.activity.subject`, `.activity.max_score`, `.total_score`, `.feedback`), `answers` (list of StudentQuestion with `.activity_question.question_text`, `.student_answer`, `.uploaded_file`), `has_next` (bool) |

> **Important:** the `grading_queue` badge value is `"Review auto-grade"` (not `"Flagged"`). The current template incorrectly assumes `"Flagged"`. Task 3 fixes this.

---

## Design tokens (reference)

These exist on `:root` in `templates/teacher_base.html`. Use them — do NOT hardcode their hex values.

```
--cream: #faf7f2;       --cream-2: #f3ede2;       --paper: #ffffff;
--forest: #1b4332;      --forest-2: #2d5a47;      --forest-light: #d9e4dd;
--gold: #b7925a;        --gold-soft: #e8d5b0;     --gold-bg: rgba(183,146,90,0.08);
--rose: #c08479;        --rose-soft: #f4e0dc;
--ink: #2d3142;         --ink-dim: #6c7080;       --ink-muted: #a0a4b8;
--border: rgba(45,49,66,0.08);                    --border-strong: rgba(45,49,66,0.14);
--shadow: 0 1px 2px rgba(45,49,66,0.03), 0 12px 32px -12px rgba(45,49,66,0.08);
--shadow-hover: 0 2px 4px rgba(45,49,66,0.04), 0 20px 48px -16px rgba(45,49,66,0.12);
--display: 'Fraunces', serif;
--body: 'Inter Tight', sans-serif;
--radius: 16px;         --radius-sm: 10px;
```

Named blocks available in `teacher_base.html`: `title`, `extra_css`, `content`. Use `extra_css` for `<style>` blocks.

---

# Task 1 — `gradebook_home.html`

**Files:**
- Modify: `gradebookcomponent/templates/gradebookcomponent/gradebook_home.html` (full rewrite)

**Goal:** A subject-tile landing page that mirrors the layout shape of `templates/teacher/subject_list.html`.

- [ ] **Step 1.1: Read the current template**

Run: `cat gradebookcomponent/templates/gradebookcomponent/gradebook_home.html`

Confirm the current structure: `{% extends "teacher_base.html" %}`, `{% block content %}` only, inline `<style>` after the markup. The view passes `tiles` (list of `{subject, pending}`).

- [ ] **Step 1.2: Replace the file with the new template**

Overwrite `gradebookcomponent/templates/gradebookcomponent/gradebook_home.html` with:

```django
{% extends "teacher_base.html" %}
{% load static %}

{% block title %}Gradebook{% endblock %}

{% block extra_css %}
<style>
  .courses-shell { padding: 8px 0; }

  .courses-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 28px;
  }
  .courses-title-block .page-title {
    font-family: var(--display);
    font-size: 32px;
    font-weight: 400;
    letter-spacing: -0.025em;
    color: var(--forest);
    line-height: 1.1;
    margin: 0 0 4px;
  }
  .courses-title-block .page-title em {
    font-style: italic;
    color: var(--gold);
    font-weight: 300;
  }
  .courses-title-block .page-sub {
    color: var(--ink-dim);
    font-size: 14px;
    font-family: var(--display);
    font-style: italic;
  }

  .courses-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 18px;
  }

  .t-course {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 24px 26px;
    box-shadow: var(--shadow);
    transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
    border-left: 4px solid var(--forest-2);
    display: flex;
    flex-direction: column;
    gap: 14px;
    text-decoration: none;
    color: inherit;
  }
  .t-course:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
    border-color: var(--gold-soft);
  }
  .t-course-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
  }
  .t-course-head-text { min-width: 0; }
  .t-course-name {
    font-family: var(--display);
    font-size: 19px;
    font-weight: 500;
    color: var(--forest);
    letter-spacing: -0.01em;
    line-height: 1.25;
    margin: 0;
  }
  .t-course-code {
    font-family: var(--display);
    font-style: italic;
    color: var(--ink-dim);
    font-size: 13px;
    margin-top: 2px;
  }

  .t-badge {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    font-family: var(--display);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    white-space: nowrap;
  }
  .t-badge--gold {
    background: var(--gold-bg);
    color: var(--gold);
    border: 1px solid var(--gold-soft);
  }
  .t-badge--forest {
    background: var(--forest-light);
    color: var(--forest);
    border: 1px solid var(--forest-light);
  }

  .t-course-meta {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    padding: 12px 0 0;
    border-top: 1px solid var(--border);
  }
  .t-course-meta-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ink-muted);
    font-weight: 600;
    margin-bottom: 2px;
  }
  .t-course-meta-value {
    font-family: var(--display);
    font-size: 14px;
    color: var(--forest);
    font-weight: 500;
  }

  .t-course-actions {
    display: flex;
    gap: 8px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
  }
  .t-course-actions a {
    flex: 1;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    background: var(--forest);
    color: var(--cream);
    font-family: var(--body);
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    text-align: center;
    border: 1px solid var(--forest);
    transition: background 0.15s;
  }
  .t-course-actions a:hover { background: var(--forest-2); }

  .t-empty {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 24px;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--ink-dim);
  }
  .t-empty .ico { font-size: 32px; margin-bottom: 12px; opacity: 0.4; color: var(--gold); }
  .t-empty .lead { font-size: 16px; margin-bottom: 6px; color: var(--forest); font-family: var(--display); }
  .t-empty .sub { font-size: 13px; }
</style>
{% endblock %}

{% block content %}
<div class="courses-shell">
  <div class="courses-header">
    <div class="courses-title-block">
      <h1 class="page-title">Grade<em>book</em></h1>
      <div class="page-sub">Subjects you teach &middot; tap a card to open its gradebook</div>
    </div>
  </div>

  <div class="courses-grid">
    {% for tile in tiles %}
      <a class="t-course" href="{% url 'gradebook_subject' tile.subject.id %}">
        <div class="t-course-head">
          <div class="t-course-head-text">
            <h3 class="t-course-name">{{ tile.subject.subject_name }}</h3>
            {% if tile.subject.subject_code %}
              <div class="t-course-code">{{ tile.subject.subject_code }}</div>
            {% endif %}
          </div>
          {% if tile.pending %}
            <span class="t-badge t-badge--gold">{{ tile.pending }} pending</span>
          {% else %}
            <span class="t-badge t-badge--forest">All graded</span>
          {% endif %}
        </div>

        <div class="t-course-meta">
          <div>
            <div class="t-course-meta-label">Needs grading</div>
            <div class="t-course-meta-value">{{ tile.pending|default:"0" }}</div>
          </div>
          <div>
            <div class="t-course-meta-label">Status</div>
            <div class="t-course-meta-value">
              {% if tile.pending %}{{ tile.pending }} pending{% else %}Up to date{% endif %}
            </div>
          </div>
        </div>

        <div class="t-course-actions">
          <a href="{% url 'gradebook_subject' tile.subject.id %}">
            <i class="fas fa-table"></i> Open gradebook
          </a>
        </div>
      </a>
    {% empty %}
      <div class="t-empty">
        <div class="ico"><i class="fas fa-book-open"></i></div>
        <div class="lead">No subjects assigned yet</div>
        <div class="sub">You aren't teaching any subjects this term.</div>
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 1.3: Start the dev server (in a new terminal)**

Run: `python manage.py runserver`

Expected: server starts on `http://127.0.0.1:8000/`. Leave it running for all subsequent tasks.

- [ ] **Step 1.4: Verify in browser**

Visit `http://127.0.0.1:8000/gradebook/` while logged in as a teacher.

Expected to see:
- Page title "Gradebook" (in browser tab) and an `H1` reading "Grade**book**" with "book" italic in gold.
- Subtitle line "Subjects you teach · tap a card to open its gradebook" in italic.
- Subject tiles in a responsive grid. Each tile has a 4px forest-green left border, white background, soft shadow, and lifts on hover.
- Each tile shows the subject name in large display font, the subject code in italic gold-grey beneath, a pending/all-graded badge in the top-right.
- Two-column meta row showing "Needs grading" count and "Status" (either "{n} pending" or "Up to date").
- A primary green "Open gradebook" button at the bottom of each tile.
- If you have no subjects assigned, you see the centered empty state with the open-book icon.

If the page renders unstyled or with hex colors that don't match the subject pages, you've broken the `extra_css` block — re-check Step 1.2.

- [ ] **Step 1.5: Compare with subject_list.html**

In another tab, open `http://127.0.0.1:8000/subject/` (or wherever `subject_list.html` is mounted).

Side-by-side, verify:
- Same fonts (Fraunces for headings, Inter Tight for body).
- Same card shape, same shadow, same hover lift.
- Same color palette (forest greens, gold accents, cream surface).

If anything looks visually inconsistent (e.g., gradebook tiles are smaller, different shadow, etc.), revisit the CSS in Step 1.2.

- [ ] **Step 1.6: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/gradebook_home.html
git commit -m "style(gradebook): align gradebook_home with subject design system"
```

---

# Task 2 — `subject_gradebook.html`

**Files:**
- Modify: `gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html` (full rewrite)

**Goal:** Wide score grid with sticky student column, restyled to use design tokens. Override `<details>` cell editor preserved (no JS added).

- [ ] **Step 2.1: Read the current template**

Run: `cat gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html`

Confirm context: `subject`, `term`, `activities`, `rows`. Each row has `student`, `cells` (each cell has `activity` and `sa`), `final`. Each `sa` (when present) has `total_score`, `is_editable`, `score_logs.exists`.

- [ ] **Step 2.2: Replace the file with the new template**

Overwrite `gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html` with:

```django
{% extends "teacher_base.html" %}
{% load static %}

{% block title %}{{ subject.subject_name }} · Gradebook{% endblock %}

{% block extra_css %}
<style>
  .gb-shell { padding: 8px 0; }

  .gb-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 22px;
  }
  .gb-header-left {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
  }
  .gb-back {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-strong);
    background: transparent;
    color: var(--ink-dim);
    font-family: var(--body);
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    align-self: flex-start;
    transition: border-color 0.15s, color 0.15s;
  }
  .gb-back:hover { border-color: var(--gold); color: var(--forest); }
  .gb-title {
    font-family: var(--display);
    font-size: 28px;
    font-weight: 400;
    letter-spacing: -0.025em;
    color: var(--forest);
    line-height: 1.15;
    margin: 0;
  }
  .gb-title em {
    font-style: italic;
    color: var(--gold);
    font-weight: 300;
  }
  .gb-csv {
    padding: 10px 18px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--forest);
    background: var(--forest);
    color: var(--cream);
    font-family: var(--body);
    font-weight: 600;
    font-size: 13px;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: background 0.15s;
  }
  .gb-csv:hover { background: var(--forest-2); }

  .t-table-wrap {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow-x: auto;
    overflow-y: visible;
  }

  .gb-grid {
    width: 100%;
    border-collapse: collapse;
    background: var(--paper);
    font-family: var(--body);
  }
  .gb-grid thead th {
    background: var(--cream-2);
    color: var(--forest);
    font-family: var(--display);
    font-size: 13px;
    font-weight: 500;
    text-align: left;
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 2;
    white-space: nowrap;
  }
  .gb-grid thead th .gb-max {
    display: block;
    color: var(--ink-muted);
    font-size: 11px;
    font-weight: 400;
    margin-top: 2px;
    font-style: italic;
  }
  .gb-grid tbody td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    color: var(--ink);
    vertical-align: top;
  }
  .gb-grid tbody tr:hover td { background: var(--cream); }
  .gb-grid tbody tr:last-child td { border-bottom: none; }

  .gb-sticky-left {
    position: sticky;
    left: 0;
    background: var(--paper);
    border-right: 1px solid var(--border);
    font-family: var(--display);
    font-weight: 500;
    color: var(--forest);
    z-index: 1;
  }
  .gb-grid tbody tr:hover .gb-sticky-left { background: var(--cream); }
  .gb-grid thead .gb-sticky-left { z-index: 3; background: var(--cream-2); }

  .gb-final {
    font-family: var(--display);
    font-weight: 600;
    color: var(--gold);
    border-left: 1px solid var(--border);
    text-align: right;
    white-space: nowrap;
    position: sticky;
    right: 0;
    background: var(--paper);
    z-index: 1;
  }
  .gb-grid tbody tr:hover .gb-final { background: var(--cream); }
  .gb-grid thead .gb-final { z-index: 3; background: var(--cream-2); }

  .gb-cell-graded { color: var(--forest); font-weight: 600; }
  .gb-cell-ungraded { background: var(--gold-bg); color: var(--gold); font-weight: 600; }
  .gb-cell-empty { color: var(--ink-muted); text-align: center; }

  .t-cell-edit {
    list-style: none;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    background: var(--cream);
    color: var(--forest);
    font-weight: 600;
    border: 1px solid transparent;
    transition: border-color 0.15s;
  }
  .t-cell-edit::-webkit-details-marker { display: none; }
  .t-cell-edit::marker { content: ''; }
  details[open] .t-cell-edit { border-color: var(--gold-soft); }
  details[open] .t-cell-edit::after {
    content: '\f303';
    font-family: 'Font Awesome 5 Free';
    font-weight: 900;
    font-size: 10px;
    color: var(--gold);
    margin-left: 4px;
  }
  .t-cell-edit-mark {
    color: var(--gold);
    font-size: 14px;
    line-height: 1;
    margin-left: 2px;
  }

  .gb-override-form {
    background: var(--paper);
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-hover);
    padding: 12px;
    margin-top: 6px;
    min-width: 220px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .gb-override-form label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-family: var(--display);
    font-size: 11px;
    color: var(--ink);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 500;
  }
  .gb-override-form input,
  .gb-override-form textarea {
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--paper);
    color: var(--ink);
    font-family: var(--body);
    font-size: 13px;
    text-transform: none;
    letter-spacing: normal;
    font-weight: 400;
    outline: none;
    transition: border-color 0.15s;
  }
  .gb-override-form input:focus,
  .gb-override-form textarea:focus { border-color: var(--gold); }
  .gb-override-form button {
    padding: 8px 12px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--forest);
    background: var(--forest);
    color: var(--cream);
    font-family: var(--body);
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .gb-override-form button:hover { background: var(--forest-2); }

  .gb-empty-row td {
    text-align: center;
    padding: 40px 24px;
    color: var(--ink-dim);
    font-family: var(--display);
    font-style: italic;
  }
</style>
{% endblock %}

{% block content %}
<div class="gb-shell">
  <div class="gb-header">
    <div class="gb-header-left">
      <a class="gb-back" href="{% url 'gradebook_home' %}">
        <i class="fas fa-arrow-left"></i> All subjects
      </a>
      <h1 class="gb-title">
        {{ subject.subject_name }}{% if term %}<em> · {{ term.term_name }}</em>{% endif %}
      </h1>
    </div>
    <a class="gb-csv" href="{% url 'gradebook_subject_csv' subject.id %}">
      <i class="fas fa-file-csv"></i> Export CSV
    </a>
  </div>

  <div class="t-table-wrap">
    <table class="gb-grid">
      <thead>
        <tr>
          <th class="gb-sticky-left">Student</th>
          {% for a in activities %}
            <th>
              {{ a.activity_name }}
              <span class="gb-max">out of {{ a.max_score }}</span>
            </th>
          {% endfor %}
          <th class="gb-final">Final</th>
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
          <tr>
            <td class="gb-sticky-left">{{ row.student.last_name }}, {{ row.student.first_name }}</td>
            {% for cell in row.cells %}
              <td class="{% if cell.sa %}{% if cell.sa.total_score > 0 %}gb-cell-graded{% else %}gb-cell-ungraded{% endif %}{% else %}gb-cell-empty{% endif %}">
                {% if cell.sa %}
                  {% if cell.sa.is_editable %}
                    <details>
                      <summary class="t-cell-edit">
                        {{ cell.sa.total_score }}{% if cell.sa.score_logs.exists %}<span class="t-cell-edit-mark">•</span>{% endif %}
                      </summary>
                      <form class="gb-override-form" method="post" action="{% url 'gradebook_override' cell.sa.id %}">
                        {% csrf_token %}
                        <label>
                          New score
                          <input name="new_score" type="number" min="0" max="{{ cell.activity.max_score }}" step="0.01" value="{{ cell.sa.total_score }}" required>
                        </label>
                        <label>
                          Reason
                          <textarea name="reason" rows="2" required placeholder="Why this override?"></textarea>
                        </label>
                        <button type="submit">Override</button>
                      </form>
                    </details>
                  {% else %}
                    {{ cell.sa.total_score }}
                  {% endif %}
                {% else %}&mdash;{% endif %}
              </td>
            {% endfor %}
            <td class="gb-final">{{ row.final }}%</td>
          </tr>
        {% empty %}
          <tr class="gb-empty-row"><td colspan="100">No students enrolled yet.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2.3: Verify in browser**

Visit `http://127.0.0.1:8000/gradebook/subject/<id>/` for a subject that has at least one enrolled student and one graded activity.

Expected to see:
- Outline back-button "← All subjects" at the top-left.
- Subject name as `H1` in display font, with the term name italic in gold (e.g., "English 7 *· Q1*").
- Primary "Export CSV" button on the right.
- A rounded-corner table card with a tinted header row using `--cream-2`. Header column names in display font with "out of {n}" in italic muted text underneath.
- Sticky student column on the left — scroll horizontally to confirm it stays put.
- "Final" column on the right with a small left-border separator and gold text. Scroll horizontally to confirm it stays anchored to the right edge of the visible viewport.
- Cell color states: graded cells show forest green text; ungraded cells (score 0) have a subtle gold tint; missing cells show a centered em-dash.
- Editable cells show a small chip-shaped clickable summary; clicking opens an inline form below, with a pencil glyph indicator.

- [ ] **Step 2.4: Test the override form**

Click any editable cell. The `<details>` should open showing:
- A "New score" input (number, range bound to the activity's max).
- A "Reason" textarea (required).
- A primary green "Override" button.

Submit a test override. The page should reload and the score should reflect the change. The override marker (`•` in gold) should appear next to the score, indicating prior override(s).

If the form submit fails with a 400, the view requires a non-empty reason — that's working as designed. Don't change view behavior.

- [ ] **Step 2.5: Test the empty state**

If you have a subject with no enrolled students, visit it. You should see "No students enrolled yet." centered, padded, italic display font, dim ink. If you don't have such a subject, skip this step.

- [ ] **Step 2.6: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html
git commit -m "style(gradebook): restyle subject_gradebook with design tokens and sticky table"
```

---

# Task 3 — `grading_queue.html`

**Files:**
- Modify: `gradebookcomponent/templates/gradebookcomponent/grading_queue.html` (full rewrite)

**Goal:** Submissions queue table styled with the shared kit. Fixes the existing badge bug (template assumed badge value `"Flagged"` but the view passes `"Review auto-grade"`).

- [ ] **Step 3.1: Read the current template**

Run: `cat gradebookcomponent/templates/gradebookcomponent/grading_queue.html`

Confirm context: `rows` — list of `{ "sa", "quiz_type_name", "badge" }`. The `badge` field will be either `"Needs grading"` or `"Review auto-grade"`.

- [ ] **Step 3.2: Replace the file with the new template**

Overwrite `gradebookcomponent/templates/gradebookcomponent/grading_queue.html` with:

```django
{% extends "teacher_base.html" %}
{% load static %}

{% block title %}Grading Queue{% endblock %}

{% block extra_css %}
<style>
  .gq-shell { padding: 8px 0; }

  .gq-header {
    margin-bottom: 22px;
  }
  .gq-title {
    font-family: var(--display);
    font-size: 32px;
    font-weight: 400;
    letter-spacing: -0.025em;
    color: var(--forest);
    line-height: 1.1;
    margin: 0 0 4px;
  }
  .gq-title em {
    font-style: italic;
    color: var(--gold);
    font-weight: 300;
  }
  .gq-sub {
    color: var(--ink-dim);
    font-size: 14px;
    font-family: var(--display);
    font-style: italic;
  }

  .gq-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 22px;
  }
  .gq-back {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-strong);
    background: transparent;
    color: var(--ink-dim);
    font-family: var(--body);
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    transition: border-color 0.15s, color 0.15s;
  }
  .gq-back:hover { border-color: var(--gold); color: var(--forest); }

  .t-table-wrap {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow-x: auto;
  }
  .gq-table {
    width: 100%;
    border-collapse: collapse;
    background: var(--paper);
    font-family: var(--body);
  }
  .gq-table thead th {
    background: var(--cream-2);
    color: var(--forest);
    font-family: var(--display);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    text-align: left;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .gq-table tbody td {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    color: var(--ink);
    vertical-align: middle;
  }
  .gq-table tbody tr:hover td { background: var(--cream); }
  .gq-table tbody tr:last-child td { border-bottom: none; }
  .gq-student {
    font-family: var(--display);
    font-weight: 500;
    color: var(--forest);
  }
  .gq-action-cell { text-align: right; white-space: nowrap; }

  .t-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    font-family: var(--display);
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    white-space: nowrap;
  }
  .t-badge--gold {
    background: var(--gold-bg);
    color: var(--gold);
    border: 1px solid var(--gold-soft);
  }
  .t-badge--rose {
    background: var(--rose-soft);
    color: var(--rose);
    border: 1px solid var(--rose-soft);
  }
  .t-badge--forest {
    background: var(--forest-light);
    color: var(--forest);
    border: 1px solid var(--forest-light);
  }

  .gq-grade-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    background: var(--forest);
    color: var(--cream);
    font-family: var(--body);
    font-weight: 600;
    font-size: 12px;
    text-decoration: none;
    border: 1px solid var(--forest);
    transition: background 0.15s;
  }
  .gq-grade-btn:hover { background: var(--forest-2); }

  .t-empty {
    text-align: center;
    padding: 60px 24px;
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--ink-dim);
  }
  .t-empty .ico { font-size: 32px; margin-bottom: 12px; opacity: 0.5; color: var(--forest); }
  .t-empty .lead { font-size: 16px; margin-bottom: 6px; color: var(--forest); font-family: var(--display); }
  .t-empty .sub { font-size: 13px; }
</style>
{% endblock %}

{% block content %}
<div class="gq-shell">
  <div class="gq-header">
    <h1 class="gq-title">Grading <em>Queue</em></h1>
    {% if rows %}
      <div class="gq-sub">{{ rows|length }} submission{{ rows|length|pluralize }} awaiting your attention</div>
    {% endif %}
  </div>

  <div class="gq-toolbar">
    <a class="gq-back" href="{% url 'gradebook_home' %}">
      <i class="fas fa-arrow-left"></i> Back to gradebook
    </a>
  </div>

  {% if not rows %}
    <div class="t-empty">
      <div class="ico"><i class="fas fa-check-circle"></i></div>
      <div class="lead">No submissions awaiting your attention</div>
      <div class="sub">You're caught up. New submissions will appear here.</div>
    </div>
  {% else %}
    <div class="t-table-wrap">
      <table class="gq-table">
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
              <td class="gq-student">{{ row.sa.student.last_name }}, {{ row.sa.student.first_name }}</td>
              <td>{{ row.sa.activity.subject.subject_name }}</td>
              <td>{{ row.sa.activity.activity_name }}</td>
              <td>{{ row.quiz_type_name }}</td>
              <td>
                {% if row.badge == 'Needs grading' %}
                  <span class="t-badge t-badge--gold">{{ row.badge }}</span>
                {% else %}
                  <span class="t-badge t-badge--rose">{{ row.badge }}</span>
                {% endif %}
              </td>
              <td class="gq-action-cell">
                <a class="gq-grade-btn" href="{% url 'gradebook_grade' row.sa.id %}">
                  Grade <i class="fas fa-arrow-right"></i>
                </a>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3.3: Verify in browser (with submissions)**

Visit `http://127.0.0.1:8000/gradebook/queue/` while there are pending submissions.

Expected to see:
- `H1` "Grading **Queue**" with "Queue" italic gold.
- Subtitle line "{n} submission(s) awaiting your attention" in italic display font.
- Outline "← Back to gradebook" button beneath the heading.
- Table with the kit's standard look: cream-tinted head row, uppercase display-font column labels, hover row tinting.
- Student column in display font / forest.
- Status badges: gold for "Needs grading", rose for "Review auto-grade".
- Right-aligned compact "Grade →" button per row.

- [ ] **Step 3.4: Verify in browser (empty queue)**

If your queue is empty (or temporarily empty), the page should show:
- The header with `H1` only (no subtitle line).
- Centered `.t-empty` block with a green check-circle icon, lead "No submissions awaiting your attention", sub line "You're caught up. New submissions will appear here."

If you need to test this and don't have an empty queue, you can either grade everything in the queue first or temporarily skip — but verify the page at least renders without error in both states.

- [ ] **Step 3.5: Click a "Grade →" button**

Should navigate to the grade-submission page for that row. If it 404s or errors, the URL name `gradebook_grade` was misspelled or the row's `sa.id` wasn't accessible in the template. Re-check Step 3.2.

- [ ] **Step 3.6: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/grading_queue.html
git commit -m "style(gradebook): restyle grading_queue and fix Review auto-grade badge"
```

---

# Task 4 — `grade_submission.html`

**Files:**
- Modify: `gradebookcomponent/templates/gradebookcomponent/grade_submission.html` (full rewrite)

**Goal:** Two-column grading workspace (student answer left, grade form right), styled with the shared kit. Right panel sticky on tall pages.

- [ ] **Step 4.1: Read the current template**

Run: `cat gradebookcomponent/templates/gradebookcomponent/grade_submission.html`

Confirm context: `sa`, `answers`, `has_next`. The `sa` exposes `.student.first_name`, `.student.last_name`, `.activity.activity_name`, `.activity.subject.subject_name`, `.activity.max_score`, `.total_score`, `.feedback`. Each `answer` exposes `.activity_question.question_text`, `.student_answer`, `.uploaded_file`.

- [ ] **Step 4.2: Replace the file with the new template**

Overwrite `gradebookcomponent/templates/gradebookcomponent/grade_submission.html` with:

```django
{% extends "teacher_base.html" %}
{% load static %}

{% block title %}Grade · {{ sa.activity.activity_name }}{% endblock %}

{% block extra_css %}
<style>
  .gs-shell { padding: 8px 0; }

  .gs-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 22px;
  }
  .gs-back {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-strong);
    background: transparent;
    color: var(--ink-dim);
    font-family: var(--body);
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    align-self: flex-start;
    transition: border-color 0.15s, color 0.15s;
  }
  .gs-back:hover { border-color: var(--gold); color: var(--forest); }
  .gs-title {
    font-family: var(--display);
    font-size: 28px;
    font-weight: 400;
    letter-spacing: -0.025em;
    color: var(--forest);
    line-height: 1.15;
    margin: 0;
  }
  .gs-title em {
    font-style: italic;
    color: var(--gold);
    font-weight: 300;
  }
  .gs-sub {
    color: var(--ink-dim);
    font-size: 14px;
    font-family: var(--display);
    font-style: italic;
  }

  .gs-split {
    display: grid;
    grid-template-columns: 1.5fr 1fr;
    gap: 28px;
    align-items: start;
  }
  @media (max-width: 960px) {
    .gs-split { grid-template-columns: 1fr; }
  }

  .t-panel {
    background: var(--paper);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 28px 32px;
  }
  .t-panel--answer { border-left: 4px solid var(--forest-2); }
  .t-panel--grade {
    border-left: 4px solid var(--gold);
    position: sticky;
    top: 24px;
  }
  @media (max-width: 960px) {
    .t-panel--grade { position: static; }
  }
  .t-panel h2 {
    font-family: var(--display);
    font-size: 22px;
    font-weight: 500;
    color: var(--forest);
    margin: 0 0 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  .gs-answer-block {
    padding: 16px 0;
    border-bottom: 1px solid var(--border);
  }
  .gs-answer-block:last-child { border-bottom: none; padding-bottom: 0; }
  .gs-answer-block:first-child { padding-top: 0; }
  .gs-q-label {
    font-family: var(--display);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--ink-muted);
    font-weight: 600;
    margin-bottom: 6px;
  }
  .gs-q-text {
    font-family: var(--display);
    font-size: 16px;
    color: var(--ink);
    margin: 0 0 12px;
    line-height: 1.4;
  }
  .gs-a-text {
    font-family: var(--body);
    font-size: 14px;
    color: var(--ink);
    line-height: 1.6;
  }
  .gs-attachment {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    padding: 6px 12px;
    border-radius: var(--radius-sm);
    background: var(--cream);
    color: var(--forest);
    font-family: var(--body);
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    border: 1px solid transparent;
    transition: border-color 0.15s;
  }
  .gs-attachment:hover { border-color: var(--gold-soft); }

  .gs-form { display: flex; flex-direction: column; gap: 18px; }
  .gs-field { display: flex; flex-direction: column; gap: 6px; }
  .gs-label-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 8px;
  }
  .gs-label {
    font-family: var(--display);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--ink-muted);
    font-weight: 600;
  }
  .gs-helper {
    font-family: var(--body);
    font-size: 12px;
    color: var(--ink-dim);
  }
  .gs-form input[type="number"],
  .gs-form textarea {
    padding: 12px 14px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--paper);
    color: var(--ink);
    font-family: var(--body);
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
    width: 100%;
    box-sizing: border-box;
  }
  .gs-form input[type="number"] {
    font-family: var(--display);
    font-size: 18px;
    color: var(--forest);
    font-weight: 500;
  }
  .gs-form textarea { min-height: 160px; resize: vertical; line-height: 1.5; }
  .gs-form input[type="number"]:focus,
  .gs-form textarea:focus { border-color: var(--gold); }

  .gs-btn-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }
  .gs-btn {
    flex: 1 1 140px;
    padding: 10px 20px;
    border-radius: var(--radius-sm);
    font-family: var(--body);
    font-weight: 600;
    font-size: 13px;
    cursor: pointer;
    text-align: center;
    transition: background 0.15s, border-color 0.15s;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .gs-btn--primary {
    background: var(--forest);
    color: var(--cream);
    border: 1px solid var(--forest);
  }
  .gs-btn--primary:hover { background: var(--forest-2); }
  .gs-btn--secondary {
    background: transparent;
    color: var(--gold);
    border: 1px solid var(--gold-soft);
  }
  .gs-btn--secondary:hover { background: var(--gold-bg); }
  @media (max-width: 480px) {
    .gs-btn { flex: 1 1 100%; }
  }
</style>
{% endblock %}

{% block content %}
<div class="gs-shell">
  <div class="gs-header">
    <a class="gs-back" href="{% url 'gradebook_queue' %}">
      <i class="fas fa-arrow-left"></i> Back to queue
    </a>
    <h1 class="gs-title">{{ sa.student.last_name }}, <em>{{ sa.student.first_name }}</em></h1>
    <div class="gs-sub">
      {{ sa.activity.activity_name }} &middot; {{ sa.activity.subject.subject_name }} &mdash; out of {{ sa.activity.max_score }}
    </div>
  </div>

  <div class="gs-split">
    <section class="t-panel t-panel--answer">
      <h2>Student's Answer</h2>
      {% for a in answers %}
        <div class="gs-answer-block">
          <div class="gs-q-label">Question</div>
          <p class="gs-q-text">{{ a.activity_question.question_text }}</p>
          {% if a.student_answer %}
            <div class="gs-a-text">{{ a.student_answer|linebreaks }}</div>
          {% endif %}
          {% if a.uploaded_file %}
            <a class="gs-attachment" href="{{ a.uploaded_file.url }}" target="_blank" rel="noopener">
              <i class="fas fa-paperclip"></i> {{ a.uploaded_file.name }}
            </a>
          {% endif %}
        </div>
      {% empty %}
        <div class="gs-answer-block">
          <div class="gs-a-text" style="color: var(--ink-dim); font-style: italic;">No answer recorded.</div>
        </div>
      {% endfor %}
    </section>

    <section class="t-panel t-panel--grade">
      <h2>Grade</h2>
      <form class="gs-form" method="post">
        {% csrf_token %}
        <div class="gs-field">
          <div class="gs-label-row">
            <span class="gs-label">Score</span>
            <span class="gs-helper">out of {{ sa.activity.max_score }}</span>
          </div>
          <input name="score" type="number" min="0" max="{{ sa.activity.max_score }}" step="0.01" value="{{ sa.total_score }}" required>
        </div>
        <div class="gs-field">
          <span class="gs-label">Feedback</span>
          <textarea name="feedback" rows="6">{{ sa.feedback }}</textarea>
        </div>
        <div class="gs-btn-row">
          <button class="gs-btn gs-btn--primary" type="submit">
            <i class="fas fa-save"></i> Save
          </button>
          {% if has_next %}
            <button class="gs-btn gs-btn--secondary" type="submit" name="save_and_next" value="1">
              Save &amp; Next <i class="fas fa-arrow-right"></i>
            </button>
          {% endif %}
        </div>
      </form>
    </section>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4.3: Verify in browser**

Visit `http://127.0.0.1:8000/gradebook/grade/<student_activity_id>/` for any submission in the queue (use a "Grade →" link from `/gradebook/queue/`).

Expected to see:
- Outline "← Back to queue" button at the top.
- `H1` "{LastName}, *{FirstName}*" with first name italic gold.
- Subtitle italic display: "{activity_name} · {subject_name} — out of {max_score}".
- Two columns: student answer (wider, left, forest left-border accent) and grade form (narrower, right, gold left-border accent).
- Each answer block: "QUESTION" label uppercase muted, question text in display font, answer text in body font with tighter line-height.
- Uploaded file shows as a small chip with a paperclip icon, hover gives a gold border.
- Right panel: large display-font score input and a tall feedback textarea. "out of N" helper text right-aligned next to the SCORE label.
- Two buttons: primary green "Save", and an outline gold "Save & Next →" (only when `has_next`).

- [ ] **Step 4.4: Test sticky behavior**

Find a submission with a long answer (or temporarily resize the browser to make the answer scrollable). Scroll the page — the right Grade panel should stay anchored near the top of the viewport while the left answer panel scrolls.

If sticky doesn't work, check that the parent `.gs-split` doesn't have `overflow: hidden` and that the viewport is wider than 960px (sticky is disabled on narrow screens by media query).

- [ ] **Step 4.5: Test the Save and Save & Next flows**

- Edit the score, click **Save**. Page should reload showing the updated score. Verify by going back to the queue and re-opening the same submission.
- If `has_next` is true, click **Save & Next →**. Page should redirect to the next pending submission (or back to the queue if you just graded the last one).
- On a narrow viewport (~400px), buttons should stack vertically.

- [ ] **Step 4.6: Test the empty-answers state**

If you have a submission with no `StudentQuestion` records, the left panel should show "No answer recorded." in dim italic. (If you can't easily produce this state, skip — the template still works for the common case.)

- [ ] **Step 4.7: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/grade_submission.html
git commit -m "style(gradebook): restyle grade_submission with split-panel design"
```

---

# Task 5 — Cross-template visual walk

**Goal:** Confirm the four pages feel like a single unified flow, and look continuous with `subject_list.html`.

- [ ] **Step 5.1: Walk the gradebook flow**

In a fresh browser tab, navigate this sequence:

1. `/gradebook/` — gradebook home (Task 1).
2. Click any tile → `/gradebook/subject/<id>/` (Task 2).
3. Click "← All subjects" back to home, then visit `/gradebook/queue/` (Task 3).
4. Click any "Grade →" → `/gradebook/grade/<id>/` (Task 4).
5. Click "← Back to queue".

While walking, watch for visual discontinuities — anything where the surface, font, color, or spacing feels different from the others.

- [ ] **Step 5.2: Compare with subject pages**

Open `/subject/` (the subject list page that uses `templates/teacher/subject_list.html`) and compare:
- Heading sizes and weights match.
- Card shadow, radius, and hover lift match (subject tiles vs. gradebook tiles).
- Buttons use the same forest/cream primary and outline styles.
- Empty states have the same shape.

If a gradebook page has a noticeably different shadow weight, font size, or color, edit the corresponding template and re-verify. Keep the kit values consistent: `var(--shadow)`, `var(--radius)`, `var(--display)` 32px for top-level page titles, etc.

- [ ] **Step 5.3: Check responsive breakpoints**

Resize the browser narrow (~480px) and verify:
- `gradebook_home` tiles still render at one column.
- `subject_gradebook` table can be scrolled horizontally inside its rounded card; sticky student column still works.
- `grading_queue` table is horizontally scrollable.
- `grade_submission` collapses to single column; sticky grade panel becomes static; buttons stack.

- [ ] **Step 5.4: Quick accessibility sanity check**

- Keyboard-tab through `gradebook_home` — each tile is reachable and shows a focus ring.
- On `subject_gradebook`, the editable cell summaries are reachable via Tab and toggle on Enter (native `<details>` behavior).
- The "Grade →" buttons in the queue are reachable.
- Status badges are not color-only — each carries its text label.

- [ ] **Step 5.5: Final commit (only if any tweaks needed)**

If Step 5.1 or 5.2 surfaced fixes, commit them as:

```bash
git add gradebookcomponent/templates/gradebookcomponent/
git commit -m "style(gradebook): cross-template polish after visual walk"
```

If no tweaks were needed, skip the commit — Tasks 1–4 already covered everything.

---

## Done definition

- All four templates render without errors.
- Each page visually consumes the design tokens (no hardcoded `#1b4332`/`#b7925a`/`#faf7f2`/`#c08479` hex values left in the four templates).
- The override `<details>` form on `subject_gradebook` still works without any new JavaScript.
- The `grading_queue` page correctly styles both `Needs grading` (gold) and `Review auto-grade` (rose) badges.
- Subject pages and gradebook pages feel visually continuous when navigated back-to-back.
- No changes to any `.py` file, `urls.py`, `teacher_base.html`, or any template outside the four listed.

---

## Reference: tokens & shapes used (cheat sheet)

**Page header:** display 32px / `--forest`, `<em>` italic in `--gold`. Subtitle display italic 14px `--ink-dim`.
**Outline back-button:** transparent bg, `--ink-dim` text, `--border-strong` border, `--radius-sm`, hover border `--gold` and color `--forest`.
**Primary button:** `--forest` bg, `--cream` text, `--radius-sm`, hover `--forest-2`.
**Card / panel:** `--paper` bg, `1px solid --border`, `--radius` (16px), `--shadow`. Optional 4px left border `--forest-2` (info) or `--gold` (action).
**Table head:** `--cream-2` bg, display 11px uppercase `--forest`, sticky.
**Table row hover:** `--cream`.
**Badge gold:** `--gold-bg` / `--gold` / `--gold-soft` border.
**Badge rose:** `--rose-soft` / `--rose`.
**Badge forest:** `--forest-light` / `--forest`.
