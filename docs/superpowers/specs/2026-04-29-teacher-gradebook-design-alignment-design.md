# Teacher Gradebook — Design Alignment with Subject Pages

**Date:** 2026-04-29
**Scope:** Visual redesign only. No view, URL, or model changes.
**Affected app:** `gradebookcomponent`
**Affected templates (4):**

- `gradebookcomponent/templates/gradebookcomponent/gradebook_home.html`
- `gradebookcomponent/templates/gradebookcomponent/subject_gradebook.html`
- `gradebookcomponent/templates/gradebookcomponent/grading_queue.html`
- `gradebookcomponent/templates/gradebookcomponent/grade_submission.html`

## Goal

Bring the four daily-use teacher gradebook templates in line with the modern design system already used by `templates/teacher/subject_list.html` and the rest of the teacher subject area.

The gradebook templates currently use minimal CSS with hardcoded hex colors. The subject templates use design-system tokens defined in `templates/teacher_base.html` (`--forest`, `--gold`, `--cream`, `--paper`, `--ink`, `--radius`, etc.) and a shared visual language of rounded paper cards, italic display-font accents, and warm-neutral surfaces. After this change, a teacher navigating between Subjects and Gradebook should not perceive a stylistic gap.

This spec covers only the four templates listed above. The deeper gradebook admin pages under `gradebook/`, `subgradebook/`, `termbook/`, `transmutation/`, `activityGrade/`, and `studentProgress/` rely on `_legacy_stack.html` (Bootstrap 5, jQuery, DataTables, Select2, SweetAlert2) and provide live functional behavior. They are explicitly out of scope and will be addressed in a separate effort.

## Non-Goals

- No changes to Python views, URL routes, query logic, or model fields.
- No new dependencies. No JavaScript framework. No CSS preprocessor.
- No DataTables, Select2, jQuery, or Bootstrap added.
- No column-sort, advanced filtering, or pagination beyond what each template currently has.
- No modal-based override editor — the existing `<details>` pattern stays.
- No copy changes beyond the empty-state and subtitle text noted below.

## Approach

Follow the exact pattern used by `templates/teacher/subject_list.html`: each template inlines its styles in `{% block extra_css %}<style>…</style>{% endblock %}` and consumes the design tokens defined on `:root` in `teacher_base.html`. No shared static CSS file is added — that would diverge from the pattern we're trying to match for only four templates.

## Design tokens (consumed, not redefined)

These are already defined in `templates/teacher_base.html`. All hardcoded hex values in the four templates are replaced with token references.

| Use | Token |
|---|---|
| Page card / panel background | `var(--paper)` (`#ffffff`) |
| Soft cream surface (chips, hover rows, head row) | `var(--cream)` / `var(--cream-2)` |
| Primary brand / dark text | `var(--forest)` (with `--forest-2` for hover, `--forest-light` for tinted fills) |
| Accent / gold | `var(--gold)`, `--gold-soft`, `--gold-bg` |
| Warning / at-risk | `var(--rose)`, `--rose-soft` |
| Body / dim / muted text | `var(--ink)` / `--ink-dim` / `--ink-muted` |
| Borders | `var(--border)` / `--border-strong` |
| Shadow | `var(--shadow)` (resting) / `--shadow-hover` |
| Radius | `var(--radius)` (16px) / `--radius-sm` (10px) |
| Fonts | `var(--display)` (Fraunces) for headings & emphasis; `var(--body)` (Inter Tight) for everything else |

## Shared visual patterns (the "kit")

The four templates use a small set of recurring shapes. Class names mirror the conventions in `subject_list.html` so the patterns are recognizable across both apps.

### Page header

- Title: `<h1 class="page-title">Word <em>Word</em></h1>`. The `<em>` portion is italic in `var(--gold)`. Display font, 32px, weight 400, `letter-spacing: -0.025em`, color `var(--forest)`.
- Subtitle: `<div class="page-sub">…</div>`. `var(--display)` italic, 14px, `var(--ink-dim)`. Used for term/semester context or contextual counts.
- Title block sits in a `.courses-header` flex row that allows right-side actions to sit alongside it.

