# Student Profile: Edit Modal, Active Badges, Level Visuals

**Status:** Draft
**Date:** 2026-04-30
**Scope:** `templates/student/profile.html`, `accounts/views/user_views.py`, `gamification/`

## Goals

Three improvements to the student profile page:

1. **Edit Profile modal** — replace the navigation to `/update_header_profile/` with an in-page modal so editing happens without leaving the profile.
2. **Active (featured) badges** — let the student curate exactly 5 badges to feature; remaining badges stay accessible under a "Show more" toggle.
3. **Level visual system** — communicate level/tier on the avatar at a glance and celebrate level-ups.

## Non-goals

- Editing course, year level, or ID number from the student-side modal (registrar-controlled).
- Changing the existing `update_header_profile` view's signature or permissions.
- Server-side level-up celebration tracking — handled client-side via `localStorage`.
- Restyling other roles' profile pages.

## 1. Edit Profile modal

### Behavior

- The "Edit Profile" button on the student profile (already present in `templates/student/profile.html`, in the `is_own_profile` block) opens a modal instead of navigating.
- Modal contains a single `<form>` that POSTs to `{% url 'update_header_profile' user_id=profile.user.id %}` (the existing view, unchanged).
- On success the view already redirects to `view_profile_header`; we accept that — the page reload shows the updated state.
- On validation error the existing view re-renders the standalone template; for parity with the modal we will switch the form submission to a `fetch` POST so we can surface field errors inside the modal without losing modal state. If the response is a redirect (302), we follow it; if 200 with errors, we re-render fields with `is-invalid` highlighting and an inline error message per field.

### Fields

| Field | Type | Editable |
|---|---|---|
| `student_photo` | file input + `<img>` preview | yes |
| `phone_number` | text | yes |
| `gender` | select | yes |
| `date_of_birth` | date | yes |
| `address` | textarea | yes |
| `id_number` | text (`disabled`) | no — labelled "Managed by registrar" |
| `course` | text (`disabled`) | no — same hint |
| `grade_year_level` | text (`disabled`) | no — same hint |

### Backend impact

The view at `accounts/views/user_views.py:1039` (`update_header_profile`) gets one branch: when `request.headers.get('X-Requested-With') == 'XMLHttpRequest'`, it returns JSON instead of HTML.

- **Success (XHR):** `JsonResponse({'ok': True, 'redirect': reverse('view_profile_header', kwargs={'pk': profile.user.id})})` with status 200.
- **Validation failure (XHR):** `JsonResponse({'ok': False, 'errors': form.errors})` with status 400.
- **Image validation failure (XHR):** same shape as validation failure, with errors keyed by `student_photo`.
- **Non-XHR behavior is unchanged** so any direct hits to the URL still work.

JS side: on `ok=true` close the modal and `location.reload()`; on errors, render `is-invalid` per field and show messages inline.

## 2. Active (featured) badges

### Data model

`gamification/models.py` — add to `StudentBadge`:

```python
is_featured = models.BooleanField(default=False, db_index=True)
```

Migration: `gamification/migrations/<next>_studentbadge_is_featured.py`.

### Endpoint

`POST /gamification/badges/featured/`

- Auth: `@login_required`
- Body: `{ "badge_ids": [<id>, <id>, <id>, <id>, <id>] }`
- Validation:
  - Exactly 5 ids.
  - All ids must reference `StudentBadge` rows owned by `request.user`.
  - On failure, return `400` with `{ "error": "<message>" }`.
- Effect (atomic): set `is_featured = False` on all the user's `StudentBadge` rows, then set `is_featured = True` on the five matching ids.
- Response: `200` with `{ "featured_ids": [...] }`.

URL: add to `gamification/urls.py` as `path('badges/featured/', views.set_featured_badges, name='set_featured_badges')`.

### View context (`profile_view`)

For students, partition `earned` into:

- `featured_badges` — `earned.filter(is_featured=True)` (expected: 0–5).
- `other_badges` — `earned.filter(is_featured=False)`.

Pass both to the template.

### UI on the profile page

In the existing **Badges** section (left column of the grid):

- **Featured row**: render `featured_badges` in the existing `.badges-grid`, prominent.
  - If `featured_badges.count() < 5` and `is_own_profile`, show a soft empty-slot tile per missing slot ("Pick a featured badge") that opens the manage modal on click.
- **More row** (only rendered if `other_badges` is non-empty): heading "More badges (N)" with a `Show more` / `Show less` toggle. Tiles are the same `.badge-tile` style.
- **Manage button** (only when `is_own_profile`): in `profile-section-head`, alongside the existing earned count. Opens the manage modal.
  - Disabled with hint "Earn 5 badges to unlock" if `earned_count < 5`.

### Manage Featured Badges modal

- Grid of all earned badges, each as a checkbox tile (re-uses `.badge-tile` styling).
- Live counter: `X / 5 selected` in the modal header.
- "Save" button is disabled unless `count === 5`. Selecting a 6th deselects nothing — instead the click is rejected with a small inline message "You can only feature 5".
- Pre-checked = currently `is_featured` ones.
- On save: `fetch('/gamification/badges/featured/', { method: 'POST', body: JSON.stringify({badge_ids: [...]}) })`. On success → close modal, `location.reload()`. On failure → show server message in modal footer.

