# Old LMS Migration — Foundation + Dashboard + Role PoC

**Date:** 2026-05-20
**Status:** Approved design — ready for implementation planning
**Parent docs:**
- [docs/migration/2026-05-19-old-lms-migration-plan.md](../../migration/2026-05-19-old-lms-migration-plan.md) (overall migration plan)
- [docs/migration/2026-05-20-assessment-models-addendum.md](../../migration/2026-05-20-assessment-models-addendum.md) (assessment scope, later plan)
- [docs/migration/2026-05-20-media-files-subplan.md](../../migration/2026-05-20-media-files-subplan.md) (media pipeline, later plan)

---

## 1. Goal

Build the **foundation** for migrating data from an old LMS to Classedge-AI, validated end-to-end against the simulation classedge (`/home/classify/Desktop/Projects/simulation-lms/classedge`) using `roles.Role` as the proof-of-concept model. Deliver an operations dashboard that lets a human run the pipeline sequentially or per-model, with precise per-row error tracking down to source file and line number.

After this plan ships, every subsequent migration (accounts, classroom, assessment, media, then SNCFI and NewHope) plugs into the same foundation without re-doing scaffolding.

## 2. Non-goals (deferred to later plans)

- Migrating any model other than `roles.Role`.
- Media / file content migration.
- Running against SNCFI or NewHope production deployments.
- Cross-tenant merging strategies.
- Cutover automation (read-only freeze, DNS swap).

## 3. Target source

`/home/classify/Desktop/Projects/simulation-lms/classedge` — Django project on local filesystem. Will be run locally during development to serve the new `/api/migration/...` endpoints over HTTPS or HTTP (dev-mode).

The base URL is operator-configurable via `MIGRATION_OLD_LMS_BASE_URL`. The same code will later point at SNCFI and NewHope deployments without changes.

## 4. Architecture overview

```
┌─────────────────────────────────────┐                ┌──────────────────────────────────────┐
│   simulation-lms/classedge (old)    │                │     Classedge-Ai (new)                │
│                                     │   HTTPS+Token  │                                       │
│   migration_api app (additive)      │ ◄───────────── │   migration app                       │
│   ├─ MigrationToken                 │   cursor pages │   ├─ MigrationJob                     │
│   ├─ Auth + Throttle                │                │   ├─ IDMap                            │
│   ├─ CursorByPkPagination           │                │   ├─ MigrationRunLog                  │
│   ├─ /api/migration/health/         │                │   ├─ MigrationErrorRecord             │
│   └─ /api/migration/roles/role/     │                │   ├─ OldLmsClient                     │
│                                     │                │   ├─ mappers/ + writers/              │
│                                     │                │   ├─ Celery: migrate_model_batch      │
│                                     │                │   ├─ Celery beat: run_migration_pipe… │
│                                     │                │   └─ Dashboard (base_operation.html)  │
└─────────────────────────────────────┘                └──────────────────────────────────────┘
```

## 5. Components — old side (`migration_api`)

Located at `/home/classify/Desktop/Projects/simulation-lms/classedge/migration_api/`. Additive only — touches existing code in exactly two places: one `INSTALLED_APPS` line and one `urls.py` include.

### 5.1 Files

```
migration_api/
├── __init__.py
├── apps.py
├── models.py                      # MigrationToken
├── migrations/0001_initial.py
├── authentication.py              # MigrationTokenAuthentication
├── throttling.py                  # Default + heavy scoped throttles
├── pagination.py                  # CursorByPkPagination
├── serializers/
│   ├── __init__.py
│   └── role.py
├── views/
│   ├── __init__.py
│   ├── base.py                    # MigrationReadOnlyViewSet (list + detail)
│   ├── health.py
│   └── role.py                    # RoleMigrationViewSet — list + detail-by-pk
├── urls.py
└── admin.py
```

### 5.2 `MigrationToken` model

```python
class MigrationToken(models.Model):
    label        = CharField(max_length=120)
    token_hash   = CharField(max_length=64, unique=True)   # sha256 hex
    is_active    = BooleanField(default=True)
    created_at   = DateTimeField(auto_now_add=True)
    last_used_at = DateTimeField(null=True, blank=True)
```

