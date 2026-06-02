# Migration Foundation — Operator Runbook

This runbook covers the foundation pipeline (Roles only, simulation classedge target). For per-app expansions, see the matching follow-up plans.

## 1. Prerequisites

- Old LMS source: `/home/classify/Desktop/Projects/simulation-lms/classedge`
- New LMS: `/home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai`
- Redis running (Celery broker)
- The Classedge-Ai venv at `env/` is shared by both projects in this development setup

## 2. Generate a migration token (one-time per environment)

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
/home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/env/bin/python manage.py shell -c "from migration_api.models import MigrationToken; p, t = MigrationToken.objects.create_token(label='dev'); print('TOKEN:', p)"
```

Copy the printed token — it is not retrievable later (only the SHA-256 hash is stored).

## 3. Configure the new side

Add to `.env`:

```
MIGRATION_OLD_LMS_BASE_URL=http://127.0.0.1:8001
MIGRATION_OLD_LMS_TOKEN=<paste>
MIGRATION_ENABLED=False     # leave False until you are ready to start
MIGRATION_DRY_RUN=False
```

## 4. Boot

Terminal 1 (old side):
```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
/home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/env/bin/python manage.py runserver 127.0.0.1:8001
```

Terminal 2 (new side worker):
```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
env/bin/celery -A lms worker -l info
```

Terminal 3 (new side beat):
```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
env/bin/celery -A lms beat -l info
```

Terminal 4 (new side web):
```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
env/bin/python manage.py runserver
```

## 5. Start the migration

1. Log in as superuser.
2. Visit `/operations/migration/`.
3. Confirm the header shows the correct source URL.
4. Click **Start pipeline**.
5. Set `MIGRATION_ENABLED=true` in `.env` and restart Celery beat so the orchestrator ticks every `MIGRATION_BATCH_INTERVAL_SECONDS` (default 30).

## 6. Monitor

- Overview table polls every 3s — watch progress bar and rate.
- Click a job to see live batch logs.
- Click error count badges to drill into per-row failures.

## 7. Triage an error

1. Open the error from the inspector at `/operations/migration/errors/`.
2. The drawer shows: source file + line, field, expected, actual, payload excerpt, full traceback.
3. Click **open in VS Code** for the exact line of the failing code.
4. Fix the underlying issue. Click **Retry this row** to re-run just that PK. On success, the error auto-resolves.

## 8. Pause / resume / restart

- **Pause all** — flips all `pending`/`running` jobs to `paused`. Workers finish current batch then stop.
- **Resume all** — flips `paused` → `running`.
- **Restart from zero** (per-job, in detail page) — clears cursor and counters. Requires `confirm=yes` POST parameter.

## 9. Dry-run rehearsal

Toggle **dry-run** on the overview before starting the pipeline. Writers will short-circuit before `save()` but run logs still record what would have happened. Use this to time a run without changing the new DB.

Note: the in-memory dry-run toggle resets on Django process restart. For persistent dry-run, set `MIGRATION_DRY_RUN=True` in `.env`.

## 10. Verify completion

In the overview, click **Verify** on a completed job. The job's `last_verification` JSON shows `count_parity` and `idmap_complete`. Both must be `true` before the foundation is considered done.

You can also inspect via the Django shell:
```bash
env/bin/python manage.py shell -c "from migration.models import MigrationJob; print(MigrationJob.objects.get(app_label='roles', model_name='Role').last_verification)"
```

## 11. Rollback

Foundation is reversible:
```bash
env/bin/python manage.py shell -c "from migration.models import *; from roles.models import Role; MigrationJob.objects.all().delete(); IDMap.objects.all().delete(); MigrationErrorRecord.objects.all().delete(); MigrationRunLog.objects.all().delete(); Role.objects.all().delete()"
```

This drops every Role row created by the pipeline plus all tracking state. **Use only on test environments — this deletes ALL roles.**

## 12. Pointing at SNCFI or NewHope

The same code base targets any old LMS that has the `migration_api` app installed. Procedure:

1. Install `migration_api` in the target LMS (follow the foundation plan's Phase A tasks against that codebase).
2. Mint a token on the target LMS (step 2 of this runbook).
3. Set `MIGRATION_OLD_LMS_BASE_URL` and `MIGRATION_OLD_LMS_TOKEN` in `.env` on the new side.
4. Reset state (step 11) if you are starting clean, or leave intact to resume.
5. Start the pipeline (step 5).

## 13. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 401 errors in dashboard, jobs auto-pause | Wrong/expired token | Regenerate token, update `.env`, restart workers |
| 429 errors / throttled | Hit the old-side rate limit | Wait, or raise `migration_default` in old-side settings |
| Progress bar stuck at 0% | `MIGRATION_ENABLED=False` or beat not running | Set to True, restart beat |
| `source_file` empty in errors | Frame filter excluded all frames | Investigate test for `error_capture`; project frames must live under `BASE_DIR` |
| Tests pass but live run fails on permissions M2M | Old-side and new-side Permission tables differ | Confirm `auth_permission` has matching `(app_label, codename)` rows on both sides |

## 14. Test the whole pipeline locally

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
env/bin/python -m pytest migration/ -v
# Expected: 59 passed, 2 skipped (the E2E tests opt-in via MIGRATION_E2E=1)
```

For a real end-to-end check against a running simulation server, see `migration/tests/test_e2e_roles_role.py` for the procedure.