### Toolbar / back-link row

- `.courses-toolbar` flex row, `gap: 10px`, `flex-wrap: wrap`.
- `.toolbar-btn.outline` for back-style links: transparent background, `var(--ink-dim)` text, `var(--border-strong)` border, `var(--radius-sm)`, padding `10px 18px`.
- Primary action buttons reuse `.courses-toolbar button` style: `var(--forest)` bg, `var(--cream)` text, hover `var(--forest-2)`.

### Card / panel

- `.t-panel` (new): `var(--paper)` bg, `1px solid var(--border)`, `var(--radius)`, `var(--shadow)`, padding `28px 32px`. Hover-emphasized cards may add `4px solid var(--forest-2)` (or `--gold` for action panels) as a left border.
- Tile-style cards reuse `.t-course` directly from `subject_list.html`.

### Table wrapper

- `.t-table-wrap` (new): `var(--paper)` bg, `1px solid var(--border)`, `var(--radius)`, `var(--shadow)`, `overflow-x: auto`. Radius lives on the wrapper so sticky cells inside the table don't have to fight rounded corners.
- `<thead>` cells: `var(--cream-2)` bg, `var(--forest)` text, `var(--display)` font, 11px uppercase, `letter-spacing: 0.08em`, padding `12px 14px`, sticky top.
- `<tbody>` rows: `1px solid var(--border)` separator, hover row → `var(--cream)`.

### Badge

- `.t-badge` base: padding `4px 10px`, `var(--radius-sm)`, `var(--display)` font, 11px, uppercase, `letter-spacing: 0.06em`.
- Modifiers: `.t-badge--gold` (gold-bg / gold text / gold-soft border), `.t-badge--rose` (rose-soft / rose), `.t-badge--forest` (forest-light / forest).

### Empty state

- `.t-empty` from `subject_list.html`: centered, `var(--paper)`, `1px solid var(--border)`, `var(--radius)`, padding `60px 24px`. Icon (`.ico`), lead line (`.lead`, display font, `--forest`), sub line (`.sub`, body font, `--ink-dim`).

## Per-template designs

### 1. `gradebook_home.html`

Direct mirror of `subject_list.html` since both are "list of teacher's subjects."

- **Header:** `<h1 class="page-title">Grade<em>book</em></h1>`. Subtitle shows the active term/semester when present, falling back to the academic year (same logic as subject_list.html).
- **Toolbar:** Omitted on first pass — the current view does not provide search/filter context. Adding it is out of scope.
- **Grid:** `.courses-grid` (auto-fill, `minmax(320px, 1fr)`, gap 18px).
- **Tile (`.t-course`):**
  - `.t-course-name` → `subject.subject_name`.
  - `.t-course-code` → `subject.subject_code`.
  - `.t-course-meta` (2-col): "Pending" count (from `tile.pending`) on the left and "Status" on the right showing "Up to date" / "{n} pending" — both derived from `tile.pending`. Only data the view already provides — no new query work. If the view later surfaces additional context (term, last updated), it can drop into the existing cells without restructuring.
  - Status badge: `.t-badge--gold` "{n} need grading" when `tile.pending > 0`, else `.t-badge--forest` "All graded". Sits in the title row to the right of `.t-course-name`.
  - `.t-course-actions`: single primary button "Open gradebook →" pointing at the existing `gradebook_subject` URL. Secondary outline action only added if the queue route supports a per-subject filter — otherwise omitted (YAGNI).
- **Empty state:** `.t-empty` with book-open icon, lead "No subjects assigned yet", sub "You aren't teaching any subjects this term."

### 2. `subject_gradebook.html`

