# Sub-plan — Media & File Migration

**Date:** 2026-05-20
**Parent doc:** [2026-05-19-old-lms-migration-plan.md](./2026-05-19-old-lms-migration-plan.md) (resolves open decision §6 item 5)
**Related:** [2026-05-20-assessment-models-addendum.md](./2026-05-20-assessment-models-addendum.md) §4
**Status:** Draft

---

## 1. Why a separate pipeline

The JSON migration pipeline in the parent plan moves rows efficiently but cannot move bytes — `FileField` / `ImageField` columns only carry a relative path string. The actual files live in the old LMS's `MEDIA_ROOT` (currently a local filesystem under `media/`). The new LMS will need the same files at compatible paths before any feature that renders them works.

Treating this as a **separate, parallel pipeline** keeps the row migration fast and unblocks Phase 7 of the parent plan: rows migrate now with a `legacy_file_url` placeholder, files backfill independently.

---

## 2. Scope — files to migrate

Inventory from the codebase (~30 `FileField`/`ImageField` columns). Grouped by criticality:

### 2.1 Critical (blocks features on launch)
| Domain | Field(s) | Old MEDIA subdir |
|------|---------|------------------|
| accounts | `CustomUser.student_photo`, `Certificate.file`, `DisplayImage.image` | `profile/`, `certificate/`, etc. |
| activity | `Activity.activity_file_instruction`, `ActivityQuestion.question_instruction`, `QuestionChoice.choice_image`, `StudentActivity.file`, `RetakeRecordDetail.uploaded_file` | `ActivityFile/`, `uploads/` |
| module | `Module.file` | `module/` |
| subject | `Subject.subject_photo`, `SDG.photo` | `subjectPhoto/` |
| classroom | `Screenshot.image` | `Screenshot/` |

### 2.2 Important (degraded UX if missing)
| Domain | Field(s) | Old MEDIA subdir |
|------|---------|------------------|
| social_media | `Post.image`, `GroupMessage.file`, `GroupPhoto.photo` | `group_messages/`, `group_photos/` |
| message | `Message.file` | `chat_uploads/` |
| ai_content | `*.reference_file` | `uploads/` |
| central_content / received_central_content | textbook + module files, subject photos | varies |

### 2.3 Low priority / regeneratable
- Logos, templates, generated certificates that can be re-rendered from data.

---

## 3. Architecture

```
┌────────────────────────────────┐                   ┌────────────────────────────────┐
│         OLD LMS                 │                   │       Classedge-AI              │
│                                 │                   │                                 │
│  migration_api app              │  HTTPS (token)    │  migration app                  │
│   ├─ /media-manifest/           │ ◄──────────────── │   ├─ MediaFile model            │
│   └─ /media-blob/<path>         │     range reqs    │   ├─ Celery: fetch_media_batch  │
│                                 │                   │   └─ Celery beat                │
│  Files on local FS / S3         │                   │  Files on new MEDIA_ROOT / S3   │
└────────────────────────────────┘                   └────────────────────────────────┘
```

Two cooperating pieces:

1. **Manifest endpoint** lists every file the old LMS knows about (path, size, sha256, mtime, owning model+pk+field). Cursor-paginated.
2. **Blob endpoint** streams a single file's bytes by relative path. Supports HTTP `Range` so a failed transfer can resume mid-file.

