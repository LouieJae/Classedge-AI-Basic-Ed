# Classedge Plus — Sub-project 2: School Matching & Push

**Status:** Design
**Date:** 2026-04-16
**Depends on:** Sub-project 1 (central catalog portal foundation) — shipped.
**Follow-up:** Sub-project 3 (school-side consumption UI) — not yet brainstormed.

## 1. Goal

Let a central Publisher bind a central-curated `CentralSubject` to a specific school's existing `Subject`, then push the full subject tree (subject → modules → activities, plus files) over HTTPS into a new isolated app on the school's Classedge deployment. Re-push on update. Unbind cascades and deletes from the school. Zero changes to the school's native `Subject` / `Module` / `Activity` tables.

Sub-2 ends when the snapshot data has landed in the school's `received_central_content` tables. Surfacing that data to teachers/students is Sub-3's job.

## 2. Non-goals

- Teacher or student UI on the school side.
- Any bridge between `ReceivedCentralSubject` and the school's native `Subject`.
- Scheduling, curation, skip/hide, or supplementary activities (all Sub-3).
- Auto-push on publish. Push is always Publisher-triggered.
- Automatic retry with backoff. Retries are manual.
- Per-school tier enforcement / Plus subscription gating.
- Central media CDN. Files live in each school's local media dir after push.
- Webhook-style callbacks from school back to central.

## 3. Topology

```
┌─────────────────────┐      HTTPS + bearer token        ┌──────────────────┐
│ central.classedge   │ ─── POST /api/central/ingest ──> │ school Classedge │
│ (central_content)   │ <── GET  /api/central/subjects ──│ (HCCCI, etc.)    │
│                     │ <── DELETE /api/central/ingest/N │                  │
└─────────────────────┘                                   └──────────────────┘
  central DB                                                school DB
  + Schools registry                                        + received_central_content app
  + SchoolSubjectBinding                                    + 3 mirror tables
  + PushJob (history)
```

Central and each school are separate deployments with separate databases. Central never reads from or writes to a school's database directly; all communication is HTTP calls with a bearer token. The central portal is operated by Classify Inc, as are all three school deployments — there is no adversarial trust boundary. Bearer-token-only auth is sufficient.

## 4. Data model

### 4.1 Central DB — new models (`central_content` app)

**`School`**

| Field         | Type                     | Notes                                           |
|---------------|--------------------------|-------------------------------------------------|
| `name`        | `CharField(100)`         | "HCCCI"                                         |
| `base_url`    | `URLField`               | "https://classedge.hccci.edu.ph"                |
| `api_token`   | `CharField(80)`          | 40-hex generated on create, shown once          |
| `is_active`   | `BooleanField`           | Inactive schools hidden from matching dropdown  |
| `notes`       | `TextField(blank)`       | Free text                                       |
| `created_by`  | `FK CentralStaff PROTECT`|                                                 |
| `created_at`  | `DateTimeField auto_now_add` |                                             |
| `updated_at`  | `DateTimeField auto_now` |                                                 |

**`SchoolSubjectBinding`**

| Field                 | Type                          | Notes                                              |
|-----------------------|-------------------------------|----------------------------------------------------|
| `central_subject`     | `FK CentralSubject CASCADE`   |                                                    |
| `target_school`       | `FK School PROTECT`           |                                                    |
| `school_subject_id`   | `IntegerField`                | School-side `Subject.id` (no cross-DB FK possible) |
| `school_subject_name` | `CharField(200)`              | Cached for display; refreshed on each bind         |
| `school_subject_code` | `CharField(30, blank)`        | Cached for display                                 |
| `pushed_version`      | `PositiveIntegerField(null)`  | `central_subject.version` at last successful push  |
| `last_pushed_at`      | `DateTimeField(null)`         |                                                    |
| `bound_by`            | `FK CentralStaff PROTECT`     |                                                    |
| `bound_at`            | `DateTimeField auto_now_add`  |                                                    |

Constraint: `UNIQUE(central_subject, target_school)`.

**`PushJob`**

| Field             | Type                          | Notes                                             |
|-------------------|-------------------------------|---------------------------------------------------|
| `central_subject` | `FK CentralSubject CASCADE`   |                                                   |
| `target_school`   | `FK School CASCADE`           |                                                   |
| `kind`            | `CharField choices`           | `"push"` or `"delete"`                            |
| `status`          | `CharField choices`           | `"success"` or `"failed"`                         |
| `subject_version` | `PositiveIntegerField`        | Central version at time of attempt                |
| `http_status`     | `IntegerField(null)`          |                                                   |
| `response_body`   | `TextField(blank)`            | Truncated to 10000 chars for storage              |
| `error_message`   | `TextField(blank)`            | Exception message if no HTTP response             |
| `started_at`      | `DateTimeField auto_now_add`  |                                                   |
| `finished_at`     | `DateTimeField`               |                                                   |
| `triggered_by`    | `FK CentralStaff PROTECT`     |                                                   |

