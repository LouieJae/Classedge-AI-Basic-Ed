# Port Retake PK Swap + Source-of-Truth Unification from HCCCI-LMS

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring this repo (HCCCI-Frontend/Classedge-Ai, web-ahead) in line with HCCCI-LMS (mobile-ahead) on two coupled workstreams: (a) make `local_id` the primary key on `RetakeRecord` / `RetakeRecordDetail`; (b) make `RetakeRecord`/`RetakeRecordDetail` the single source of truth for student answers, removing all `StudentQuestion` writes.

**Architecture:** Two phases. Phase 1 swaps the PK type (`bigint` → `varchar(36)` cuid) on both retake tables and rewrites the two dependent FK columns (`activity_retakerecorddetail.retake_record_id` and `mobile_attachment.record_details_id`) in a single transactional migration, mirroring the LMS spec. Phase 2 rewrites all `StudentQuestion` writers (web `answer_views`, `batch_save_views`, `score_admin_views`, `participation_views`, `mobile/views/student_activity_views.py`) to write `RetakeRecord(retake_number=1)` + `RetakeRecordDetail` instead, migrates grading/export/gradebook/calendar/course/module readers to read from the retake models, and backfills historical `StudentQuestion` rows into synthetic retake records. `StudentQuestion` is left in place as a frozen legacy table (drop is a follow-up).

**Tech Stack:** Django 4.x, Postgres (Neon dev DB) + SQLite (local dev), `cuid==0.4`, DRF.

**Source-of-truth references (in `/home/classify/Desktop/Projects/HCCCI-LMS/`):**
- Spec PK swap: `docs/superpowers/specs/2026-05-06-retake-pk-local-id-design.md`
- Spec source-of-truth: `docs/superpowers/specs/2026-05-12-retake-as-single-source-design.md`
- Audit note: `docs/superpowers/notes/2026-05-12-retake-unification-audit.md`
- Runbook: `docs/superpowers/runbooks/2026-05-06-retake-pk-swap-runbook.md`
- Reference code (canonical, web-behind): `classedge/{activity,mobile,gradebookcomponent,course,calendars,module,simulation}/`

**Baseline divergence (this repo vs. LMS):**
- This repo has a **squashed activity migration history** (5 migrations) vs LMS's 41. Activity, StudentActivity already use integer PKs here — no prior PK swap landed. Retake migration numbering starts fresh from this repo's tip.
- This repo has `RetakeRecord.choice_order = JSONField(default=dict, blank=True)` which LMS does not — **must be preserved**.
- LMS `RetakeRecordDetail.save()` has stray `print()` debug statements — **do not port them**.
- This repo has features LMS does not (`assessment_views.py`, `ai_content/`, `at_risk/`, `central_content/`, `gamification/`, `ide/`, `rag_tutor/`, etc.). Tasks below touch only the retake/grading/gradebook surface; do not refactor unrelated apps.

---

## Pre-flight scoping (Task 0)

### Task 0: Audit grep — confirm scope on THIS repo

**Files:** none yet (read-only audit).

- [ ] **Step 1: Confirm `cuid` is installed**

Run: `grep -c "^cuid==" requirements.txt`
Expected: `1` (already verified `cuid==0.4`).

- [ ] **Step 2: Capture every `StudentQuestion` writer in app code**

Run:
```bash
git grep -nE 'StudentQuestion\.objects\.(create|update_or_create|bulk_create|get_or_create)' -- 'activity/**.py' 'mobile/**.py' 'gradebookcomponent/**.py' 'course/**.py' 'calendars/**.py' 'module/**.py'
```
Expected: a non-empty list. Save the output to `docs/superpowers/notes/2026-05-18-port-audit.md` under section "Writers".

- [ ] **Step 3: Capture every `StudentQuestion` reader in app code**

Run:
```bash
git grep -nE 'StudentQuestion\.objects\.(filter|get|all|values|values_list|aggregate)' -- 'activity/**.py' 'mobile/**.py' 'gradebookcomponent/**.py' 'course/**.py' 'calendars/**.py' 'module/**.py'
```
Append to the same note under "Readers".

- [ ] **Step 4: Capture direct `total_score` mutations**

Run:
```bash
git grep -nE 'total_score\s*[+\-]?=' -- 'activity/**.py' 'gradebookcomponent/**.py'
```
Append under "total_score mutations".

