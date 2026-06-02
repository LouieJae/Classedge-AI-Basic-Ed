# Pre-flight findings — 2026-05-20

- Simulation Role count: 9
- Sample row: [{'id': 2, 'name': 'Registrar', 'created_at': datetime.datetime(2026, 1, 8, 6, 4, 55, 919438, tzinfo=datetime.timezone.utc), 'updated_at': None}, {'id': 3, 'name': 'Admin', 'created_at': datetime.datetime(2026, 1, 8, 6, 4, 56, 88622, tzinfo=datetime.timezone.utc), 'updated_at': None}, {'id': 4, 'name': 'Academic Director', 'created_at': datetime.datetime(2026, 1, 8, 6, 4, 56, 95935, tzinfo=datetime.timezone.utc), 'updated_at': None}]
- `manage.py check` passes: yes (verified using Classedge-Ai venv, one harmless deprecation warning)
- Role model fields match plan expectation: yes
- Python interpreter used: /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/env/bin/python

## Live smoke test (Task 9) — 2026-05-20

- Server booted: `python manage.py runserver 127.0.0.1:8001 --noreload` (background)
- `GET /api/migration/health/` with token → 200, body: `{"ok":true,"db_ok":true,"server_time":"2026-05-20T01:58:22+00:00","version":"1"}`
- `GET /api/migration/roles/role/?limit=3` with token → 200, returned 3 roles (Student, Registrar, Admin), `next_cursor="3"`, `has_more=true`, `total_estimated=9`
- `GET /api/migration/health/` without token → 401
- Permission codename M2M correctly serialized as `[{"app_label":..., "codename":...}]`
- Response JSON confirmed snake_case (`next_cursor`, `total_estimated`, `app_label`)
- Roles in sim DB: Student (id=1), Registrar (id=2), Admin (id=3), Academic Director (id=4), … 9 total

**Phase A complete.** 24/24 pytest tests pass on the old side. Endpoints proven over HTTP with token auth, throttling rates configured (30/min default, 10/min heavy), cursor pagination working.

## End-to-end run (Task 29) — 2026-05-20

Live run against simulation server via shell (`migrate_model_batch.run(job_id=...)`):

| Metric | Value |
|---|---|
| Total Role rows migrated | 9 / 9 |
| Wall-clock duration | 0.38 s |
| Batches required | 1 (fit in one 500-row page) |
| Rows errored | 0 |
| RunLog entries | 1 |
| IDMap entries created | 9 |
| `verify_migration` count_parity | true |
| `verify_migration` idmap_complete | true |

**Idempotency re-run:** Reset job (status=running, last_cursor='') and ran again — 0 new rows, 0 new IDMap entries, 0 new errors. Idempotency confirmed.

## Failure injection check (Task 30) — 2026-05-20

Registered a synthetic mapper that raises `MissingFKError("nonexistent","Thing", old_pk=2, field_name="fake_field")` for pk=2 only.

Outcome:
- `rows_written = 8`, `rows_errored = 1` (the one synthetic failure)
- 1 `MigrationErrorRecord` created with:
  - `category="missing_fk"`, `old_pk="2"`, `field="fake_field"`
  - `expected="IDMap nonexistent.Thing old_pk=2"`, `actual="not found"`
  - `source_function="buggy_mapper"`, `source_line=23`
  - `source_file="<string>"` (heredoc-exec artifact — real mappers in `.py` files produce real paths; `test_capture_source_line_points_at_project_frame` proves this)
  - `payload_excerpt` contains the full Role payload (id=2, name="Registrar", 50+ permission codenames)

Error drawer render check via Django test client `GET /operations/migration/errors/1/`:
- Status 200 with all of: category badge, old_pk, field name, expected/actual, source_function, `:23` line ref, `vscode://file...` deep link, payload (`Registrar`), Retry button, Mark resolved button.

Synthetic error cleaned up post-check.

---

## Final test totals

- Old side `migration_api/`: **24 passed**
- New side `migration/`: **59 passed, 2 skipped** (opt-in E2E)
- Combined: **83 passed**
- `manage.py check`: clean on both sides
- Live E2E: 9/9 roles migrated, count_parity=true, idmap_complete=true, idempotent on re-run
- Failure injection: error captured with all expected fields, drawer renders correctly

**Foundation plan: COMPLETE.**