## 3. Level visual system

All three pieces share the same tier mapping (defined once in CSS via classes and once in JS for the level-up toast):

| Level | Tier | Color token |
|---|---|---|
| 1–9 | Bronze | `#cd7f32` |
| 10–19 | Silver | `#c0c0c0` |
| 20–29 | Gold | `var(--gold)` |
| 30–49 | Platinum | `#e5e4e2` |
| 50+ | Diamond | `#b9f2ff` |

A small template tag (`gamification/templatetags/level_tier.py`) computes a tier slug from a level integer and is used in the template to add the right class to the avatar wrapper.

### Tier ring

- Replace the fixed `border: 3px solid var(--gold)` on `.profile-photo` with a class-driven border:
  ```css
  .profile-photo.tier-bronze   { border: 3px solid #cd7f32; box-shadow: 0 0 0 4px rgba(205,127,50,0.15); }
  .profile-photo.tier-silver   { border: 3px solid #c0c0c0; box-shadow: 0 0 0 4px rgba(192,192,192,0.18); }
  .profile-photo.tier-gold     { border: 3px solid var(--gold); box-shadow: 0 0 0 4px var(--gold-glow); }
  .profile-photo.tier-platinum { border: 3px solid #e5e4e2; box-shadow: 0 0 0 4px rgba(229,228,226,0.18); }
  .profile-photo.tier-diamond  { border: 3px solid #b9f2ff; box-shadow: 0 0 0 4px rgba(185,242,255,0.22); }
  ```

### Level pill

- A small `<span class="level-pill tier-X">Lv 14</span>` positioned `absolute` bottom-right of the avatar wrapper.
- Wrapper becomes `position: relative` so the pill anchors correctly.

### XP progress ring

- An inline SVG circle wraps the avatar, sized to the avatar + ring stroke. Stroke color matches tier; arc length = XP-into-current-level / XP-needed-for-next-level.
- Source values come from `StudentGamification`. The exact field names will be discovered during implementation by reading `gamification/models.py`; the spec assumes a `current_xp`-and-`xp_to_next_level` pair or equivalents (`level_progress` / `level_total`). If neither exists, the implementation plan adds a derived property rather than a new column.
- The arc animates from 0 to its final value on page load via a CSS `transition` on `stroke-dashoffset`.
- If `gamification` is `None`, the ring renders empty (0%).

### Confetti on level-up (client-side)

- On profile load, JS reads `localStorage.getItem('lastSeenLevel:<userId>')` and compares to `data-current-level` on the avatar wrapper.
- **Gating** (to avoid celebrating just because the user is new on this device):
  - If the stored value is missing → write the current level silently, do **not** fire.
  - If the stored value exists and current > stored → fire celebration, then update the stored value.
  - If current ≤ stored → do nothing.
- Celebration:
  - A short confetti burst using `canvas-confetti` loaded from CDN (`https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js`). If the script fails to load, we fall back to a toast-only celebration.
  - A toast: "Level up! You're now Lv N · {Tier}". Toast uses SweetAlert2 (already loaded across the student shell).

## Architecture / boundaries

- **Templates touched:** `templates/student/profile.html` (modal markup, badges restructure, avatar wrapper), one new partial `templates/student/_edit_profile_modal.html` if the form gets large enough to warrant it.
- **Views/URLs touched:** `accounts/views/user_views.py` (XHR error branch in `update_header_profile`), `gamification/views.py` + `gamification/urls.py` (new `set_featured_badges`), `gamification/models.py` (new field), one new template tag.
- **JS:** Inline in `templates/student/profile.html` for the modal submit, manage-badges modal, and level-up detection. No new global script files.

## Error handling

- Modal POST that fails network: show "Couldn't save. Try again." in modal footer; keep state.
- Featured badges POST: any 4xx → toast the server message; modal stays open.
- If level-up `localStorage` is unavailable (private mode), the confetti silently no-ops.
- If `StudentGamification` is missing, all level visuals fall back to neutral (no border tier class, no pill, empty ring).

## Testing

- Unit tests in `gamification/tests/`:
  - `set_featured_badges` rejects count != 5.
  - Rejects badges not owned by the user.
  - Successfully replaces the featured set atomically.
- Manual / smoke tests:
  - Edit modal opens, saves, reloads with new photo.
  - Edit modal shows server-side validation errors inline (e.g., DOB in future).
  - Manage modal cannot save with 4 or 6 selected.
  - Level pill, ring, and tier border render correctly at boundaries (level 9 → 10, 19 → 20, etc.).
  - Confetti fires once after a forced level change in a test account; does not fire again on next reload.

## Out of scope (explicitly)

- A "Request change" workflow for registrar-controlled fields (id/course/year).
- Server-side persisted "saw the level-up" flag.
- A separate teacher-side equivalent (we only update the student profile here; teacher profile design is unchanged).