- [ ] **Step 5: Confirm zero `int(retake_record_id)` / `int(retake_record_detail_id)` casts**

Run:
```bash
git grep -nE 'int\(retake_record_(id|detail_id)' -- '**.py' '**.html' '**.js'
```
Expected: zero hits. If any, list under "PK-int casts to remove" — they break post-cutover.

- [ ] **Step 6: Confirm cross-app FK targets**

Run:
```bash
git grep -nE 'record_details\s*=\s*models\.ForeignKey' -- 'mobile/**.py'
```
Expected: exactly one hit in `mobile/models/attachment.py`. If the FK lives elsewhere, list it under "Cross-app FKs" and add a corresponding step to Task 2.

- [ ] **Step 7: Commit the audit note**

```bash
git add docs/superpowers/notes/2026-05-18-port-audit.md
git commit -m "docs: pre-port audit of StudentQuestion + retake PK references"
```

---

## Phase 1 — PK swap (RetakeRecord, RetakeRecordDetail → cuid PK)

### Task 1: Backfill management command

**Files:**
- Create: `activity/management/commands/backfill_retake_local_ids.py`
- Test: `activity/tests/test_backfill_retake_local_ids.py`

- [ ] **Step 1: Write the failing test**

```python
# activity/tests/test_backfill_retake_local_ids.py
from django.core.management import call_command
from django.test import TestCase
from accounts.models import CustomUser
from activity.models import Activity, StudentActivity, RetakeRecord, RetakeRecordDetail, ActivityQuestion

class BackfillRetakeLocalIdsTests(TestCase):
    def setUp(self):
        self.student = CustomUser.objects.create(email="s@x.com")
        self.activity = Activity.objects.create(activity_name="A", max_score=10)
        self.sa = StudentActivity.objects.create(student=self.student, activity=self.activity)

    def test_backfills_null_local_id_on_both_models(self):
        rr = RetakeRecord.objects.create(student_activity=self.sa, student=self.student, activity=self.activity)
        # Null out the auto-populated local_id to simulate legacy rows
        RetakeRecord.objects.filter(pk=rr.pk).update(local_id=None)
        q = ActivityQuestion.objects.create(activity=self.activity)
        d = RetakeRecordDetail.objects.create(retake_record=rr, student=self.student, activity_question=q)
        RetakeRecordDetail.objects.filter(pk=d.pk).update(local_id=None)

        call_command("backfill_retake_local_ids")

        rr.refresh_from_db(); d.refresh_from_db()
        self.assertTrue(rr.local_id)
        self.assertTrue(d.local_id)

    def test_check_mode_exits_zero_when_clean(self):
        from django.core.management.base import SystemCheckError
        try:
            call_command("backfill_retake_local_ids", "--check")
        except SystemExit as e:
            self.assertEqual(e.code, 0)

    def test_idempotent_second_run_no_change(self):
        rr = RetakeRecord.objects.create(student_activity=self.sa, student=self.student, activity=self.activity)
        call_command("backfill_retake_local_ids")
        before = rr.local_id
        rr.refresh_from_db()
        call_command("backfill_retake_local_ids")
        rr.refresh_from_db()
        self.assertEqual(rr.local_id, before)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test activity.tests.test_backfill_retake_local_ids -v 2`
Expected: FAIL — `Unknown command: 'backfill_retake_local_ids'`.

- [ ] **Step 3: Write the command**