Plaintext token shown once on creation in admin. Stored hashed. Constant-time compare on auth.

### 5.3 Authentication

`Authorization: Token <plaintext>` → SHA-256 → lookup → must be `is_active=True`. Updates `last_used_at` on success.

### 5.4 Throttling

Two DRF scoped throttles:
- `migration_default` — 30/min, used by Role and other light endpoints.
- `migration_heavy` — 10/min, reserved for high-volume endpoints later.

Scope key is the token id, not the IP.

### 5.5 Cursor pagination

`CursorByPkPagination`:
- Orders by `pk ASC`.
- `?cursor=<last_pk>` returns rows with `pk > last_pk`.
- Page size: `?limit=<n>` clamped 1–500, default 500.
- Response: `{results, next_cursor, has_more, total_estimated}` where `total_estimated` is a cached `COUNT(*)` (5-minute TTL).

Stable over long runs: even if old rows are inserted at the tail, no row is ever returned twice and never skipped.

### 5.6 Endpoints

```
GET /api/migration/health/
GET /api/migration/roles/role/?cursor=&limit=500
GET /api/migration/roles/role/<old_pk>/         # for single-row retry from new side
```

## 6. Components — new side (`migration`)

Located at `Classedge-Ai/migration/`.

### 6.1 Files

```
migration/
├── apps.py
├── models/
│   ├── __init__.py
│   ├── job.py
│   ├── idmap.py
│   ├── run_log.py
│   └── error_record.py
├── migrations/0001_initial.py
├── client/
│   ├── __init__.py
│   ├── http.py
│   └── exceptions.py
├── mappers/
│   ├── __init__.py                # registry
│   ├── base.py                    # MapperResult, helpers
│   └── roles_role.py
├── writers/
│   ├── __init__.py
│   └── base.py
├── tasks/
│   ├── __init__.py
│   ├── batch.py
│   ├── pipeline.py
│   ├── verify.py
│   └── retry.py                   # retry_single_row, sweep_missing_fk
├── services/
│   ├── __init__.py
│   ├── progress.py
│   └── error_capture.py
├── views/
│   ├── __init__.py
│   ├── overview.py
│   ├── job_detail.py
│   ├── errors.py
│   └── actions.py
├── templates/migration/
│   ├── base.html                  # extends templates/base_operation.html
│   ├── overview.html
│   ├── job_detail.html
│   ├── errors.html
│   ├── _job_row.html
│   ├── _run_log_tail.html
│   └── _error_drawer.html
├── static/migration/
│   └── migration.css
├── urls.py
├── admin.py
└── settings_defaults.py
```

### 6.2 Models

**`MigrationJob`** — one row per `(app_label, model_name)`:
```
app_label, model_name (unique together)
status: pending | running | paused | completed | failed
last_cursor (nullable str)
total_estimated, rows_fetched, rows_written, rows_skipped, rows_errored
started_at, updated_at, completed_at
dry_run (bool, defaults from setting)
```

**`IDMap`** — `(app_label, model_name, old_pk)` → `new_pk`. Unique together. Indexed on `(app_label, model_name, old_pk)`. CharField PKs to support int and UUID.

**`MigrationRunLog`** — one row per batch attempt:
```
job (FK)
started_at, finished_at
cursor_in, cursor_out
rows_in_page, rows_written, rows_skipped, rows_errored
http_status, retry_attempt
is_retry, is_dry_run
notes (text, blank)
```

**`MigrationErrorRecord`** — schema in §7.2.

### 6.3 `OldLmsClient`

`requests.Session` with:
- Auth header injected from `MIGRATION_OLD_LMS_TOKEN`.
- Timeout from `MIGRATION_HTTP_TIMEOUT` (default 30s).
- Retry policy: max `MIGRATION_MAX_RETRIES` attempts, exponential backoff (1s, 2s, 4s, …), only on 5xx and connection errors.
- 401/403 → raise `AuthError` (no retry).
- 429 → raise `ThrottledError`, respects `Retry-After` header.
- 4xx other than 401/403/429 → `PermanentError`.
- 5xx exhausted → `TransientError`.