The new side records each entry in a `MediaFile` table, downloads to the matching path under the new `MEDIA_ROOT`, verifies the sha256, and — if the owning row already exists locally — patches the model's FileField to point at the new path. If the row doesn't exist yet (row migration hasn't reached it), it leaves the file in place and lets the row mapper find it later.

---

## 4. Components

### 4.1 Old side — extend `migration_api`

**New endpoints:**
```
GET /api/migration/media-manifest/?cursor=&limit=500
GET /api/migration/media-blob/?path=<urlencoded-relative-path>
```

Manifest entry shape:
```json
{
  "path": "ActivityFile/q_123/instruction.pdf",
  "size": 184231,
  "sha256": "9af1...",
  "mtime": "2025-11-02T08:14:11Z",
  "owner": {"app": "activity", "model": "ActivityQuestion", "pk": 4421, "field": "question_instruction"}
}
```

Owner enrichment is derived from each `FileField`'s `upload_to` plus a reverse index (one-time scan at deploy of `migration_api`). Files that no row references are still listed but flagged `"orphan": true`.

**Throttling:** separate scope from row migration — e.g. 10 blob req/sec, 50 MB/sec aggregate. Blob endpoint must stream (not buffer) to avoid OOM on large videos.

### 4.2 New side — extend `migration` app

```python
class MediaFile(models.Model):
    old_path = CharField(unique=True)
    new_path = CharField(blank=True)
    size = BigIntegerField()
    sha256_expected = CharField(max_length=64)
    sha256_actual = CharField(max_length=64, blank=True)
    owner_app = CharField(blank=True)
    owner_model = CharField(blank=True)
    owner_old_pk = CharField(blank=True)
    owner_field = CharField(blank=True)
    status = CharField(choices=[
        "discovered", "downloading", "downloaded",
        "verified", "linked", "orphan", "failed", "skipped"
    ])
    attempts = IntegerField(default=0)
    last_error = TextField(blank=True)
    discovered_at / downloaded_at / linked_at
```

**Tasks:**
- `discover_media_manifest()` — paginate the manifest, upsert `MediaFile` rows.
- `download_media_batch(limit)` — pick N `discovered`/`failed` rows, fetch via Range, write to `MEDIA_ROOT/<old_path>` (preserve subpath so existing `upload_to` callables match), verify sha256, mark `verified`.
- `link_media_to_rows(limit)` — for `verified` rows whose owner row exists locally (resolved via IDMap), update the model's FileField column to the new path, mark `linked`.
- `verify_media()` — counts, missing files, sha mismatches, unlinked rows.

**Settings:**
```python
MEDIA_MIGRATION_BATCH_SIZE = 20         # files per beat tick
MEDIA_MIGRATION_MAX_BYTES_PER_TICK = 50_000_000
MEDIA_MIGRATION_INTERVAL_SECONDS = 30
MEDIA_MIGRATION_PARALLEL_DOWNLOADS = 4
MEDIA_MIGRATION_RETRY_LIMIT = 5
```

### 4.3 Coordination with row migration

Row mappers write **the raw old path string** into the FileField (Django stores FileFields as strings under the hood). Because the new side preserves the same subdirectory layout, the file becomes valid the moment the media pipeline drops the bytes in place — no row-rewrite needed in the common path.

For the edge case where storage backends differ (e.g. new LMS is on S3), the linker task is responsible for rewriting the path string after upload.

---

## 5. Path strategy

Two viable options:

**Option A — preserve paths verbatim** (recommended)
- New `MEDIA_ROOT` mirrors the old subdir layout exactly.
- No model rewrites; existing `upload_to` callables keep working for *new* uploads because they generate the same shape.
- Cost: any cross-tenant collisions (if multiple old variants merge into one new LMS) need a tenant prefix injected at copy time.

**Option B — rehash on the new side**
- New side generates a fresh path from `upload_to` for each file.
- Row mapper must rewrite the FileField column after the linker runs.
- More work, but mandatory if storage layout has changed (e.g. switching to per-tenant buckets).

Decision required before implementation. Default to A unless the new LMS already runs on a different storage layout.

---

## 6. Order of operations relative to parent plan

```
Parent Phase A/B  →  add manifest endpoint + MediaFile model (no downloads yet)
Parent Phase C    →  row migration runs; FileField columns hold old paths (broken links OK)
Media Phase M1    →  discover_media_manifest fills MediaFile table
Media Phase M2    →  download_media_batch runs continuously, throttled
Media Phase M3    →  link_media_to_rows runs in parallel, gated on IDMap
Parent Phase D    →  delta sync also re-runs manifest discovery for files changed since last run
Final cutover     →  verify_media reports 100% linked or explicit skips
```

Media Phases M1–M3 are background work — they don't block row migration progress.

---

## 7. Failure handling

| Failure | Handling |
|---------|---------|
| Network drop mid-file | HTTP Range resume; if attempts > limit, mark `failed`, alert |
| sha256 mismatch | Delete partial, retry once, then `failed` |
| File on disk but no DB row references it | `orphan` — keep for one verification cycle, then archive separately |
| DB row references a missing file | After full run completes, list as a verification finding (not a migration failure — old LMS may have had broken links too) |
| Disk full on new side | Pause beat; downloads idempotent on resume |
| Old LMS file deleted between manifest and download | Mark `skipped`, log |

---

## 8. Storage sizing

Before kickoff, run the manifest in dry-run to compute:
- Total file count
- Total bytes
- Distribution by subdir (find the heaviest tables — likely `ActivityFile/` and `Screenshot/`)
- Largest single file (sets streaming chunk size + timeout)

This output drives provisioning of the new `MEDIA_ROOT` and the throttle numbers in §4.2.

---

## 9. Verification

- `MediaFile.count(status="linked") + count(status="orphan") == manifest total`
- For 1% sample: download from new side, sha256 matches `sha256_expected`
- For every `FileField` column: query `WHERE field IS NOT NULL AND field NOT IN (linked paths)` → must be empty
- Spot-check: open 20 random rows of each critical model in the UI, confirm file renders

---

## 10. Open questions

1. **Storage backend on the new side** — local FS, S3, or other? Determines path strategy (§5) and informs whether the manifest needs to record content-type explicitly.
2. **Multi-tenant collisions** — if `classedge-newhope` + `sncfilms` merge, do we prefix paths (`/newhope/...`, `/sncfilms/...`) or rely on UUIDs already present in `upload_to`?
3. **Large video / Screenshot data** — is full migration required, or is a cutoff date acceptable (e.g. only files newer than 12 months)?
4. **Generated/derivable assets** (thumbnails, generated certificates) — migrate, or regenerate on the new side from source data?
5. **Old-side egress cost** — if old LMS files live on S3, who pays the bandwidth bill for the bulk pull?

---

## 11. Next steps

1. Resolve §10 open questions.
2. Run the manifest endpoint dry-run on staging to get the sizing numbers in §8.
3. Confirm path strategy (§5).
4. Implement manifest endpoint alongside Phase A of the parent plan so it's ready when row migration starts.
