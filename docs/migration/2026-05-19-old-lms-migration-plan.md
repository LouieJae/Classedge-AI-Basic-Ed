# Old LMS → Classedge-AI Data Migration Plan

**Date:** 2026-05-19
**Status:** Draft — not yet implemented
**Author:** brainstorm session

---

## 1. Goal

Perform a **one-time full data migration** from the old LMS (simulation-lms / classedge / sncfilms / classedge-newhope deployments) to the new **Classedge-AI** LMS.

- Migration runs over time (days/weeks), not as a single cutover
- Celery workers on the new side pull data from the old side via REST API
- Old and new systems are on **separate hosts** — no direct DB connection
- Migration must be **throttled** so the new LMS is not overloaded
- After migration completes and is verified, the old LMS is retired

---

## 2. Schema Comparison Summary

Comparing `classedge-newhope` (most recent old variant) vs `Classedge-Ai`:

| App | Verdict | Notes |
|------|---------|------|
| classroom | Identical | 1:1 copy |
| roles | Identical | 1:1 copy |
| mobile / rms | Empty in both | Skip |
| coil | Identical | 1:1 copy |
| message | Identical | 1:1 copy |
| social_media | Minor | New `GroupMessageRead` table (no source — skip) |
| calendars | Moderate | New optional FKs: `department`, `subject` → leave NULL on migrated rows |
| logs | Moderate | `Notification.entity_id` widened `Integer → CharField`; `UserActivityLog` **dropped** in new schema |
| accounts | Moderate | New fields `legal_update_required`, `accepted_eula_version`, `accepted_nda_version`, `accepted_privacy_version` — populate from old `TermAndAgreement` |

**Overall:** ~90% schema overlap. Per-model mapper functions needed for ~10% of cases. No heavy restructuring required.

---

## 3. Architecture

```
┌─────────────────────────┐                 ┌────────────────────────────┐
│   OLD LMS (production)  │                 │     Classedge-AI (new)     │
│                         │                 │                            │
│  migration_api app      │   HTTPS + Token │  migration app             │
│  ├─ /api/migration/...  │ ◄────────────── │  ├─ MigrationJob model     │
│  ├─ Cursor pagination   │                 │  ├─ IDMap model            │
│  ├─ DRF read-only views │                 │  ├─ Celery tasks per model │
│  └─ Rate-limit throttle │                 │  └─ Celery beat scheduler  │
└─────────────────────────┘                 └────────────────────────────┘
```

### Why this shape

- One isolated app per side → easy to delete after migration completes
- Token auth → only the new LMS can read; not a public API
- Cursor pagination (by `pk` or `updated_at`) → stable over long migrations even if old data changes
- Celery + beat → naturally throttled, resumable, observable

---

## 4. Components

### 4.1 On the Old LMS — `migration_api` app

**Models:**
- `MigrationToken(token, label, created_at, last_used_at, is_active)` — auth for the new LMS to call in

**Endpoints** (DRF, read-only, token-auth, throttled):

```
GET /api/migration/health/                    → sanity check
GET /api/migration/<app>/<model>/?cursor=&limit=500
    e.g. /api/migration/accounts/customuser/
         /api/migration/classroom/teacher-attendance/
         /api/migration/calendars/event/
         ... one per migratable model
```

Response shape:
```json
{
  "results": [ {...model fields, FKs as old pks...}, ... ],
  "next_cursor": "12345",
  "has_more": true,
  "total_estimated": 50000
}
```

**Throttling:** `rest_framework.throttling` — e.g. 30 req/min per token. Configurable per endpoint for heavy models.

### 4.2 On Classedge-AI — `migration` app

**Models:**

```python
class MigrationJob(models.Model):
    app_label = CharField        # e.g. "accounts"
    model_name = CharField       # e.g. "CustomUser"
    last_cursor = CharField(null=True)
    status = CharField(choices=[pending, running, paused, completed, failed])
    rows_fetched = IntegerField(default=0)
    rows_written = IntegerField(default=0)
    rows_skipped = IntegerField(default=0)
    error_count = IntegerField(default=0)
    last_error = TextField(blank=True)
    started_at / updated_at / completed_at

class IDMap(models.Model):
    app_label = CharField
    model_name = CharField
    old_pk = CharField           # CharField to support int + UUID
    new_pk = CharField
    class Meta:
        unique_together = [("app_label", "model_name", "old_pk")]
        indexes = [Index(fields=["app_label", "model_name", "old_pk"])]
```

**Tasks:**
- `migrate_model_batch(job_id)` — fetch one page, transform, write, advance cursor
- `run_migration_pipeline()` — orchestrator; respects dependency order
- `verify_migration(app, model)` — count + sample-checksum comparison

**Settings:**
```python
MIGRATION_OLD_LMS_BASE_URL = "https://old-lms.example.com"
MIGRATION_OLD_LMS_TOKEN = env("MIGRATION_TOKEN")
MIGRATION_BATCH_SIZE = 500
MIGRATION_BATCH_INTERVAL_SECONDS = 30   # celery beat tick
MIGRATION_DRY_RUN = False
```