```python
# activity/management/commands/backfill_retake_local_ids.py
import cuid
import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from activity.models import RetakeRecord, RetakeRecordDetail

class Command(BaseCommand):
    help = "Backfill RetakeRecord / RetakeRecordDetail rows with NULL or empty local_id."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--check", action="store_true",
                            help="Exit 0 if zero gaps, 1 otherwise.")

    def handle(self, *args, **opts):
        gap = Q(local_id__isnull=True) | Q(local_id="")
        rr_gaps = RetakeRecord.objects.filter(gap)
        d_gaps = RetakeRecordDetail.objects.filter(gap)
        rr_n, d_n = rr_gaps.count(), d_gaps.count()
        self.stdout.write(f"RetakeRecord gaps: {rr_n}; RetakeRecordDetail gaps: {d_n}")

        if opts["check"]:
            sys.exit(0 if (rr_n == 0 and d_n == 0) else 1)
        if opts["dry_run"]:
            return

        with transaction.atomic():
            for rr in rr_gaps.only("pk"):
                RetakeRecord.objects.filter(pk=rr.pk).update(local_id=cuid.cuid())
            for d in d_gaps.only("pk"):
                RetakeRecordDetail.objects.filter(pk=d.pk).update(local_id=cuid.cuid())

        # Duplicate guard
        assert RetakeRecord.objects.values("local_id").distinct().count() == RetakeRecord.objects.count()
        assert RetakeRecordDetail.objects.values("local_id").distinct().count() == RetakeRecordDetail.objects.count()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test activity.tests.test_backfill_retake_local_ids -v 2`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add activity/management/commands/backfill_retake_local_ids.py activity/tests/test_backfill_retake_local_ids.py
git commit -m "feat(activity): add backfill_retake_local_ids command"
```

---

### Task 2: Phase A migration — add unique index on `local_id` (live-safe)

**Files:**
- Create: `activity/migrations/0006_retake_local_id_unique.py` (next number after current `0005_alter_activity_max_score.py`).

- [ ] **Step 1: Run the backfill (dev DB)**

Run: `python manage.py backfill_retake_local_ids && python manage.py backfill_retake_local_ids --check`
Expected: exit 0.

- [ ] **Step 2: Tighten the model fields (still nullable=False but no PK swap yet)**

Modify `activity/models/retake_models.py`:

```python
# RetakeRecord.local_id
local_id = models.CharField(max_length=36, unique=True, db_index=True, default=cuid.cuid, editable=False)
```

Repeat for `RetakeRecordDetail.local_id`. Keep them as regular (non-PK) fields for this phase.

- [ ] **Step 3: Generate the migration**

Run: `python manage.py makemigrations activity --name retake_local_id_unique`
Expected: file `0006_retake_local_id_unique.py` created with `AlterField` on both models.

- [ ] **Step 4: Apply the migration**

Run: `python manage.py migrate activity`
Expected: applies cleanly. If a `UniqueViolation` fires, run the duplicate-finder SQL from the LMS runbook (Phase A step 4) and hand-resolve, then retry.

- [ ] **Step 5: Commit**

```bash
git add activity/models/retake_models.py activity/migrations/0006_retake_local_id_unique.py
git commit -m "feat(activity): unique index on retake local_id (phase A)"
```

---

### Task 3: Phase B migration — swap PK to `local_id`, rewrite FK columns

**Files:**
- Modify: `activity/models/retake_models.py` (set `primary_key=True` on both `local_id` fields).
- Create: `activity/migrations/0007_swap_retake_pk.py`.
- Reference: copy the Postgres + SQLite RunPython bodies from `/home/classify/Desktop/Projects/HCCCI-LMS/classedge/activity/migrations/0036_swap_retake_pk.py` verbatim, **preserving the `%%I` escaping**, and (a) drop any references to prior LMS-only migrations in `dependencies=[]`, (b) keep the `SeparateDatabaseAndState` state-only `AlterField` on `mobile.Attachment.record_details`.

- [ ] **Step 1: Update the models**

Edit `activity/models/retake_models.py`:

```python
class RetakeRecord(models.Model):
    # ... existing fields, BUT replace local_id with:
    local_id = models.CharField(
        max_length=36, primary_key=True, default=cuid.cuid, editable=False,
    )
    # delete any explicit id field if added; leave choice_order, last_heartbeat_at, total_elapsed_seconds untouched.

    def save(self, *args, **kwargs):
        if not self.local_id:
            self.local_id = cuid.cuid()
        super().save(*args, **kwargs)


class RetakeRecordDetail(models.Model):
    # ... existing fields, BUT replace local_id with:
    local_id = models.CharField(
        max_length=36, primary_key=True, default=cuid.cuid, editable=False,
    )

    def save(self, *args, **kwargs):
        if not self.local_id:
            self.local_id = cuid.cuid()
        is_new = self.pk is None
        old_file = None
        if not is_new:
            try:
                old_file = RetakeRecordDetail.objects.get(pk=self.pk).uploaded_file
            except RetakeRecordDetail.DoesNotExist:
                old_file = None
        super().save(*args, **kwargs)
        if self.uploaded_file and (is_new or old_file != self.uploaded_file):
            from mobile.models import Attachment
            Attachment.objects.create(record_details=self, file=self.uploaded_file)