Wide horizontally-scrolling score grid with a sticky student column and inline `<details>` override editor. Structure preserved; only styling changes.

- **Header strip:**
  - Left: `.toolbar-btn.outline` "← All subjects" linking to `gradebook_home`.
  - Center: `<h1 class="page-title">{{ subject.subject_name }}<em>{% if term %} · {{ term.term_name }}{% endif %}</em></h1>`. Term portion italic in `--gold`.
  - Right: primary "Export CSV" button styled per the toolbar primary-button rules.

- **Grid wrapper:** Replace `.grid-wrap` with `.t-table-wrap`. Radius lives on the wrapper. Table inside has `border-collapse: collapse`, `width: 100%`, no own border.

- **Table head:** Activity columns show name in `var(--display)` 13px / `var(--forest)`; the `(max_score)` is on a second line in `var(--ink-muted)` 11px regular weight.

- **Table body:**
  - Sticky-left student cell — class `.gb-sticky-left`. `var(--paper)` background, `1px solid var(--border)` right border, `var(--display)` font 14px / `var(--forest)`, weight 500, padding `10px 14px`. Sticky-left positioning preserved.
  - "Final" column right-side: bold, `var(--gold)`, `var(--display)` font 14px, similar right-of-table sticky treatment with a `1px solid var(--border)` left border.
  - Cell states (semantics preserved, look modernized):
    - `.graded` → `var(--forest)` text, weight 600, no fill.
    - `.ungraded` → `var(--gold-bg)` background, `var(--gold)` text.
    - `.not-attempted` → `var(--ink-muted)` text, em-dash centered, no fill.
  - Override marker (was `*`) → small superscript dot in `var(--gold)`, generated via CSS `::after` rather than inline character, so the cell stays clean.

- **Override `<details>` editor:**
  - Summary cell rendered as a clickable chip — class `.t-cell-edit`: `var(--cream)` bg, `var(--forest)` text, `var(--radius-sm)`, padding `4px 10px`, hover `1px solid var(--gold-soft)`. When `<details open>`, append a small pencil glyph via `::after`.
  - When open, the form panels in directly under the summary (still inside the cell — does not float):
    - `var(--paper)` bg, `1px solid var(--border-strong)`, `var(--radius-sm)`, `var(--shadow-hover)`, padding `12px`, min-width `220px`.
    - Labels in `var(--display)` 12px `var(--ink)`. Inputs match toolbar inputs (radius `--radius-sm`, border `--border`, focus border `--gold`).
    - Submit button: full-width primary forest, padding `8px 12px`, `var(--radius-sm)`, weight 600.
  - No JS added — native `<details>` behavior preserved. Closing happens by re-clicking the summary, as today.

- **Empty grid (no students enrolled):** the existing single `<tr>` becomes a styled empty-state row with padding `40px 24px`, `var(--ink-dim)`, italic `var(--display)`, centered. `colspan="100"` retained.

### 3. `grading_queue.html`

Flat list of submissions awaiting attention. Smallest delta of the four.

- **Header:** `<h1 class="page-title">Grading <em>Queue</em></h1>`. Subtitle line: count of pending rows in `var(--display)` italic, e.g. *"3 submissions awaiting your attention"*. Suppressed when `rows` is empty (the empty state takes over).

- **Toolbar row:** `.toolbar-btn.outline` "← Back to gradebook" linking to `gradebook_home` on the left. Right side reserved for future filters but no controls added now.

- **Table:** wrapped in `.t-table-wrap`. Columns unchanged: Student, Subject, Activity, Type, Status, Action. Apply shared head/body styling rules from the kit.
  - Student cell: `var(--display)` font 14px / `var(--forest)` weight 500.
  - Subject / Activity / Type cells: `var(--body)` font 14px / `var(--ink)`.

- **Status badges:**
  - "Needs grading" → `.t-badge--gold`.
  - "Flagged" → `.t-badge--rose`.
  - "Graded" reserved as `.t-badge--forest` if the view ever surfaces it.