Methods:
- `fetch_page(app, model, cursor=None, limit=500) -> {results, next_cursor, has_more, total_estimated}`
- `fetch_by_pk(app, model, old_pk) -> dict`
- `health() -> dict`

### 6.4 Mapper contract

```python
@dataclass
class MapperResult:
    fields: dict                # new-model field values
    fk_resolutions: list[tuple] # [(target_app, target_model, old_pk, new_field_name)]
    skip: bool = False
    skip_reason: str = ""
```

Mappers are pure functions. FK resolution is centralized: mappers declare which old-PK fields need IDMap rewriting; the writer performs the lookup and either fills the new FK or records a `missing_fk` error.

```python
@register_mapper("roles", "Role")
def map_role(payload: dict) -> MapperResult:
    return MapperResult(
        fields={
            "name": payload["name"],
            "description": payload.get("description", ""),
            "is_active": payload.get("is_active", True),
        },
        fk_resolutions=[],
    )
```

### 6.5 Writer

For each row:
1. Open savepoint.
2. Look up existing `IDMap` row. If present → load target instance, else create new instance.
3. Run mapper.
4. Resolve declared FKs via IDMap; missing → raise `MissingFKError(field, target_app, target_model, old_pk)`.
5. Apply fields, call `full_clean()`, call `save()`.
6. Upsert `IDMap` row.
7. Release savepoint.

On any exception, rollback the savepoint and re-raise typed for `error_capture`.

### 6.6 Celery tasks

**`migrate_model_batch(job_id)`** — fetches one page, writes each row, advances cursor atomically with counters, appends `MigrationRunLog`. Honors `MIGRATION_DRY_RUN`. Honors `MigrationJob.status == paused` by returning early.

**`run_migration_pipeline()`** — beat-triggered orchestrator. For each `MigrationJob` in dependency order (Phase 1: just `roles.Role`), enqueues `migrate_model_batch` if status is `pending`/`running` and not already in-flight.

**`verify_migration(app, model)`** — count parity, sampled deep-field comparison, IDMap completeness. Returns a structured report stored on the job.

**`retry_single_row(job_id, old_pk)`** — re-fetches one row by PK, re-runs mapper + writer, marks any matching error records resolved on success.

### 6.7 Settings

```python
MIGRATION_OLD_LMS_BASE_URL = env("MIGRATION_OLD_LMS_BASE_URL")
MIGRATION_OLD_LMS_TOKEN    = env("MIGRATION_OLD_LMS_TOKEN")
MIGRATION_BATCH_SIZE       = env.int("MIGRATION_BATCH_SIZE", 500)
MIGRATION_BATCH_INTERVAL_SECONDS = env.int("MIGRATION_BATCH_INTERVAL_SECONDS", 30)
MIGRATION_DRY_RUN          = env.bool("MIGRATION_DRY_RUN", False)
MIGRATION_HTTP_TIMEOUT     = env.int("MIGRATION_HTTP_TIMEOUT", 30)
MIGRATION_MAX_RETRIES      = env.int("MIGRATION_MAX_RETRIES", 5)
MIGRATION_ENABLED          = env.bool("MIGRATION_ENABLED", False)   # beat schedule no-op when False
```

## 7. Error tracking — precise per-row diagnostics

This is the core operator UX. Every failure produces a `MigrationErrorRecord` whose fields point unambiguously at the data that failed and the line of our code that failed it.

### 7.1 Error categories

| Category | Source |
|---|---|
| `transport_error` | network / 5xx exhausted from `OldLmsClient` |
| `auth_error` | 401/403 — job auto-pauses |
| `throttled` | 429 — task sleeps Retry-After then re-enqueues; no row blamed |
| `mapper_error` | exception inside `mappers/*.py` |
| `missing_fk` | IDMap lookup returns None for a declared FK |
| `validation` | Django `ValidationError` on `full_clean()` |
| `db_error` | `IntegrityError` / `DataError` |
| `unknown` | last-resort `except Exception` |