```

**Do not port** the LMS `print(...)` debug statements.

- [ ] **Step 2: Author the swap migration**

Create `activity/migrations/0007_swap_retake_pk.py`. Copy the body of LMS's `0036_swap_retake_pk.py`. Set `dependencies = [('activity', '0006_retake_local_id_unique'), ('mobile', '0002_attachment_activity_question_and_more')]`. Confirm:

- The Postgres SQL uses `%%I` everywhere (per LMS Lesson 2).
- The single migration rewrites BOTH `activity_retakerecorddetail.retake_record_id` AND `mobile_attachment.record_details_id` in one transaction, populating the new `varchar(36)` columns from the old integer ids while the parent `id` still exists (per LMS Lesson 1).
- `SeparateDatabaseAndState` wraps a state-only `AlterField` on `mobile.Attachment.record_details` so Django's state stays in sync without re-running DDL.

- [ ] **Step 3: Dry-run on a fresh SQLite copy**

```bash
cp db.sqlite3 db.sqlite3.before_retake_swap
python manage.py migrate activity 0007 --plan
python manage.py migrate activity 0007
```
Expected: applies cleanly on SQLite.

- [ ] **Step 4: Post-flight SQL checks (must each return 0)**

```bash
python manage.py dbshell <<'SQL'
SELECT COUNT(*) FROM activity_retakerecorddetail c
LEFT JOIN activity_retakerecord rr ON c.retake_record_id = rr.local_id
WHERE c.retake_record_id IS NOT NULL AND rr.local_id IS NULL;

SELECT COUNT(*) FROM mobile_attachment a
LEFT JOIN activity_retakerecorddetail rrd ON a.record_details_id = rrd.local_id
WHERE a.record_details_id IS NOT NULL AND rrd.local_id IS NULL;
SQL
```
Expected: `0` and `0`.

- [ ] **Step 5: Smoke test in shell**

```bash
python manage.py shell <<'PY'
from activity.models import RetakeRecord, RetakeRecordDetail
assert RetakeRecord._meta.pk.name == "local_id"
assert RetakeRecordDetail._meta.pk.name == "local_id"
print("OK")
PY
```
Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add activity/models/retake_models.py activity/migrations/0007_swap_retake_pk.py
git commit -m "feat(activity): swap RetakeRecord/Detail PK to cuid local_id (phase B)"
```

---

### Task 4: Schema + FK integrity tests

**Files:**
- Create: `activity/tests/test_retake_pk_swap.py`

- [ ] **Step 1: Write the tests**

```python
# activity/tests/test_retake_pk_swap.py
from django.db import models as dj_models
from django.test import TestCase
from accounts.models import CustomUser
from activity.models import Activity, StudentActivity, ActivityQuestion, RetakeRecord, RetakeRecordDetail
from mobile.models import Attachment

class RetakePKSwapTests(TestCase):
    def test_pk_is_local_id_charfield(self):
        for M in (RetakeRecord, RetakeRecordDetail):
            self.assertEqual(M._meta.pk.name, "local_id")
            self.assertIsInstance(M._meta.pk, dj_models.CharField)
            self.assertEqual(M._meta.pk.max_length, 36)

    def test_client_minted_cuid_is_accepted_as_pk(self):
        s = CustomUser.objects.create(email="t@x.com")
        a = Activity.objects.create(activity_name="A", max_score=10)
        sa = StudentActivity.objects.create(student=s, activity=a)
        rr = RetakeRecord.objects.create(local_id="client_minted_cuid_001", student_activity=sa, student=s, activity=a)
        self.assertEqual(RetakeRecord.objects.get(pk="client_minted_cuid_001").pk, rr.pk)

    def test_fk_integrity_string_keys(self):
        s = CustomUser.objects.create(email="u@x.com")
        a = Activity.objects.create(activity_name="A", max_score=10)
        sa = StudentActivity.objects.create(student=s, activity=a)
        q = ActivityQuestion.objects.create(activity=a)
        rr = RetakeRecord.objects.create(student_activity=sa, student=s, activity=a)
        d = RetakeRecordDetail.objects.create(retake_record=rr, student=s, activity_question=q)
        self.assertIsInstance(d.retake_record_id, str)
        self.assertEqual(d.retake_record_id, rr.local_id)
```