### 4.3 Per-model mapper functions

Each model gets a small function on the new side:

```python
def map_customuser(payload: dict) -> dict:
    return {
        "username": payload["username"],
        "email": payload["email"],
        ...
        "legal_update_required": False,
        "accepted_eula_version": payload.get("terms_version") or "0.0.0",
        "accepted_nda_version": "0.0.0",
        "accepted_privacy_version": "0.0.0",
    }
```

FK fields are rewritten via `IDMap` lookup (e.g. `profile.role_id = IDMap.get("roles", "role", old_role_id)`).

---

## 5. Migration Order (dependency-driven)

| Phase | App / Model | Notes |
|------|-------------|-------|
| 1 | `roles.Role` | No FK deps |
| 2 | `accounts.CustomUser` | Depends on Role indirectly |
| 3 | `accounts.Profile` | FK → CustomUser, Role |
| 4 | `accounts.LoginHistory`, `APIKey` | FK → User |
| 5 | `classroom.*` (Teacher_Attendance, Screenshot, Classroom_mode) | FK → User/Subject |
| 6 | `calendars.Holiday`, `Event`, `Announcement` | `department`/`subject` FKs left NULL |
| 7 | **Assessment / Question / Activity data** | Largest volume — heavy throttling |
| 8 | `message.*` | FK → User |
| 9 | `social_media.*` | FK → User (skip `GroupMessageRead` — no source) |
| 10 | `coil.CoilPartnerSchool` | Standalone |
| 11 | `logs.*` | Largest volume, lowest urgency. `UserActivityLog` **skipped entirely** (model removed in new schema) |

---

## 6. Open Decisions / TBD

These are decisions to confirm tomorrow before implementation begins:

1. **UserActivityLog**: skip entirely **OR** archive raw JSON to a new `migration.LegacyAuditLog` table?
2. **Assessment data priority**: stick with dependency order (users first), or fast-track assessment data once users are migrated?
3. **Old variant source of truth**: is the production DB `classedge-newhope`, `classedge`, or `sncfilms`? Or do all three need to be migrated into a single new tenant?
4. **Tenant strategy**: if multiple old deployments → single new DB, do we need namespacing (prefixes on usernames, etc.)?
5. **Media files / uploads**: any `FileField` / `ImageField` data — does the new side fetch the file URL, or stream the binary? (Not yet planned.)
6. **Cutover**: how will the old LMS be put into read-only mode during the final sync? Or is "data freeze" not required?
7. **Throttle numbers**: starting values for `BATCH_SIZE` and `BATCH_INTERVAL_SECONDS`.

---

## 7. Implementation Phases (high-level)

### Phase A — Foundation (old side)
1. Create `migration_api` app
2. Add `MigrationToken` model + admin
3. Build base paginated read viewset class
4. Add 1 endpoint as proof-of-concept (`Role`)
5. Add throttling, deploy to staging

### Phase B — Foundation (new side)
1. Create `migration` app
2. Add `MigrationJob` + `IDMap` models + migrations
3. Build base `migrate_model_batch` Celery task
4. Build mapper for `Role`, run end-to-end against staging old LMS
5. Verify IDMap, idempotency, resume after crash

### Phase C — Roll out per app
For each app in the order from §5:
1. Expose endpoints on old LMS
2. Write mapper(s) on new LMS
3. Write tests (unit per mapper, integration per app)
4. Dry-run on staging
5. Run on production with low throttle, monitor
6. Verify counts + checksums

### Phase D — Finalisation
1. Final delta sync (everything created since last run)
2. Verification report (per-model count parity)
3. Old LMS → read-only mode
4. DNS / routing cutover
5. Archive old LMS DB dump
6. Delete `migration_api` app from old LMS (or just turn off the host)

---

## 8. Testing Strategy

- **Unit tests:** one per mapper function — known old payload → expected new field dict
- **Integration tests:** seed a small fixture into a staging old-LMS DB → run full migration in dry-run + real mode → assert row counts, FK integrity, sampled field values
- **Idempotency tests:** re-run a completed batch → assert no duplicates, no errors
- **Resume tests:** kill mid-batch → restart → assert correct resume cursor

---

## 9. Risks

| Risk | Mitigation |
|------|-----------|
| Old LMS overloaded by migration reads | Throttle on old side, exponential backoff on new side |
| New LMS overloaded by writes | Celery beat interval + small batch size; can pause via `MigrationJob.status = paused` |
| FK rewiring bugs → orphaned rows | IDMap with unique constraints; verification phase catches gaps |
| Data created on old LMS during migration | Cursor by `updated_at` (not pk) for tables that change; final delta sync before cutover |
| Schema drift between old variants | Pick one source variant per migration run; if multi-source, run pipeline separately per source with tenant tagging |
| Media files not migrated | Add explicit phase; treat as separate pipeline (S3-style sync) |

---

## 10. Next Steps (tomorrow)

1. Answer the 7 open decisions in §6
2. Confirm migration order + throttle numbers
3. Use `superpowers:writing-plans` to convert this into an executable implementation plan
4. Begin Phase A
