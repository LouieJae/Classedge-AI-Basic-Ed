# Gradebook htmx Adoption + Termbook Table Alignment

**Date:** 2026-05-06
**Scope:** Pilot htmx adoption on the gradebook page only; align the standalone termbook list page with the gradebook table design and behavior.

---

## Goal

Convert the gradebook page (`grade-book/`) and the standalone termbook list page (`term-book/`) from full-page-reload CRUD to htmx-driven partial updates. Both pages will share the same table markup, styles (`gb-*`), and htmx interactions so they look and behave identically.

This is a pilot — no other pages are touched. Existing full-page views remain as fallbacks.

## Non-Goals

- No htmx adoption outside the gradebook + termbook tables.
- No conversion of standalone `create_grade_book.html` / `update_grade_book.html` pages — they continue to work for direct links / fallback.
- No inline cell-edit (tap-to-edit on name/percentage/weight) — deferred to a later pass.
- No subgradebook, transmutation, activity-grading, or student-grades changes.
- No SPA routing, no Alpine/Stimulus, no front-end build tooling.

## Affected Files

**Templates**
- `gradebookcomponent/templates/gradebookcomponent/gradebook/grade_book.html` (modify — wire htmx, mount modal container)
- `gradebookcomponent/templates/gradebookcomponent/termbook/term_book.html` (rewrite — adopt `gb-*` table + htmx)
- New partials under `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/`:
  - `_gradebook_table.html`
  - `_gradebook_row.html`
  - `_gradebook_totals.html`
  - `_gradebook_form.html`
  - `_empty_state.html`
- New partials under `gradebookcomponent/templates/gradebookcomponent/termbook/partials/`:
  - `_termbook_table.html`
  - `_termbook_row.html`
  - `_termbook_totals.html`
  - `_termbook_form.html`

**Views**
- `gradebookcomponent/views/gradebook_view.py` (add htmx endpoints alongside existing views)
- `gradebookcomponent/views/termbook_view.py` (add htmx endpoints; full-page views remain)

**URLs**
- `gradebookcomponent/urls.py` (add htmx-only routes under `gradebook/htmx/...` and `termbook/htmx/...`)

**Settings (optional but preferred)**
- Add `django-htmx` to `INSTALLED_APPS` and middleware for clean `request.htmx` API. If not adopted, fall back to `request.headers.get("HX-Request") == "true"`.

## Architecture

### Endpoints (new, htmx-only)

| Purpose | Method | URL name | URL pattern | Response |
|---|---|---|---|---|
| List/filter gradebooks | GET | `gradebook-htmx-list` | `gradebook/htmx/list/` | `_gradebook_table.html` |
| Open create form | GET | `gradebook-htmx-form` | `gradebook/htmx/form/` | `_gradebook_form.html` (modal body) |
| Open edit form | GET | `gradebook-htmx-form-edit` | `gradebook/htmx/form/<pk>/` | `_gradebook_form.html` |
| Submit create/edit | POST | (same form URLs) | — | success → `_gradebook_row.html` (with `HX-Trigger: gb-modal-close, gb-totals-refresh`); error → `_gradebook_form.html` (200, with errors) |
| Delete row | POST | `gradebook-htmx-delete` | `gradebook/htmx/delete/<pk>/` | empty 200, `HX-Trigger: gb-totals-refresh` |
| Refresh totals row | GET | `gradebook-htmx-totals` | `gradebook/htmx/totals/` | `_gradebook_totals.html` |

A mirrored set of endpoints exists for termbook (`termbook/htmx/list/`, `.../form/`, `.../form/<pk>/`, `.../delete/<pk>/`, `.../totals/`).

### View layer

- All htmx views detect htmx requests and short-circuit to render a partial. Non-htmx requests to these URLs return `HttpResponseBadRequest` (these are not user-facing pages).
- Reuse existing `GradeBookForm` and `TermBookForm` — only the response template differs.
- Permissions / queryset scoping mirrors existing full-page views (same login decorator, same `request.user` filtering).
- `HX-Trigger` header is used to fan out events:
  - `gb-modal-close` → modal listens, hides itself.
  - `gb-totals-refresh` → totals row listens (`hx-trigger="gb-totals-refresh from:body"`) and refetches.