- [ ] **Step 2: Run tests**

Run: `python manage.py test activity.tests.test_retake_pk_swap -v 2`
Expected: PASS, 3 tests.

- [ ] **Step 3: Commit**

```bash
git add activity/tests/test_retake_pk_swap.py
git commit -m "test(activity): retake PK swap schema + FK integrity"
```

---

## Phase 2 — Source-of-truth unification (`StudentQuestion` → retake models)

### Task 5: `select_canonical_details` helper (pre-cutover, no behavior change)

**Files:**
- Create: `activity/services/retake_resolver.py` (or append to existing if present; check first).
- Reference: copy from `/home/classify/Desktop/Projects/HCCCI-LMS/classedge/activity/services/retake_resolver.py`.
- Test: `activity/tests/test_retake_resolver.py`.

- [ ] **Step 1: Check whether `retake_resolver.py` already exists here**

Run: `ls activity/services/retake_resolver.py 2>/dev/null && echo EXISTS || echo MISSING`

- [ ] **Step 2: Diff against LMS and bring helper to parity**

Run: `diff activity/services/retake_resolver.py /home/classify/Desktop/Projects/HCCCI-LMS/classedge/activity/services/retake_resolver.py`

Port the LMS version of `select_canonical_details(student_activity)` — it returns the `RetakeRecordDetail` queryset matching the activity's `retake_method` (highest/average/first/latest).

- [ ] **Step 3: Write tests covering all four retake_methods**