No `pending`/`in_progress` state — push is synchronous, the row is inserted only after the HTTP call returns.

### 4.2 School DB — new app `received_central_content`

**`ReceivedCentralSubject`**

Fields (content from the central payload): `subject_name`, `subject_descriptive_title`, `subject_short_name`, `subject_description`, `subject_code`, `subject_type`, `unit`, `subject_photo` (ImageField), `target_grade_level`, `target_curriculum`, `target_sdgs` (M2M → `subject.SDG`).

Fields (provenance metadata): `central_id` (int, unique), `central_version` (int), `received_at` (datetime, auto_now_add), `last_received_at` (datetime, auto_now).

**`ReceivedCentralModule`**

| Field               | Type                                 |
|---------------------|--------------------------------------|
| `received_subject`  | `FK ReceivedCentralSubject CASCADE`  |
| `central_id`        | `IntegerField unique`                |
| `file_name`         | `CharField(100)`                     |
| `description`       | `TextField(blank)`                   |
| `file`              | `FileField(null, blank)`             |
| `url`               | `URLField(1500, blank)`              |
| `iframe_code`       | `TextField(blank)`                   |
| `order`             | `PositiveIntegerField(default=0)`    |

**`ReceivedCentralActivity`**

| Field                     | Type                                 |
|---------------------------|--------------------------------------|
| `received_subject`        | `FK ReceivedCentralSubject CASCADE`  |
| `central_id`              | `IntegerField unique`                |
| `activity_name`           | `CharField(100)`                     |
| `activity_instruction`    | `TextField(blank)`                   |
| `activity_type`           | `FK activity.ActivityType PROTECT`   |
| `max_score`               | `PositiveIntegerField`               |
| `time_duration`           | `PositiveIntegerField`               |
| `passing_score`           | `FloatField`                         |
| `passing_score_type`      | `CharField choices`                  |
| `max_retake`              | `PositiveIntegerField`               |
| `retake_method`           | `CharField choices`                  |
| `shuffle_questions`       | `BooleanField`                       |
| `is_graded`               | `BooleanField`                       |
| `related_modules`         | `M2M ReceivedCentralModule`          |

**Isolation guarantee.** The `received_central_content` app has zero FKs into the school's native `Subject` / `Module` / `Activity` tables. It references only `subject.SDG` and `activity.ActivityType` for taxonomy — both of which are essentially static lookup tables. The school's existing code is untouched.

## 5. API surface (school side)

All endpoints require the header `Authorization: Bearer <CENTRAL_INGEST_TOKEN>`. The value lives in the school's `.env` as `CENTRAL_INGEST_TOKEN`. Missing or mismatched → `401`.