### Frontend integration

- `htmx.org@1.9.12` is already loaded in `templates/base_operation.html`. No new asset needed.
- Add `<body hx-headers='{"X-CSRFToken":"{{ csrf_token }}"}'>` (or scope to the gradebook page wrapper) so all htmx POSTs include CSRF.
- Single modal mount at the bottom of `grade_book.html` and `term_book.html`:
  ```html
  <div id="gb-modal" class="gb-modal" hx-on:gb-modal-close="this.innerHTML=''"></div>
  ```
- Search input uses `hx-get` with `hx-trigger="keyup changed delay:300ms"` and `hx-target="#gb-table-body"`.

### Termbook alignment

- `term_book.html` is rewritten to use the same `gb-table`, `gb-cell-strong`, `gb-action-cell`, `gb-icon-btn` markup currently in `grade_book.html`'s termbook section.
- The embedded termbook section inside `grade_book.html` and the standalone `term_book.html` page **both include `_termbook_table.html`** — single source of truth.
- Same htmx behaviors: debounced search, modal create/edit, row-swap delete, totals refresh on event.

### Data flow examples

**Search gradebooks:**
1. User types in search input → `hx-get="/gradebook/htmx/list/?q=..."`, `hx-target="#gb-tbody"`, `hx-swap="innerHTML"`.
2. View filters queryset, renders `_gradebook_table.html` body, returns it.

**Delete a gradebook:**
1. Click trash icon → `hx-post="/gradebook/htmx/delete/42/"`, `hx-target="closest tr"`, `hx-swap="outerHTML swap:200ms"`, `hx-confirm="Delete this gradebook?"`.
2. View deletes, returns `HttpResponse(status=200, headers={"HX-Trigger": "gb-totals-refresh"})`.
3. Row fades out. Totals tfoot listens to `gb-totals-refresh` and refetches via `hx-get`.

**Create gradebook (modal):**
1. Click "Add Gradebook" → `hx-get="/gradebook/htmx/form/"`, `hx-target="#gb-modal"`, `hx-swap="innerHTML"`.
2. Modal partial renders form with `hx-post="/gradebook/htmx/form/"`, `hx-target="#gb-modal"`, `hx-swap="innerHTML"`.
3. On success, view returns the new `_gradebook_row.html` with `HX-Trigger: gb-modal-close, gb-totals-refresh` and `HX-Reswap: afterbegin`, `HX-Retarget: #gb-tbody`. Row appears, modal closes, totals refresh.
4. On error, view returns the form partial with bound errors (status 200) — modal stays open.

## Error Handling

- Form validation errors: return `_gradebook_form.html` with bound form (status 200), htmx swaps it back into the modal. No page reload.
- Server errors (5xx): a global JS listener on `htmx:responseError` shows a toast: `"Something went wrong. Please try again."`
- Permission errors (403/404): treated as `htmx:responseError`, same toast.
- Empty list (no rows): list endpoint renders an `_empty_state.html` `<tr>` inside `#gb-tbody`.

## Testing

- One Django `TestCase` per htmx endpoint covering:
  - Authenticated GET/POST returns 200 and the expected partial template (use `assertTemplateUsed`).
  - `HX-Request: true` header path works; non-htmx request returns 400.
  - Form validation errors return form partial, not the row.
  - Delete returns 200 + `HX-Trigger: gb-totals-refresh`.
- Manual browser smoke test on both pages:
  - Search debounces and updates table without flash.
  - Create modal opens, validates, closes on success, row appears.
  - Edit modal preloads values, saves, row updates.
  - Delete confirms, fades, totals update.
  - Termbook page looks visually identical to the termbook section embedded in the gradebook page.

## Rollout / Reversibility

- All existing full-page URLs (`create-grade-book/`, `update-grade-book/<pk>/`, `delete-grade-book/<pk>/`, equivalent termbook routes) stay intact and functional.
- New htmx endpoints live under separate `htmx/` URL prefix — no collisions.
- If a regression is found, the htmx wiring on the page can be removed and full-page links restored without touching the underlying domain logic.

## Open Questions

None at design time. Form-field set, validation, and queryset scoping are inherited unchanged from existing views.