(Use LMS's tests if present; otherwise mirror the four branches with a small fixture.)

- [ ] **Step 4: Run tests**

Run: `python manage.py test activity.tests.test_retake_resolver -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add activity/services/retake_resolver.py activity/tests/test_retake_resolver.py
git commit -m "feat(activity): select_canonical_details helper for retake_method"
```

---

### Task 6: Rewrite web answer submission (`activity/views/answer_views.py`)

**Files:**
- Modify: `activity/views/answer_views.py`
- Test: `activity/tests/test_answer_views_submit.py`

- [ ] **Step 1: Write the failing integration test**

```python
# activity/tests/test_answer_views_submit.py
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from activity.models import Activity, ActivityQuestion, StudentActivity, RetakeRecord, RetakeRecordDetail, StudentQuestion, QuizType

class WebSubmitWritesRetakeOnlyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(email="s@x.com", password="pw")
        self.client.force_login(self.user)
        qt = QuizType.objects.create(name="Essay")
        self.act = Activity.objects.create(activity_name="A", max_score=10)
        self.q = ActivityQuestion.objects.create(activity=self.act, quiz_type=qt, score=10)

    def test_submit_creates_retakerecord_and_detail_no_studentquestion(self):
        url = reverse("submit_activity_answers", args=[self.act.pk])  # adjust to actual url name
        resp = self.client.post(url, {f"question_{self.q.pk}": "essay text"})
        self.assertEqual(resp.status_code, 302)
        sa = StudentActivity.objects.get(student=self.user, activity=self.act)
        rr = RetakeRecord.objects.get(student_activity=sa, retake_number=1)
        d = RetakeRecordDetail.objects.get(retake_record=rr, activity_question=self.q)
        self.assertEqual(d.student_answer, "essay text")
        self.assertFalse(StudentQuestion.objects.filter(student=self.user, activity_question=self.q).exists())
```

- [ ] **Step 2: Run to verify failure**

Run: `python manage.py test activity.tests.test_answer_views_submit -v 2`
Expected: FAIL — `StudentQuestion.objects.filter(...).exists() is True` (current code writes it).

- [ ] **Step 3: Rewrite the submit handler**

In `activity/views/answer_views.py`, replace the `StudentQuestion.objects.create/update_or_create` block with the sketch from LMS spec §"Web submit flow":

```python
student_activity, _ = StudentActivity.objects.get_or_create(student=request.user, activity=activity)
retake_record, _ = RetakeRecord.objects.get_or_create(
    student_activity=student_activity, student=request.user, activity=activity, retake_number=1,
    defaults={"status": "in_progress", "started_at": timezone.now()},
)
for question_id, answer in parsed_answers.items():
    question = ActivityQuestion.objects.get(pk=question_id)
    detail, _ = RetakeRecordDetail.objects.update_or_create(
        retake_record=retake_record, student=request.user, activity_question=question,
        defaults={"student_answer": answer.text, "uploaded_file": answer.file,
                  "submission_time": timezone.now()},
    )
    grade_detail(detail)
retake_record.status = "submitted"
retake_record.save(update_fields=["status"])
recompute_retake_record_score(retake_record)
recompute_student_activity_total(student_activity)
```

Remove every `StudentQuestion.objects.*` write in this file. Keep reads only if a fallback is required during the transition; otherwise delete them.

- [ ] **Step 4: Run test to verify pass**

Run: `python manage.py test activity.tests.test_answer_views_submit -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add activity/views/answer_views.py activity/tests/test_answer_views_submit.py
git commit -m "feat(activity): web submit writes RetakeRecord/Detail, no StudentQuestion"
```

---

### Task 7: Rewrite teacher grading views (`grading_views.py`)

**Files:**
- Modify: `activity/views/grading_views.py`
- Modify: `activity/templates/activity/grade/grade_essay.html`, `grade_essay_CM.html`, `grade_individual_essay.html`, `grade_individual_essay_CM.html`
- Modify: `activity/urls.py` (rename URL kwarg `student_question_id` → `detail_local_id`; keep old route as a redirect view for one release).
- Create: redirect helper in `activity/views/legacy_redirect_views.py` (port from LMS).
- Test: `activity/tests/test_grading_views.py`

- [ ] **Step 1: Write the failing test**

```python
# verifies GradeEssayView lists mobile-submitted RetakeRecordDetail rows
# verifies POST to GradeIndividualEssayView writes detail.score and recomputes totals
```

(Full test body: mirror LMS's `test_grading_views.py`; adjust URLs for this repo's `urls.py`.)

- [ ] **Step 2: Run test to verify failure**

Run: `python manage.py test activity.tests.test_grading_views -v 2`
Expected: FAIL (current view reads `StudentQuestion`).

- [ ] **Step 3: Port the view bodies**

Replace `GradeEssayView` / `GradeIndividualEssayView` (and `_CM` variants) with the LMS implementations from `/home/classify/Desktop/Projects/HCCCI-LMS/classedge/activity/views/grading_views.py`. Confirm imports resolve (`recompute_retake_record_score`, `recompute_student_activity_total` from `activity.services.auto_grader`).

- [ ] **Step 4: Update templates**

In each template:
- Rename context var `student_questions` → `submission_details`.
- `sq.student_answer` → `d.student_answer`, `sq.file` → `d.uploaded_file`.
- URL reverse kwarg `student_question_id` → `detail_local_id`.

- [ ] **Step 5: Add legacy URL redirect**

Port `activity/views/legacy_redirect_views.py` from LMS. Wire the old URL `…/grade-essay/<int:student_question_id>/` to the redirect; the new route uses `<str:detail_local_id>`.

- [ ] **Step 6: Run tests**

Run: `python manage.py test activity.tests.test_grading_views -v 2`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add activity/views/grading_views.py activity/views/legacy_redirect_views.py activity/urls.py activity/templates/activity/grade/ activity/tests/test_grading_views.py
git commit -m "feat(activity): grading views read RetakeRecordDetail; legacy URL redirect"
```

---

### Task 8: Rewrite remaining `StudentQuestion` writers

**Files (one commit per file):**
- Modify: `activity/views/batch_save_views.py`
- Modify: `activity/views/score_admin_views.py`
- Modify: `activity/views/participation_views.py`
- Modify: `mobile/views/student_activity_views.py` (audit finding: today dual-writes — remove `StudentQuestion` writes at lines ~109/123/135; numbers may differ here).
- Test: extend `activity/tests/test_answer_views_submit.py` with one per writer.

- [ ] **Step 1: For each file, write a test that submits via the writer and asserts zero new `StudentQuestion` rows.**
- [ ] **Step 2: Run tests — expect failure (current code writes them).**
- [ ] **Step 3: Replace each `StudentQuestion.objects.create/update_or_create/bulk_create` with the equivalent `RetakeRecordDetail` write (use `update_or_create` keyed on `(retake_record, student, activity_question)`).** Each writer must also call `recompute_retake_record_score` and `recompute_student_activity_total` after its loop.
- [ ] **Step 4: Run tests — PASS.**
- [ ] **Step 5: Commit each file separately** with message `feat(<area>): retake-only writes in <file>`.

---

### Task 9: Migrate readers (gradebook + course + calendar + module)

**Files (one commit per file):**
- Modify: `gradebookcomponent/views/utility_view.py` (replace `StudentQuestion`-based `Sum('score')` recompute with `student_activity.total_score`).
- Modify: `gradebookcomponent/views/activity_details_view.py` (iterate `select_canonical_details(sa)` for per-question render).
- Modify: `calendars/views.py` (existence checks: `RetakeRecordDetail.objects.filter(student=user, activity_question__activity=...)`).
- Modify: `course/views/classroom_views.py`, `course/views/subject_details_views.py`, `course/views/term_views.py` (same pattern).
- Modify: `module/views/progress_views.py`, `module/views/display_views.py` (same pattern).
- Test: small per-file integration test verifying counts pre/post seed.

- [ ] **Step 1: Per file — write test, swap query, run test, commit.**
- [ ] **Step 2: After all readers migrated, run the grep guard:**

```bash
git grep -nE 'StudentQuestion\.objects\.(filter|get|aggregate)' -- 'gradebookcomponent/**.py' 'course/**.py' 'calendars/**.py' 'module/**.py'
```
Expected: zero hits in production code (test code may still reference).

---

### Task 10: Backfill data migration — `StudentQuestion` → synthetic `RetakeRecord`/`Detail`

**Files:**
- Create: `activity/migrations/0008_backfill_studentquestion_into_retake.py` (data migration, no schema change).
- Test: `activity/tests/test_backfill_studentquestion.py`.

- [ ] **Step 1: Write the failing tests** covering the five rules from LMS spec §"Backfill strategy":
  1. Group `StudentQuestion` by `(student, activity)`.
  2. `RetakeRecord(retake_number=1, status='submitted', retake_time=max(submission_time))`.
  3. `RetakeRecordDetail` per `StudentQuestion` row, copying `student_answer`, `uploaded_file` (path string only), `score`, `submission_time`.
  4. `recompute_retake_record_score(rr)` per record; `recompute_student_activity_total(sa)` per SA.
  5. Conflict cases: mobile-already-has-RetakeRecord → reuse + later-submission-wins; orphaned SQ → create SA; deleted `activity_question` → skip + log.
  6. Idempotent.

- [ ] **Step 2: Run — verify failures.**

- [ ] **Step 3: Author the migration body**, mirroring the LMS plan's backfill task. Wrap in `RunPython(forwards, reverse_code=migrations.RunPython.noop)`.

- [ ] **Step 4: Apply on dev DB; sample 50 `StudentActivity` rows.**

```bash
python manage.py migrate activity
python manage.py shell <<'PY'
from activity.models import StudentActivity
for sa in StudentActivity.objects.order_by('?')[:50]:
    before = sa.total_score
    sa.refresh_from_db()
    assert abs((sa.total_score or 0) - (before or 0)) < 0.01, sa.pk
PY
```
Expected: no assertion errors. Log mismatches to `backfill_mismatches.json` per LMS spec.

- [ ] **Step 5: Commit**

```bash
git add activity/migrations/0008_backfill_studentquestion_into_retake.py activity/tests/test_backfill_studentquestion.py
git commit -m "feat(activity): backfill StudentQuestion rows into RetakeRecord/Detail"
```

---

### Task 11: Deprecate `StudentQuestion` (mark, don't drop)

**Files:**
- Modify: `activity/models/student_activity_model.py` (add module docstring + `DeprecationWarning` in `__init__`).
- Modify: `activity/__init__.py` if needed.

- [ ] **Step 1: Add the warning.**

```python
# top of student_activity_model.py
"""DEPRECATED: StudentQuestion is a frozen legacy table. All writes go through
RetakeRecord/RetakeRecordDetail. Reads in app code are forbidden. Scheduled drop:
see follow-up spec (target 2026-Q4).
"""

class StudentQuestion(models.Model):
    def __init__(self, *args, **kwargs):
        import warnings
        warnings.warn(
            "StudentQuestion is deprecated; use RetakeRecordDetail.",
            DeprecationWarning, stacklevel=2,
        )
        super().__init__(*args, **kwargs)
    # ... existing fields unchanged
```

- [ ] **Step 2: Run full test suite**

Run: `python manage.py test`
Expected: PASS (warnings allowed). If any prod-code path still instantiates `StudentQuestion`, the warning surfaces in the test run — fix the path, not the warning.

- [ ] **Step 3: Commit**

```bash
git add activity/models/student_activity_model.py
git commit -m "chore(activity): deprecate StudentQuestion (frozen legacy table)"
```

---

### Task 12: CI grep guards

**Files:**
- Modify: `pyproject.toml` or add a `Makefile` target / `scripts/check_studentquestion.sh`.

- [ ] **Step 1: Add the guard script.**

```bash
#!/usr/bin/env bash
# scripts/check_studentquestion.sh
set -euo pipefail
HITS=$(git grep -nE 'StudentQuestion\.objects\.(create|update_or_create|bulk_create|get_or_create)' \
    -- 'activity/views/**.py' 'activity/services/**.py' 'activity/utils/**.py' \
       'mobile/**.py' 'gradebookcomponent/**.py' 'course/**.py' 'calendars/**.py' 'module/**.py' \
       || true)
if [ -n "$HITS" ]; then
    echo "ERROR: StudentQuestion writers remain in production code:"
    echo "$HITS"
    exit 1
fi

MUT=$(git grep -nE 'total_score\s*[+\-]?=' -- 'activity/views/**.py' || true)
if [ -n "$MUT" ]; then
    echo "ERROR: direct total_score mutation; use recompute_student_activity_total:"
    echo "$MUT"
    exit 1
fi
```

- [ ] **Step 2: Run it.**

Run: `bash scripts/check_studentquestion.sh && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add scripts/check_studentquestion.sh
chmod +x scripts/check_studentquestion.sh
git commit -m "chore(ci): grep guard against StudentQuestion writes + total_score mutation"
```

---

### Task 13: Full-suite smoke + manual UI walkthrough

- [ ] **Step 1: Run the entire test suite**

Run: `python manage.py test`
Expected: PASS.

- [ ] **Step 2: Boot dev server**

Run: `python manage.py runserver`

- [ ] **Step 3: Manual walkthrough** (matches LMS spec §"Verification"):
  - Web user submits an Essay activity → `RetakeRecord(retake_number=1)` + `RetakeRecordDetail` created; no `StudentQuestion` row.
  - Teacher opens grading queue → sees the Essay submission.
  - Teacher grades it → `RetakeRecordDetail.score` updates; `RetakeRecord.score` recomputes; `StudentActivity.total_score` recomputes; gradebook reflects the change.
  - Mobile-submitted Essay also surfaces in the grading queue.
  - Export CSV matches gradebook totals.

- [ ] **Step 4: Capture results**

Write findings to `docs/superpowers/notes/2026-05-18-port-smoke.md`. Commit.

```bash
git add docs/superpowers/notes/2026-05-18-port-smoke.md
git commit -m "docs: smoke results for retake PK + source-of-truth port"
```

---

## Out of scope (follow-up specs)

- Drop `StudentQuestion` model + table (target: post-soak, ≥ one semester clean operation).
- Multi-attempt web UX (requires product decision).
- Per-question `ScoreChangeLog` audit (separate enhancement).
- Simulation generators rewrite (`simulation/generators/*.py`) — track separately; not blocking cutover safety because simulation data is regenerable.

## Pre-cutover checklist (production)

Before running Phase 1 + Phase 2 on production, the operator must:

1. `pg_dump` production → offsite, verified restore.
2. Run `backfill_retake_local_ids` (Phase A) and confirm `--check` exits 0.
3. Drain Celery; enable maintenance page.
4. Apply Phase 1 (migrations 0006 + 0007), run post-flight SQL — both return 0.
5. Apply Phase 2 (migration 0008 backfill), spot-check 50 `StudentActivity.total_score` deltas.
6. Deploy app code (Tasks 5–12) atomically.
7. Smoke (Task 13).
8. Disable maintenance.
9. Monitor logs 60 min for `ValueError: invalid literal for int()` and any `StudentQuestion`-targeted log/audit entries.