- **Per-row "Grade →" action:** primary forest button, compact — padding `6px 12px`, font 12px, `var(--radius-sm)`, weight 600. Trailing `→` glyph inside the label. Hover `var(--forest-2)`.

- **Empty state:** replace the bare `<p class="empty">` with `.t-empty` — checkmark icon, lead "No submissions awaiting your attention", sub "You're caught up. New submissions will appear here." (Neutral copy chosen over playful "Inbox zero" to match the existing tone of `subject_list.html`.)

### 4. `grade_submission.html`

Two-column workspace: student answer (left, wider) + grade form (right). Layout preserved; surfaces and typography upgraded.

- **Header strip:**
  - Left: `.toolbar-btn.outline` "← Back to queue" linking to `gradebook_queue`.
  - Center: `<h1 class="page-title">{{ sa.student.last_name }}, <em>{{ sa.student.first_name }}</em></h1>`. First name italic in `--gold`. (Uses the same `sa` context object the existing template references.)
  - Subtitle: `var(--display)` italic, `{{ sa.activity.activity_name }} · {{ sa.activity.subject.subject_name }} — out of {{ sa.activity.max_score }}`.

- **Layout:** existing CSS grid `1.5fr 1fr` with `gap: 2rem`. Collapse to single column at `max-width: 960px`.

- **Left panel — "Student's Answer":**
  - `.t-panel` with **left border `4px solid var(--forest-2)`**.
  - Section heading `<h2>` in `var(--display)` 22px / `var(--forest)`, with `1px solid var(--border)` bottom rule, padding-bottom 12px, margin-bottom 16px.
  - Per `.answer-block`:
    - Question line — small uppercase `var(--ink-muted)` label "QUESTION" (10px, letter-spacing 0.1em), then question text in `var(--display)` 16px / `var(--ink)`.
    - Answer text — `var(--body)` 14px / `var(--ink)`, line-height 1.6.
    - Uploaded file — link styled as an attachment chip: `var(--cream)` bg, `var(--forest)` text, paperclip glyph, `var(--radius-sm)`, padding `6px 12px`, hover `1px solid var(--gold-soft)`.
    - Block separator: `1px solid var(--border)`, padding `16px 0`.

- **Right panel — "Grade":**
  - `.t-panel` with **left border `4px solid var(--gold)`** to mark it as the action panel. `position: sticky; top: 24px;` so it stays in view on long-answer pages. Sticky disabled when the layout collapses to single-column.
  - Section heading matches left panel.
  - **Score field:**
    - Label: `var(--display)` 12px uppercase `var(--ink-muted)` "SCORE", with helper text "out of {{ sa.activity.max_score }}" in `var(--ink-dim)` 12px, right-aligned next to the label.
    - Input: number input, font 18px `var(--display)` / `var(--forest)`, padding `12px 14px`, `var(--radius-sm)`, border `var(--border)`, focus border `var(--gold)`.
  - **Feedback field:**
    - Label same pattern, "FEEDBACK".
    - Textarea: `var(--body)` 14px, padding `12px 14px`, `var(--radius-sm)`, min-height 160px. Same border/focus colors as inputs.
  - **Button row:**
    - Primary "Save" button: `var(--forest)` bg / `var(--cream)` text / `var(--radius-sm)` / padding `10px 20px` / `flex: 1`. Hover `var(--forest-2)`.
    - Secondary "Save & Next →" button (rendered only when `has_next`): outline style — transparent bg, `var(--gold)` text, `1px solid var(--gold-soft)` border. Hover fills with `var(--gold-bg)`. Same padding/radius. `flex: 1`.
    - Buttons stack vertically on screens narrower than 480px.

- **No JS added.** Native form submission, native textarea resize, native `position: sticky`.

## Responsive behavior

