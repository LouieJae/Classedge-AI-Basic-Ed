# Sub-project 3 — School-side Consumption UI

## Overview

Bridge centrally-pushed content into the school's native Subject/Module/Activity
tables so teachers see and use it like any other school-created content. The
publisher drives the entire flow from the central portal — no school-side admin
action required.

## Architecture Decision: FK Bridge on Native Subject

When the publisher pushes a `CentralSubject` to a school, the content (modules
and activities) is created as **native rows** inside an existing school-side
`Subject`. Teachers interact with them through the normal subject view — no
separate "Central Content" catalog, no lock, no drift indicator.

A nullable `central_source_id` field on native `Module` and `Activity` rows
tracks which rows originated from a central push. This field is invisible to
teachers and exists solely so that re-push can delete and recreate only
central-originated content, leaving school-created supplementary content
untouched.

## Key Flows

### Bind (publisher links CentralSubject to a school Subject)

1. Publisher opens the matching workspace (Sub-2).
2. Right panel already shows the school's subject catalog (fetched from
   `GET /api/central/subjects/`).
3. Publisher clicks "Bind" on a CentralSubject.
4. Instead of immediately creating the binding, an inline subject picker appears
   populated from the school catalog.
5. Publisher selects the target school Subject and confirms.
6. `SchoolSubjectBinding` is created with `target_subject_id` set to the
   school's native `Subject.pk`.

### Push (publisher pushes content into school Subject)

1. Publisher clicks "Push" on a bound CentralSubject (existing Sub-2 flow).
2. `build_push_payload` includes `target_subject_id` from the binding.
3. School's `POST /api/central/ingest/` handler:
   a. Looks up the native `Subject` by `target_subject_id` (404 if not found).
   b. Writes/updates `ReceivedCentralSubject` for version tracking.
   c. Deletes existing `Module` rows where `central_source_id = central_id`.
   d. Deletes existing `Activity` rows where `central_source_id = central_id`.
   e. Creates new native `Module` rows from the payload, tagged with
      `central_source_id = central_id`.
   f. Creates new native `Activity` rows from the payload, tagged with
      `central_source_id = central_id`.
   g. All inside `transaction.atomic()`.
4. `ReceivedCentralModule` / `ReceivedCentralActivity` are NOT written.

### Re-push

Same as Push. Step (c) and (d) clear only central-originated rows. School-
created modules/activities (where `central_source_id IS NULL`) are untouched.

### Delete (publisher removes content from school)

1. Publisher triggers delete (existing Sub-2 flow).
2. School's `DELETE /api/central/ingest/<central_id>/` handler:
   a. Deletes `ReceivedCentralSubject` (existing behavior).
   b. Also deletes native `Module` and `Activity` rows with matching
      `central_source_id`.

## Data Model Changes

### Modified: `central_content.SchoolSubjectBinding`

Add field:

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `target_subject_id` | PositiveIntegerField | Yes | School's native `Subject.pk`. Nullable for backward compat with existing Sub-2 bindings. Required via form validation for new bindings. Indexed. |

### Modified: `module.Module` (school-side native model)

Add field:

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `central_source_id` | PositiveIntegerField | Yes | `CentralSubject.pk` from central portal. Null for school-created modules. Indexed. Used by re-push to identify rows to clear. |

### Modified: `activity.Activity` (school-side native model)

Add field:

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `central_source_id` | PositiveIntegerField | Yes | Same semantics as Module.central_source_id. |

### Unchanged: `received_central_content.ReceivedCentralSubject`

Kept for version tracking (`central_version` field). Written on ingest as before.

### Deprecated: `received_central_content.ReceivedCentralModule/Activity`

Kept in place (77 Sub-2 tests rely on them). New push flow stops writing to
them. Future cleanup migration can drop these tables.

## Central Portal UI Changes

### Matching workspace (existing Sub-2 view)

One change to the bind flow:

- **Before (Sub-2):** Click "Bind" -> binding created immediately (CentralSubject -> School).
- **After (Sub-3):** Click "Bind" -> inline subject picker appears (populated from
  the already-fetched school catalog) -> publisher selects target Subject ->
  confirm -> binding created with `target_subject_id`.

Binding card in the workspace should display the target school Subject name.

No other central portal changes. Schools CRUD, push trigger, push history
remain as-is.

## School-side API Changes

### `POST /api/central/ingest/` (rewritten)

New required field in payload: `target_subject_id` (integer).

New behavior:
1. Validate `target_subject_id` -> fetch native `Subject` (404 on miss).
2. Update/create `ReceivedCentralSubject` (version tracking only).
3. Delete `Module.objects.filter(subject=subject_obj, central_source_id=payload.central_id)`.
4. Delete `Activity.objects.filter(subject=subject_obj, central_source_id=payload.central_id)` (confirm Activity->Subject relationship during planning).
5. Create native `Module` rows with `central_source_id` set.
6. Create native `Activity` rows with `central_source_id` set.
7. All atomic.

Returns 400 if `target_subject_id` is missing.

### `DELETE /api/central/ingest/<central_id>/` (extended)

In addition to deleting `ReceivedCentralSubject`, also delete native
`Module.objects.filter(central_source_id=central_id)` and
`Activity.objects.filter(central_source_id=central_id)`.

## What Schools See

Nothing changes from the teacher/student perspective. Pushed content appears as
native modules and activities inside the school Subject that the publisher
targeted. Teachers can view, edit, reorder, and supplement the content as they
would any school-created content.

## Testing

### Migration tests
- `SchoolSubjectBinding.target_subject_id` is nullable and indexed.
- `Module.central_source_id` is nullable and indexed.
- `Activity.central_source_id` is nullable and indexed.

### Ingest endpoint tests
- Push with valid `target_subject_id` creates native Module/Activity with `central_source_id` set.
- Re-push clears only central-tagged rows, school-created rows untouched.
- Push with unknown `target_subject_id` returns 404.
- Push without `target_subject_id` returns 400.
- DELETE clears `ReceivedCentralSubject` AND native rows with matching `central_source_id`.

### Matching UI tests
- Bind creates `SchoolSubjectBinding` with correct `target_subject_id`.
- Binding card displays target school Subject name.

### Regression
- All 142 existing tests (65 Sub-1 + 77 Sub-2) must continue passing.

## Out of Scope

- Teacher-visible drift indicator ("new version available").
- Per-school tier enforcement (Plus vs Core).
- School admin management panel for central content.
- Scheduling or curation workflows.
- `ReceivedCentralModule`/`ReceivedCentralActivity` table cleanup migration.