### 7.2 `MigrationErrorRecord` schema

```python
class MigrationErrorRecord(models.Model):
    job              = ForeignKey(MigrationJob, on_delete=CASCADE, related_name="errors")
    run_log          = ForeignKey(MigrationRunLog, on_delete=SET_NULL, null=True)
    occurred_at      = DateTimeField(auto_now_add=True)

    # where in source data
    old_app          = CharField(max_length=64)
    old_model        = CharField(max_length=64)
    old_pk           = CharField(max_length=64, blank=True)
    batch_cursor     = CharField(max_length=128, blank=True)
    batch_index      = IntegerField(null=True)

    # what failed
    category         = CharField(max_length=32)
    message          = CharField(max_length=500)
    field            = CharField(max_length=120, blank=True)
    expected         = CharField(max_length=500, blank=True)
    actual           = CharField(max_length=500, blank=True)

    # where in our code
    source_file      = CharField(max_length=255, blank=True)
    source_line      = IntegerField(null=True)
    source_function  = CharField(max_length=120, blank=True)
    traceback        = TextField(blank=True)

    # raw payload that triggered failure (capped, redacted)
    payload_excerpt  = JSONField(default=dict)

    # lifecycle
    resolved         = BooleanField(default=False)
    resolved_at      = DateTimeField(null=True)
    resolution_note  = TextField(blank=True)

    class Meta:
        indexes = [
            Index(fields=["job", "category"]),
            Index(fields=["resolved", "category"]),
        ]
```

### 7.3 Capture helper

`migration/services/error_capture.py::capture(...)` is the single funnel:
- Builds a `TracebackException`.
- Walks frames innermost-out, returns the first frame whose path starts with `BASE_DIR/migration/` or `BASE_DIR/<app>/mappers/`.
- Records `source_file`, `source_line`, `source_function` from that frame — never a Django/Celery internal frame.
- Redacts payload keys matching a configurable allowlist of safe fields; default policy: drop unknown keys whose name matches `password|token|secret|key`.
- Caps `traceback` at 20,000 chars and `message` at 500.

This helper is the only place exceptions become records — every catch site calls it.

### 7.4 Frame filter is itself tested

A dedicated unit test raises an exception inside a fake mapper module and asserts the captured `source_file` ends with `mappers/roles_role.py` and `source_line` matches the raising line — protecting against Django/Celery internals leaking into the record.

## 8. Dashboard

Extends `templates/base_operation.html`. Mounted at `/operations/migration/`. Gated to superusers via the existing project auth mixin.

### 8.1 Pipeline overview (`/operations/migration/`)

- Header strip: target old-LMS base URL, active token label, last successful `health` call, current `MIGRATION_DRY_RUN` state.
- Global controls: **Start pipeline**, **Pause all**, **Resume all**, **Toggle dry-run**.
- Job table — one row per `MigrationJob`, columns: status pill · progress bar (rows_written / total_estimated) · rate (rows/min) · ETA · error count badge · row actions.
- HTMX polls `_job_row.html` fragment every 3s. Configurable poll interval.

### 8.2 Job detail (`/operations/migration/job/<id>/`)

- Header: full counters from `MigrationJob`.
- Last 50 `MigrationRunLog` rows, newest first, auto-tailed.
- Recent 10 errors, with link to inspector pre-filtered to the job.
- Action buttons: **Pause**, **Resume**, **Restart from cursor**, **Restart from zero** (confirm modal), **Re-verify**, **Sweep missing-FK retries**.

### 8.3 Error inspector (`/operations/migration/errors/`)

- Filters: job · category · date range · `old_pk` search · resolved/unresolved.
- Row click opens the error drawer.

### 8.4 Error drawer

Displays every field of the selected `MigrationErrorRecord`. Top section shows the precise location:

```
CODE   migration/mappers/roles_role.py:243  in  map_role()
```

The path/line render as a `vscode://file/<absolute>:<line>` link. Drawer also offers:
- **Retry this row** (enqueues `retry_single_row`).
- **Mark resolved** with optional note.
- **Copy payload** (JSON copy-to-clipboard).
- Collapsible traceback.