URL prefix: `/api/central/` (mounted in the school's root urlconf; not under `settings_central`).

### 5.1 `GET /api/central/subjects/`

Returns the school's `Subject` list for the central matching UI.

```json
[
  {"id": 17, "subject_name": "Math 101", "subject_code": "MATH101"},
  {"id": 18, "subject_name": "Geometry", "subject_code": "MATH201"}
]
```

No pagination. Ordered by `subject_name`.

### 5.2 `POST /api/central/ingest/`

Accepts `multipart/form-data` with a required `payload` part (JSON string) and zero or more file parts.

**File part naming convention:**
- Subject photo: key `subject_photo`
- Module file for the N-th module in the payload's `modules` array: key `module_<N>_file` (0-indexed)

**Payload schema:**

```json
{
  "central_id": 42,
  "central_version": 3,
  "subject_name": "Algebra 1",
  "subject_descriptive_title": "Foundations of Algebra",
  "subject_short_name": "ALG1",
  "subject_description": "...",
  "subject_code": "ALG101",
  "subject_type": "Lec",
  "unit": 3,
  "target_grade_level": "Grade 7",
  "target_curriculum": "K-12",
  "target_sdgs": ["Quality Education", "Gender Equality"],
  "subject_photo_part": "subject_photo",
  "modules": [
    {
      "central_id": 101,
      "file_name": "Module 1",
      "description": "Intro",
      "order": 0,
      "url": "",
      "iframe_code": "",
      "file_part": "module_0_file"
    }
  ],
  "activities": [
    {
      "central_id": 201,
      "activity_name": "Quiz 1",
      "activity_instruction": "...",
      "activity_type": "Quiz",
      "max_score": 100,
      "time_duration": 30,
      "passing_score": 75,
      "passing_score_type": "percentage",
      "max_retake": 2,
      "retake_method": "highest",
      "shuffle_questions": true,
      "is_graded": true,
      "related_module_central_ids": [101]
    }
  ]
}
```

Omit `subject_photo_part` / `file_part` when the central row has no file.

**Ingest algorithm (wrapped in `transaction.atomic`):**

1. Parse `payload` JSON. Malformed → `400`.
2. Resolve `target_sdgs` names to `subject.SDG` rows. Any miss → `422` with `{"error": "unresolved_sdgs", "names": [...]}`. Abort.
3. Resolve every activity's `activity_type` name to `activity.ActivityType`. Any miss → `422` with `{"error": "unresolved_activity_types", "names": [...]}`. Abort.
4. Upsert `ReceivedCentralSubject` by `central_id`. Update every content field; set `central_version`, `last_received_at`.
5. For the current subject, collect the set of module `central_id`s in the payload. Delete any existing `ReceivedCentralModule` rows whose `central_id` is not in that set. Upsert the rest.
6. Same for activities.
7. Rebuild each activity's `related_modules` M2M from `related_module_central_ids`. Unknown ids → `422`, abort.
8. Files: for each referenced `*_part` slug, pull the matching file from the multipart request. Missing part → `400`, abort. Save into the Image/FileField (Django handles storage).
9. Return `200` with `{"received_subject_id": <pk>, "central_version": 3, "received_at": "<iso>"}`.

Any exception inside the transaction rolls back, and the response body carries the error.

### 5.3 `DELETE /api/central/ingest/<central_id>/`

Looks up `ReceivedCentralSubject` by `central_id`.

- Found → delete (FK cascade removes modules and activities), return `204`.
- Not found → return `404` (treated as success by central — the endpoint is idempotent).
- Auth failure → `401`.

## 6. Central-side push function

Location: `central_content/push.py`

```python
def push_subject_to_school(
    binding: SchoolSubjectBinding,
    triggered_by: CentralStaff,
) -> PushJob:
    """
    Build a multipart payload for binding.central_subject and POST it to
    binding.target_school.base_url + "/api/central/ingest/".

    On 2xx: update binding.pushed_version = central_subject.version,
            binding.last_pushed_at = now(), write PushJob(status=success),
            write AuditLogEntry(action="push").
    On non-2xx or requests.RequestException:
            write PushJob(status=failed) with http_status / error_message,
            write AuditLogEntry(action="push_failed"). Do NOT raise.
    """
```

The function is synchronous. The view handler calls it directly; the Publisher's HTTP request blocks until the push returns. Expected duration: seconds to tens of seconds depending on file sizes. This is acceptable given the three schools have few Publishers and push is a manual action.

A sibling function `delete_subject_from_school(binding, triggered_by)` performs the `DELETE` call for unbinds.

### 6.1 Payload builder

Walks the `CentralSubject` → modules → activities tree. Strips:
- `state`, `created_by`, `submitted_by`, `reviewed_by`, `review_notes`, `source_notes`, `created_at`, `updated_at`, `id` (central PK).

Rewrites:
- `id` → `central_id` on every entity.
- `target_sdgs` FK set → list of SDG names.
- `activity_type` FK → `ActivityType.name`.
- `related_modules` M2M → `related_module_central_ids` list.

Emits:
- `central_version = central_subject.version` at top level.
- `*_part` slugs for every file-bearing field, matched by the multipart builder that attaches the actual file bytes.

## 7. UI flow (central side)

### 7.1 Routes

| Route                                  | Method | Purpose                                                  |
|----------------------------------------|--------|----------------------------------------------------------|
| `/schools/`                            | GET    | List registered schools                                  |
| `/schools/new`                         | GET/POST | Create a school (generates api_token, shown once)      |
| `/schools/<id>/edit`                   | GET/POST | Edit name / base_url / is_active / notes                |
| `/schools/<id>/regenerate-token`       | POST   | Regenerate api_token (shown once, old one invalidated)   |
| `/matching/`                           | GET    | Matching workspace, default school = first active       |
| `/matching/?school=<id>`               | GET    | Matching scoped to a specific school                    |
| `/matching/bind`                       | POST   | Create `SchoolSubjectBinding`                            |
| `/matching/unbind/<binding_id>`        | POST   | Cascade-delete from school, then delete binding          |
| `/matching/push/<binding_id>`          | POST   | Push the binding (calls `push_subject_to_school`)        |
| `/push-history/`                       | GET    | `PushJob` list with filters                              |

All mounted under `central_content/urls.py`, which is the `ROOT_URLCONF` when `DJANGO_SETTINGS_MODULE=lms.settings_central`.

### 7.2 Matching workspace (layout A)

- **Top:** school dropdown (active schools only) + "Add school" link.
- **Middle — two-panel picker:**
  - **Left:** approved central subjects (`state=approved`), showing `name · v<version>`. Greyed-out if already bound to the selected school.
  - **Right:** selected school's subject list, fetched live at page load via `GET /api/central/subjects/` on the school. Shows `name — code`. Greyed-out if already bound to a central subject.
  - **"Bind selected"** button enables when both panels have a selection; POSTs to `/matching/bind`.
- **Bottom — current bindings table:** columns = Central subject, School subject, Status, Actions.

**Status derivation** (server-side in the view, not JS):

| Condition                                                         | Label                                  | Color | Actions                 |
|-------------------------------------------------------------------|----------------------------------------|-------|-------------------------|
| `pushed_version is null`                                          | "Not pushed"                           | grey  | `[Push]` `[Unbind]`     |
| `pushed_version == central_subject.version`                       | "Up to date · v{N}"                    | green | `[Re-push]` `[Unbind]`  |
| `pushed_version < central_subject.version`                        | "Drift — pushed v{X}, current v{Y}"    | amber | `[Push update]` `[Unbind]` |
| Most recent PushJob for binding `status=failed` (overlay)         | "Push failed · <shortened error>"      | red   | `[Retry]` `[Unbind]`    |

### 7.3 Unbind confirmation

HTMX modal:

> This will delete **{central_subject.name}** and all its modules and activities from **{school.name}**. Teachers who have scheduled content from this subject will lose it. Type `{central_subject.name}` to confirm.

Submit → `POST /matching/unbind/<binding_id>` → view calls `delete_subject_from_school(binding)`:

1. Calls `DELETE /api/central/ingest/<central_id>/` on the school.
2. On `204` or `404` → delete `SchoolSubjectBinding`, write `PushJob(kind=delete, status=success)`, write `AuditLogEntry(action="unbind")`. Redirect back to matching with a success banner.
3. On any other response or `requests.RequestException` → keep the binding, write `PushJob(kind=delete, status=failed)`, show the error inline. Publisher can retry.

### 7.4 Push history page

Flat list of `PushJob` rows, newest first. Filters: school (dropdown), central subject (autocomplete), kind, status. Row detail: http_status, error_message, response_body (expandable). Read-only.

## 8. Permissions

Enforced via the `@central_role_required` decorator from Sub-1 (Editor / Reviewer / Publisher roles).

| URL pattern                         | Publisher | Reviewer   | Editor |
|-------------------------------------|-----------|------------|--------|
| `/schools/*`                        | full      | read-only  | —      |
| `/matching/` (GET)                  | full      | read-only  | —      |
| `/matching/bind`, `/unbind/*`       | full      | —          | —      |
| `/matching/push/*`                  | full      | —          | —      |
| `/push-history/`                    | full      | full       | —      |

Editor sees no Schools / Matching / Push History nav entries. The nav update lives in `central_content/templates/central_content/base.html`.

## 9. Audit log

Reuse the Sub-1 `AuditLogEntry` model.

| Event                    | action           | subject_type              | subject_id      | Details                          |
|--------------------------|------------------|---------------------------|-----------------|----------------------------------|
| School created           | `school_created` | `School`                  | school.pk       | name, base_url                   |
| School edited            | `school_edited`  | `School`                  | school.pk       | changed fields                   |
| Token regenerated        | `token_regen`    | `School`                  | school.pk       | —                                |
| Binding created          | `bind`           | `SchoolSubjectBinding`    | binding.pk      | central_subject_id, target_school_id |
| Binding deleted (unbind) | `unbind`         | `SchoolSubjectBinding`    | binding.pk      | —                                |
| Push success             | `push`           | `SchoolSubjectBinding`    | binding.pk      | pushed_version                   |
| Push failure             | `push_failed`    | `SchoolSubjectBinding`    | binding.pk      | http_status, error_message       |

## 10. Testing

Extends the Sub-1 pattern — real test DB, factories helper, no new infra.

### 10.1 Central side — `central_content/tests/`

- **`test_school_model.py`** — create, unique constraints, token generation, regenerate.
- **`test_binding_model.py`** — unique constraint, cached-field population, `drift_state` helper (`"never" | "up_to_date" | "drift"`).
- **`test_push_job_model.py`** — kind/status choices, required fields.
- **`test_push_function.py`** — `push_subject_to_school` with `responses` library (or `requests_mock`) stubbing the HTTP layer:
  - happy path (2xx)
  - 401 from school
  - 422 unresolved SDG
  - 5xx from school
  - `requests.ConnectionError`
  - `requests.Timeout`
  - file field attached correctly
- **`test_delete_function.py`** — happy 204, 404 treated as success, connection error treated as failure.
- **`test_matching_views.py`** — renders, bind POST, unbind POST (mocked delete call), push POST (mocked push call), permission matrix (editor 403, reviewer view-only).
- **`test_schools_views.py`** — CRUD + permissions + token regeneration.
- **`test_push_history_views.py`** — list render, filters, permissions.

### 10.2 School side — `received_central_content/tests/`

- **`test_models.py`** — field shapes, FK cascade, unique `central_id`.
- **`test_catalog_api.py`** — list response, 401 without token, 401 with wrong token.
- **`test_ingest_api.py`** — happy path, re-push upsert + orphan delete, unresolved SDG 422, unresolved activity_type 422, missing file part 400, transaction rollback on mid-ingest failure, 401 without token.
- **`test_ingest_delete.py`** — 204 happy, 404 idempotent, 401.

### 10.3 Integration smoke test

One test in `central_content/tests/test_integration_push.py` that exercises the full loop end-to-end: builds a `CentralSubject` tree, stubs the HTTP layer so the call routes to the school-side view handler directly, verifies that `ReceivedCentralSubject` / modules / activities are populated correctly. Everything else uses mocks.

### 10.4 Target

~50-60 new tests, no flakes. `manage.py test central_content received_central_content` clean.

## 11. Migrations

- Central: one migration adding `School`, `SchoolSubjectBinding`, `PushJob`.
- School: one migration creating the `received_central_content` app schema.
- No data migration. Existing Sub-1 rows are untouched.

## 12. Deployment / rollout

1. School side: deploy new `received_central_content` app and `/api/central/*` urls. Add `CENTRAL_INGEST_TOKEN` to the school's `.env`. Run the migration.
2. Central side: deploy new models, push function, views, templates. Run the migration. Create a `School` row per deployed school, copy each token into the corresponding school's `.env`.
3. Publisher uses the matching workspace to bind and push.

Both sides can be deployed independently — the central portal won't blow up if a school is still on the old build, because matching / push will simply fail with a 404 and the `PushJob` will surface it.

## 13. Risks

1. **Large payloads block a web worker.** Synchronous push means a Publisher's click ties up a Gunicorn worker for tens of seconds per subject. With 3-4 publishers clicking manually, acceptable. If it becomes a bottleneck, a future Sub-2.5 moves push to Celery.
2. **Seed data drift.** Central and school each have their own `subject.SDG` and `activity.ActivityType` tables, seeded independently. Drift causes hard `422` failures. A Sub-2.1 seed-sync task is possible later; for now the Publisher sees a clear error listing the unresolved names.
3. **File storage multiplies.** Same PDF pushed to 3 schools = 3 copies on 3 servers. Expected.
4. **No cross-school atomicity.** If the Publisher pushes one subject to 3 schools and the 2nd fails, the 1st is already updated. PushJob per school makes the state visible, but Publisher has to reason about it. No all-or-nothing group-push in Sub-2.
5. **Sub-3 coupling assumption.** This spec assumes Sub-3 will bridge `ReceivedCentralSubject` to the school's native `Subject` via a FK added to the native `Subject` (e.g., a nullable `source_central_subject` field). If Sub-3 decides on a wrapper layer instead, the bridge mechanism is still TBD but nothing in Sub-2 constrains the choice.

## 14. Open questions deferred to Sub-3

- How does received content surface to teachers and students (native `Subject` FK, wrapper view, separate catalog)?
- Scheduling, curation, skip/hide, supplementary activities.
- Tier enforcement (is this school actually on Plus?).
- Teacher-visible drift indicator (does the teacher need to see "new version available"?).
- Purge policy for content that existed before Sub-3 shipped.
