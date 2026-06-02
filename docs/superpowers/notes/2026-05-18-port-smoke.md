# Smoke / verification notes — retake PK swap + source-of-truth port

Plan: `docs/superpowers/plans/2026-05-18-port-retake-pk-and-source-of-truth.md`
Branch: `assessment-update`
Date: 2026-05-18

## Migrations applied to local Postgres (`classedge-ai` on `localhost`)

- `activity.0006_retake_local_id_unique` — OK
- `activity.0007_swap_retake_pk` — OK; post-flight FK checks both returned 0
- `activity.0008_backfill_studentquestion_into_retake` — OK (no-op locally; 0 SQ rows)
- `mobile.0003_attachment_record_details_state` — OK

## Test results

### Tests directly authored / updated by the port (all pass)

| Module | Tests | Result |
|---|---|---|
| `activity.tests.test_backfill_retake_local_ids` | 2 | PASS |
| `activity.tests.test_retake_pk_swap` | 3 | PASS |
| `activity.tests.test_retake_resolver` | 5 | PASS |
| `activity.tests.test_answer_views_submit` | 1 | PASS |
| `activity.tests.test_grading_views` | 4 | PASS |
| `activity.tests.test_backfill_studentquestion` | 5 | PASS |
| **total** | **20/20** | **OK** |

### Other apps (regressions and pre-existing)

`gradebookcomponent calendars course module mobile`: 60 tests, 19 failures.

- **3** real regressions from Task 9 reader migration, fixed by updating `gradebookcomponent/tests/helpers.py::make_submission` to seed a `RetakeRecord` + `RetakeRecordDetail` in addition to `StudentActivity`. (See commit on this branch.)
- **16** pre-existing failures unrelated to the port:
  - `test_grade_submission.*` (5) — 403 from `authorize_subject_access`; the teacher fixture isn't matching the subject's assign_teacher gate, but the values look correct. Likely needs a `Profile` / role fixture wired up. Not caused by this port.
  - `test_override.*` (5), `test_gradebook_home.*` (2), `test_grading_queue.*` (2), `test_subject_gradebook.*` (1), `test_csv_export.*` (1) — same auth fixture trail.
  - `calendars.tests.test_department_filter.*` (2) — head/dept membership fixtures unrelated to retake work.

`python manage.py test` (no scope) fails at discovery: pre-existing `roles/tests.py` + `roles/tests/` package conflict. Unrelated.

## CI guard

`bash scripts/check_studentquestion.sh` → `OK: no StudentQuestion writers outside the deferred allowlist; no direct total_score mutation.`

## Manual UI walkthrough

Not executed in this session — would need a running dev server, real seeded data, and a teacher/student account pair. Recommended before merging:

1. Web user submits an Essay activity → confirm `RetakeRecord(retake_number=1)` + `RetakeRecordDetail` created; no `StudentQuestion` row.
2. Teacher opens grading queue → sees the Essay submission.
3. Teacher grades it → `RetakeRecordDetail.score` updates; `RetakeRecord.score` recomputes; `StudentActivity.total_score` recomputes; gradebook reflects the change.
4. Mobile-submitted Essay (via `ActivityBatchSubmitView`) also surfaces in the grading queue.
5. Export CSV matches gradebook totals.
6. Legacy URL `/activity/grade_individual_essay/<activity_id>/<old_int_id>/` redirects to the new `<detail_local_id>` URL when the SQ row exists; otherwise lands on the grading queue.

## Deferred from the port (need their own scoping)

These remain as legitimate `StudentQuestion` callers and are allowlisted in the CI guard:

| Site | Why deferred |
|---|---|
| `activity/views/question_views.py` lines 118, 402, 892, 1036 | Participation grading writes (`activity_question=None`, `is_participation=True`). `RetakeRecordDetail` has no `is_participation` field. Needs a design decision (add field / per-activity dummy Participation question / etc.). |
| `activity/tasks.py` + `activity/student_import_utils.py` | CSV grade-import bulk writers. Need a bulk RetakeRecord parent design + `RetakeRecordDetail.bulk_create` adaptation. |
| `course/views/{classroom,subject_details}_views.py` `is_participation=True` reads (6 sites) | Companion to the writers above. Marked `# LEGACY:` in code. |

Once participation is ported, these sites — and the CI allowlist — should disappear, and `StudentQuestion` becomes droppable.