### 8.5 Dry-run mode

A global setting (toggle on Screen A). When on, writers skip the final `save()` and `IDMap` upsert; run logs are tagged `is_dry_run=True`. Used to estimate timings and rehearse the run safely.

## 9. Data flow per batch

1. Celery beat fires `run_migration_pipeline` every `MIGRATION_BATCH_INTERVAL_SECONDS`.
2. Orchestrator finds eligible jobs in dependency order, enqueues `migrate_model_batch(job_id)`.
3. Task loads `MigrationJob`, reads `last_cursor`.
4. Calls `OldLmsClient.fetch_page(app, model, cursor)`.
5. For each row in the page, in a savepoint:
   - Mapper runs.
   - FK resolutions via IDMap.
   - Writer applies fields, validates, saves, upserts IDMap.
   - On any exception: `error_capture.capture(...)` then continue.
6. Atomically: update `last_cursor`, increment counters, append `MigrationRunLog`.
7. If `next_cursor is None` and `has_more is False` → mark job `completed`, enqueue `verify_migration`.

## 10. Testing strategy

- **Unit tests** — mappers (`map_role` happy/missing-field), `OldLmsClient` (200/401/429/5xx via `responses`), `error_capture` (frame filter), pagination math, throttle scope keys.
- **Integration tests** — spin up the old-side app in a pytest-django fixture with seeded Roles, hit endpoints with a real token, run a full job end-to-end against a sqlite new DB; assert counts, IDMap, run logs.
- **Idempotency test** — run a completed job twice, assert zero new rows / zero new errors.
- **Resume test** — kill mid-batch (process kill in test), restart, assert resume from saved `last_cursor`.
- **Failure injection test** — patch `map_role` to raise on a specific old_pk, assert `MigrationErrorRecord` has correct `source_file`, `source_line`, `source_function`, and that the rest of the page still processes.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Old-side `Role` schema differs from new-side | Phase 0 captures sample payload; mapper unit tests pin the contract |
| Simulation classedge not API-runnable as-is | Phase 0 explicitly boots it and curls `/api/migration/health/` before any other work begins |
| Error capture grabs Django/Celery frames | Dedicated unit test enforces project-frame filter |
| Beat task collides with existing schedule | New task name is unique; gated by `MIGRATION_ENABLED=False` default |
| HTMX polling load | Single annotated queryset for the table; poll interval configurable |
| Operator confused about which old LMS is targeted | Dashboard header always shows base URL, token label, last health timestamp |
| Token leak | Stored hashed; shown once on creation; `is_active` flag for revocation |

## 12. Acceptance criteria (whole plan)

1. `simulation-lms/classedge` exposes `/api/migration/health/` and `/api/migration/roles/role/` with token auth + throttling + cursor pagination, verified by `curl` and pytest.
2. Classedge-Ai has the `migration` app with all four models, migrations forward+backward clean.
3. End-to-end run: roles fully migrate from simulation to new DB. Count parity. IDMap populated.
4. Re-run is idempotent: zero new rows, zero new errors.
5. Kill mid-batch then restart: resumes from saved cursor, no duplicates.
6. Dashboard at `/operations/migration/` shows live progress without page reloads.
7. Deliberate failure (e.g., delete an IDMap parent FK) produces an error record showing correct `source_file`, `source_line`, `source_function`, payload excerpt, and a working `vscode://` deep link.
8. Dry-run toggle prevents writes but still records what would have happened.
9. Operator runbook at `docs/migration/runbook-foundation.md` takes a fresh developer from zero to a successful Role migration on the simulation source in under 30 minutes.

## 13. Out of scope (next plans, in order)

1. Accounts migration (`CustomUser`, `Profile`, `LoginHistory`, `APIKey`).
2. Classroom, Calendars, Coil.
3. Assessment phases 7a–7m per `docs/migration/2026-05-20-assessment-models-addendum.md`.
4. Message, Social, Logs.
5. Media files pipeline per `docs/migration/2026-05-20-media-files-subplan.md`.
6. SNCFI production run.
7. NewHope production run.