- All grids use `auto-fill` minmax, so they reflow naturally.
- `subject_gradebook.html` table relies on horizontal scroll inside `.t-table-wrap` on narrow screens — no column hiding.
- `grade_submission.html` collapses left/right panels at `max-width: 960px`.
- Sticky positioning (table head, sticky-left student column, right grade panel) all degrade gracefully on iOS and old Edge.

## Accessibility

- Color-only status conveyance avoided: status badges combine color with text labels.
- Focus rings retained: inputs and buttons rely on browser default focus + an additional `border-color: var(--gold)` cue.
- All buttons keep semantic `<button>` / `<a>` markup. No purely visual `<div>` clickables added.
- Sticky header cells in `subject_gradebook.html` have sufficient contrast (`--forest` text on `--cream-2` background).

## Verification plan

After implementation, manually verify in a real browser (the project runs Django; `python manage.py runserver` against the dev DB):

1. **`gradebook_home`**
   - With ≥1 subjects assigned: tiles render in the grid, badge color matches pending count, hover lifts the card.
   - With zero subjects: `.t-empty` shows correct icon, lead, sub copy.
2. **`subject_gradebook` (per subject)**
   - With enrolled students + activities: header centers term name in italic gold; sticky-left student column stays visible while horizontally scrolling; "Final" stays sticky on the right; each cell state (graded/ungraded/not-attempted) renders the correct treatment.
   - Click an editable cell: `<details>` opens the inline form; submitting routes to `gradebook_override` and persists. Override marker appears for previously-overridden cells.
   - With zero students: empty-state row renders.
   - "Export CSV" button still routes to `gradebook_subject_csv`.
3. **`grading_queue`**
   - With pending rows: badges in correct colors; "Grade →" buttons route to `gradebook_grade`; row hover tints `--cream`.
   - With zero rows: `.t-empty` shows correct icon/lead/sub.
4. **`grade_submission`**
   - With multiple `<answer_block>`s: question/answer/file-link layout reads cleanly; uploaded file chip renders.
   - Right panel sticky behavior on a tall answer.
   - Submit "Save" persists score+feedback; "Save & Next →" appears and routes only when `has_next`; both buttons stack on a narrow viewport.
5. **Cross-template:** Navigate Subjects → Gradebook → Subject Gradebook → Grade Submission. The visual transition should feel continuous — same fonts, same surfaces, same radius, same accent rhythm.

No automated tests are added — these are presentation-only template changes and the project does not have visual regression coverage.

## Risks

- **Sticky-left + sticky-right on the same table** (`subject_gradebook.html`) can fight overflow boundaries. Mitigation: keep `border-radius` on the `.t-table-wrap`, not on the table; verify on Safari and Firefox.
- **`<details>` styling cross-browser:** the `summary::-webkit-details-marker { display: none }` rule already used in the current template stays. Add `summary::marker { content: '' }` for Firefox.
- **Sticky right panel** (`grade_submission.html`) on iOS Safari can be flaky in nested scroll contexts. If sticky misbehaves, fall back to non-sticky.

## File inventory & change shape

For each of the four templates, the diff structure is:

1. Add `{% block extra_css %}<style>…</style>{% endblock %}` (or replace existing inline `<style>` placement so it lives inside the named block).
2. Replace existing markup inside `{% block content %}` with the new structure described above.
3. Remove the old `<style>` block at the bottom.

No changes to:
- Any `views.py`, `urls.py`, or serializer.
- `teacher_base.html`.
- Any other gradebook template not in the four-file list.

## Out of scope (explicit)

- Templates under `gradebookcomponent/templates/gradebookcomponent/{gradebook,subgradebook,termbook,transmutation,activityGrade,studentProgress}/`.
- Any usage of `_legacy_stack.html`, DataTables, Select2, jQuery, SweetAlert2, or Bootstrap 5.
- Server-side filtering, sorting, search, or pagination not already wired in the current views.
- Visual changes to the student-facing gradebook templates.
