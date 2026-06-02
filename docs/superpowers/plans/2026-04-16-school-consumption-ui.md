# School-side Consumption UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge centrally-pushed content into the school's native Subject/Module/Activity tables so teachers see pushed content as regular school content.

**Architecture:** Add nullable `central_source_id` to native Module and Activity models. Rewrite the school-side ingest endpoint to create native rows instead of `ReceivedCentralModule`/`ReceivedCentralActivity`. Inject `target_subject_id` into the push payload from the existing `SchoolSubjectBinding.school_subject_id`. Re-push deletes only central-tagged rows (preserving school-created content).

**Tech Stack:** Django 5.0.7, PostgreSQL, existing `module.Module` and `activity.Activity` models, existing `received_central_content` app.

---

## File Structure

**Modify:**
- `module/models/module.py` — add `central_source_id` field (line 33)
- `activity/models/activity_model.py` — add `central_source_id` field (line 79)
- `central_content/push.py:78-82` — inject `target_subject_id` in push payload
- `received_central_content/views/ingest.py` — rewrite `ingest_subject`, extend `delete_subject`
- `received_central_content/tests/test_ingest_api.py` — update for new native-row behavior
- `received_central_content/tests/test_ingest_delete.py` — add native row cleanup assertions
- `central_content/tests/test_integration_push.py` — verify native rows in integration test

**Create (auto-generated):**
- `module/migrations/NNNN_add_central_source_id.py`
- `activity/migrations/NNNN_add_central_source_id.py`

**Create:**
- `received_central_content/tests/test_native_ingest.py` — focused tests for Sub-3 native row behavior

---

## Context for the implementer

### Key existing code

**`SchoolSubjectBinding`** (`central_content/models/school_subject_binding.py`) already has `school_subject_id` (IntegerField), `school_subject_name` (CharField), and `school_subject_code` (CharField) from Sub-2. No schema change needed here.

**`push_subject_to_school`** (`central_content/push.py:78-129`) calls `build_push_payload(binding.central_subject)` to get a `(payload_dict, files_dict)` tuple, then POSTs `json.dumps(payload)` as multipart form data. The `target_subject_id` should be added to `payload` between `build_push_payload` and `json.dumps`.

**`ingest_subject`** (`received_central_content/views/ingest.py:40-168`) currently creates `ReceivedCentralSubject` (version tracking) plus `ReceivedCentralModule`/`ReceivedCentralActivity` rows. In Sub-3, it still writes `ReceivedCentralSubject` for version tracking but creates **native** `Module` and `Activity` rows instead.

**Native `Module`** (`module/models/module.py:21-115`) — FK to `subject.Subject` (CASCADE), fields: `file_name`, `file`, `subject`, `iframe_code`, `url`, `term`, `description`, `order`. Has `save()` with SubjectLog and notification side effects (acceptable for push).

**Native `Activity`** (`activity/models/activity_model.py:43-79`) — FK to `subject.Subject` (PROTECT), M2M `additional_modules` to Module. Fields: `activity_name`, `activity_type` (FK to ActivityType), `activity_instruction`, `max_score`, `time_duration`, `passing_score`, `passing_score_type`, `max_retake`, `retake_method`, `shuffle_questions`, `is_graded`, etc.

**Delete order matters:** When clearing central-sourced content, delete Activities first (to clear M2M to Modules), then Modules. Module has a custom `delete()` that raises `ProtectedError` if linked activities exist — but `QuerySet.delete()` bypasses the custom method, so bulk deletes are safe.

### Test patterns

- School-side tests use `@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])`
- Auth header: `HTTP_AUTHORIZATION="Bearer " + "t" * 40`
- Test DB is `test_neondb` on Neon cloud. Use `--keepdb` flag.
- Subject can be created with just `Subject.objects.create(subject_name="X", subject_code="Y")`
- Run tests: `env/bin/python manage.py test <app_label> --keepdb -v2`

---

### Task 1: Add `central_source_id` to Module model

**Files:**
- Modify: `module/models/module.py:33`

- [ ] **Step 1: Add the field**

In `module/models/module.py`, after line 33 (`order = models.PositiveIntegerField(default=0, editable=False)`), add:

```python
    central_source_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
```

- [ ] **Step 2: Generate migration**

Run: `env/bin/python manage.py makemigrations module --name add_central_source_id`

Expected: Creates `module/migrations/NNNN_add_central_source_id.py`

- [ ] **Step 3: Apply migration**

Run: `env/bin/python manage.py migrate module --keepdb`

Expected: `Applying module.NNNN_add_central_source_id... OK`

- [ ] **Step 4: Commit**

```bash
git add module/models/module.py module/migrations/*_add_central_source_id.py
git commit -m "feat(module): add central_source_id field for tracking central push origin"
```

---

### Task 2: Add `central_source_id` to Activity model

**Files:**
- Modify: `activity/models/activity_model.py:79`

- [ ] **Step 1: Add the field**

In `activity/models/activity_model.py`, after line 79 (`local_id = models.CharField(max_length=255, null=True, blank=True)`), add:

```python
    central_source_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
```

- [ ] **Step 2: Generate migration**

Run: `env/bin/python manage.py makemigrations activity --name add_central_source_id`

Expected: Creates `activity/migrations/NNNN_add_central_source_id.py`

- [ ] **Step 3: Apply migration**

Run: `env/bin/python manage.py migrate activity --keepdb`

Expected: `Applying activity.NNNN_add_central_source_id... OK`

- [ ] **Step 4: Commit**

```bash
git add activity/models/activity_model.py activity/migrations/*_add_central_source_id.py
git commit -m "feat(activity): add central_source_id field for tracking central push origin"
```

---

### Task 3: Inject `target_subject_id` in push payload

**Files:**
- Modify: `central_content/push.py:78-82`

- [ ] **Step 1: Add target_subject_id to payload**

In `central_content/push.py`, modify `push_subject_to_school` (line 78-82). After the `build_push_payload` call, add `target_subject_id`:

Replace:

```python
def push_subject_to_school(binding, triggered_by):
    from central_content.models import PushJob

    payload, files = build_push_payload(binding.central_subject)
    data = {"payload": json.dumps(payload)}
```

With:

```python
def push_subject_to_school(binding, triggered_by):
    from central_content.models import PushJob

    payload, files = build_push_payload(binding.central_subject)
    payload["target_subject_id"] = binding.school_subject_id
    data = {"payload": json.dumps(payload)}
```

- [ ] **Step 2: Run existing push tests to verify no regression**

Run: `env/bin/python manage.py test central_content.tests.test_push_function central_content.tests.test_payload_builder --keepdb -v2`

Expected: All pass (push tests mock the HTTP layer, so the extra field doesn't affect them).

- [ ] **Step 3: Commit**

```bash
git add central_content/push.py
git commit -m "feat(push): include target_subject_id in push payload from binding"
```

---

### Task 4: Write failing tests for native ingest

**Files:**
- Create: `received_central_content/tests/test_native_ingest.py`

- [ ] **Step 1: Write the test file**

Create `received_central_content/tests/test_native_ingest.py`:

```python
import json

from django.test import TestCase, override_settings, Client

from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from subject.models.sdg_models import SDG
from subject.models.subject_model import Subject


def _auth():
    return {"HTTP_AUTHORIZATION": "Bearer " + "t" * 40}


@override_settings(
    CENTRAL_INGEST_TOKEN="t" * 40,
    ROOT_URLCONF="lms.urls",
    ALLOWED_HOSTS=["*"],
)
class NativeIngestTests(TestCase):
    def setUp(self):
        self.target = Subject.objects.create(
            subject_name="Math 101", subject_code="MATH101",
        )
        SDG.objects.get_or_create(name="Quality Education")
        ActivityType.objects.get_or_create(name="Quiz")
        self.client = Client()

    def _payload(self, **overrides):
        base = {
            "central_id": 42,
            "central_version": 1,
            "target_subject_id": self.target.pk,
            "subject_name": "Algebra 1",
            "subject_descriptive_title": "Foundations of Algebra",
            "subject_short_name": "ALG1",
            "subject_description": "Central description",
            "subject_code": "ALG101",
            "subject_type": "Lec",
            "unit": 3,
            "target_grade_level": "Grade 7",
            "target_curriculum": "K-12",
            "target_sdgs": ["Quality Education"],
            "modules": [
                {
                    "central_id": 101,
                    "file_name": "Module 1",
                    "description": "Intro",
                    "order": 0,
                    "url": "",
                    "iframe_code": "",
                }
            ],
            "activities": [
                {
                    "central_id": 201,
                    "activity_name": "Quiz 1",
                    "activity_instruction": "Answer all",
                    "activity_type": "Quiz",
                    "max_score": 100,
                    "time_duration": 30,
                    "passing_score": 75,
                    "passing_score_type": "percentage",
                    "max_retake": 2,
                    "retake_method": "highest",
                    "shuffle_questions": True,
                    "is_graded": True,
                    "related_module_central_ids": [101],
                }
            ],
        }
        base.update(overrides)
        return base

    def test_push_creates_native_module(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 200)
        mod = Module.objects.get(subject=self.target, central_source_id=42)
        self.assertEqual(mod.file_name, "Module 1")
        self.assertEqual(mod.description, "Intro")

    def test_push_creates_native_activity(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 200)
        act = Activity.objects.get(subject=self.target, central_source_id=42)
        self.assertEqual(act.activity_name, "Quiz 1")
        self.assertEqual(act.max_retake, 2)
        self.assertTrue(act.shuffle_questions)

    def test_push_links_activity_to_module_via_m2m(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        act = Activity.objects.get(subject=self.target, central_source_id=42)
        mod = Module.objects.get(subject=self.target, central_source_id=42)
        self.assertIn(mod, act.additional_modules.all())

    def test_push_creates_received_subject_for_version_tracking(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        rs = ReceivedCentralSubject.objects.get(central_id=42)
        self.assertEqual(rs.central_version, 1)
        self.assertEqual(rs.subject_name, "Algebra 1")

    def test_repush_clears_old_central_rows_creates_new(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        old_mod_pk = Module.objects.get(central_source_id=42).pk

        second = self._payload(central_version=2)
        second["modules"][0]["file_name"] = "Module 1 v2"
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(second)},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        new_mod = Module.objects.get(central_source_id=42)
        self.assertNotEqual(new_mod.pk, old_mod_pk)
        self.assertEqual(new_mod.file_name, "Module 1 v2")

    def test_repush_preserves_school_created_content(self):
        Module.objects.create(
            subject=self.target, file_name="School Lesson", order=0,
        )
        Activity.objects.create(
            subject=self.target,
            activity_name="School Quiz",
            activity_type=ActivityType.objects.get(name="Quiz"),
        )
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(
            Module.objects.filter(subject=self.target, central_source_id__isnull=True).count(), 1,
        )
        self.assertEqual(
            Activity.objects.filter(subject=self.target, central_source_id__isnull=True).count(), 1,
        )
        school_mod = Module.objects.get(central_source_id__isnull=True)
        self.assertEqual(school_mod.file_name, "School Lesson")

    def test_missing_target_subject_id_returns_400(self):
        payload = self._payload()
        del payload["target_subject_id"]
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "missing_target_subject_id")

    def test_invalid_target_subject_id_returns_404(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload(target_subject_id=99999))},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "target_subject_not_found")

    def test_delete_clears_native_rows(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)

        resp = self.client.delete("/api/central/ingest/42/", **_auth())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 0)

    def test_delete_preserves_school_created_content(self):
        Module.objects.create(
            subject=self.target, file_name="School Lesson", order=0,
        )
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.client.delete("/api/central/ingest/42/", **_auth())
        self.assertEqual(
            Module.objects.filter(central_source_id__isnull=True).count(), 1,
        )
```

- [ ] **Step 2: Run the tests — expect failures**

Run: `env/bin/python manage.py test received_central_content.tests.test_native_ingest --keepdb -v2`

Expected: Most tests FAIL (ingest endpoint doesn't yet create native rows or validate `target_subject_id`).

- [ ] **Step 3: Commit the failing tests**

```bash
git add received_central_content/tests/test_native_ingest.py
git commit -m "test: add failing tests for native ingest (Sub-3 TDD red phase)"
```

---

### Task 5: Rewrite `ingest_subject` to create native rows

**Files:**
- Modify: `received_central_content/views/ingest.py`

- [ ] **Step 1: Rewrite ingest_subject**

Replace the entire `ingest_subject` function in `received_central_content/views/ingest.py` (lines 40-168) with:

```python
@csrf_exempt
@require_http_methods(["POST"])
@require_central_token
def ingest_subject(request):
    raw_payload = request.POST.get("payload")
    if not raw_payload:
        return _err(400, "missing_payload")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return _err(400, "invalid_json")

    central_id = payload.get("central_id")
    central_version = payload.get("central_version")
    target_subject_id = payload.get("target_subject_id")

    if central_id is None or central_version is None:
        return _err(400, "missing_required_fields")
    if target_subject_id is None:
        return _err(400, "missing_target_subject_id")

    from subject.models.subject_model import Subject
    try:
        target_subject = Subject.objects.get(pk=target_subject_id)
    except Subject.DoesNotExist:
        return _err(404, "target_subject_not_found")

    sdg_rows, missing_sdgs = _resolve_sdgs(payload.get("target_sdgs") or [])
    if missing_sdgs:
        return _err(422, "unresolved_sdgs", names=missing_sdgs)

    activity_type_names = [
        a["activity_type"] for a in payload.get("activities") or []
    ]
    at_by_name, missing_ats = _resolve_activity_types(activity_type_names)
    if missing_ats:
        return _err(422, "unresolved_activity_types", names=missing_ats)

    try:
        with transaction.atomic():
            from activity.models.activity_model import Activity as NativeActivity
            from module.models.module import Module as NativeModule

            received_subject, _created = ReceivedCentralSubject.objects.update_or_create(
                central_id=central_id,
                defaults={
                    "central_version": central_version,
                    "subject_name": payload.get("subject_name", ""),
                    "subject_descriptive_title": payload.get("subject_descriptive_title", ""),
                    "subject_short_name": payload.get("subject_short_name", ""),
                    "subject_description": payload.get("subject_description", ""),
                    "subject_code": payload.get("subject_code", ""),
                    "subject_type": payload.get("subject_type", ""),
                    "unit": payload.get("unit", 3),
                    "target_grade_level": payload.get("target_grade_level", ""),
                    "target_curriculum": payload.get("target_curriculum", ""),
                },
            )
            received_subject.target_sdgs.set(sdg_rows)

            subject_photo_part = payload.get("subject_photo_part")
            if subject_photo_part:
                f = request.FILES.get(subject_photo_part)
                if not f:
                    raise ValueError("missing_file_part:subject_photo")
                received_subject.subject_photo.save(f.name, f, save=True)

            NativeActivity.objects.filter(
                subject=target_subject,
                central_source_id=central_id,
            ).delete()
            NativeModule.objects.filter(
                subject=target_subject,
                central_source_id=central_id,
            ).delete()

            module_payloads = payload.get("modules") or []
            native_module_by_central_id = {}
            for m in module_payloads:
                mod = NativeModule(
                    subject=target_subject,
                    file_name=m.get("file_name", ""),
                    description=m.get("description", ""),
                    url=m.get("url", ""),
                    iframe_code=m.get("iframe_code", ""),
                    order=m.get("order", 0),
                    central_source_id=central_id,
                )
                mod.save()
                file_part = m.get("file_part")
                if file_part:
                    f = request.FILES.get(file_part)
                    if not f:
                        raise ValueError(f"missing_file_part:{file_part}")
                    mod.file.save(f.name, f, save=True)
                native_module_by_central_id[m["central_id"]] = mod

            activity_payloads = payload.get("activities") or []
            for a in activity_payloads:
                act = NativeActivity(
                    subject=target_subject,
                    activity_name=a.get("activity_name", ""),
                    activity_instruction=a.get("activity_instruction", ""),
                    activity_type=at_by_name[a["activity_type"]],
                    max_score=a.get("max_score", 100),
                    time_duration=a.get("time_duration", 0),
                    passing_score=a.get("passing_score", 0),
                    passing_score_type=a.get("passing_score_type", "percentage"),
                    max_retake=a.get("max_retake", 0),
                    retake_method=a.get("retake_method", "highest"),
                    shuffle_questions=a.get("shuffle_questions", False),
                    is_graded=a.get("is_graded", True),
                    central_source_id=central_id,
                )
                act.save()
                related_ids = a.get("related_module_central_ids") or []
                unknown = [cid for cid in related_ids if cid not in native_module_by_central_id]
                if unknown:
                    raise ValueError(f"unresolved_related_modules:{unknown}")
                act.additional_modules.set(
                    [native_module_by_central_id[cid] for cid in related_ids]
                )

    except ValueError as e:
        message = str(e)
        if message.startswith("unresolved_related_modules:"):
            return _err(422, "unresolved_related_modules", detail=message)
        if message.startswith("missing_file_part:"):
            return _err(400, "missing_file_part", detail=message.split(":", 1)[1])
        return _err(500, "server_error", detail=message)

    return JsonResponse(
        {
            "received_subject_id": received_subject.pk,
            "central_version": received_subject.central_version,
            "received_at": timezone.now().isoformat(),
        },
        status=200,
    )
```

- [ ] **Step 2: Run the new native ingest tests**

Run: `env/bin/python manage.py test received_central_content.tests.test_native_ingest --keepdb -v2`

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add received_central_content/views/ingest.py
git commit -m "feat(ingest): rewrite to create native Module/Activity rows with central_source_id"
```

---

### Task 6: Extend `delete_subject` to clean up native rows

**Files:**
- Modify: `received_central_content/views/ingest.py:171-181`

- [ ] **Step 1: Update delete_subject**

Replace the `delete_subject` function (lines 171-181, but line numbers may have shifted after Task 5) with:

```python
@csrf_exempt
@require_http_methods(["DELETE"])
@require_central_token
def delete_subject(request, central_id: int):
    from activity.models.activity_model import Activity as NativeActivity
    from module.models.module import Module as NativeModule

    try:
        subject = ReceivedCentralSubject.objects.get(central_id=central_id)
    except ReceivedCentralSubject.DoesNotExist:
        return _err(404, "not_found")

    NativeActivity.objects.filter(central_source_id=central_id).delete()
    NativeModule.objects.filter(central_source_id=central_id).delete()
    subject.delete()

    return JsonResponse({}, status=204)
```

- [ ] **Step 2: Run native ingest tests (includes delete tests)**

Run: `env/bin/python manage.py test received_central_content.tests.test_native_ingest --keepdb -v2`

Expected: All pass (includes `test_delete_clears_native_rows` and `test_delete_preserves_school_created_content`).

- [ ] **Step 3: Commit**

```bash
git add received_central_content/views/ingest.py
git commit -m "feat(ingest): extend delete to clean up native Module/Activity rows"
```

---

### Task 7: Update existing Sub-2 ingest tests

The existing `test_ingest_api.py` tests the old behavior (creating `ReceivedCentralModule`/`ReceivedCentralActivity`). The endpoint now creates native rows and requires `target_subject_id`. Update the tests.

**Files:**
- Modify: `received_central_content/tests/test_ingest_api.py`

- [ ] **Step 1: Rewrite test_ingest_api.py**

Replace the entire file `received_central_content/tests/test_ingest_api.py` with:

```python
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, Client

from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from subject.models.sdg_models import SDG
from subject.models.subject_model import Subject


def _auth_headers():
    return {"HTTP_AUTHORIZATION": "Bearer " + "t" * 40}


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class IngestHappyPathTests(TestCase):
    def setUp(self):
        self.target = Subject.objects.create(
            subject_name="Algebra 1", subject_code="ALG101",
        )
        SDG.objects.get_or_create(name="Quality Education")
        ActivityType.objects.get_or_create(name="Quiz")
        self.client = Client()

    def _base_payload(self):
        return {
            "central_id": 42,
            "central_version": 1,
            "target_subject_id": self.target.pk,
            "subject_name": "Algebra 1",
            "subject_descriptive_title": "Foundations of Algebra",
            "subject_short_name": "ALG1",
            "subject_description": "Central description",
            "subject_code": "ALG101",
            "subject_type": "Lec",
            "unit": 3,
            "target_grade_level": "Grade 7",
            "target_curriculum": "K-12",
            "target_sdgs": ["Quality Education"],
            "modules": [
                {
                    "central_id": 101,
                    "file_name": "Module 1",
                    "description": "Intro",
                    "order": 0,
                    "url": "",
                    "iframe_code": "",
                }
            ],
            "activities": [
                {
                    "central_id": 201,
                    "activity_name": "Quiz 1",
                    "activity_instruction": "Answer all",
                    "activity_type": "Quiz",
                    "max_score": 100,
                    "time_duration": 30,
                    "passing_score": 75,
                    "passing_score_type": "percentage",
                    "max_retake": 2,
                    "retake_method": "highest",
                    "shuffle_questions": True,
                    "is_graded": True,
                    "related_module_central_ids": [101],
                }
            ],
        }

    def test_no_token_returns_401(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._base_payload())},
        )
        self.assertEqual(resp.status_code, 401)

    def test_first_push_creates_rows(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._base_payload())},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)
        rs = ReceivedCentralSubject.objects.get()
        self.assertEqual(rs.central_id, 42)
        self.assertEqual(rs.central_version, 1)
        self.assertEqual(rs.target_sdgs.count(), 1)
        act = Activity.objects.get(central_source_id=42)
        self.assertEqual(act.additional_modules.count(), 1)

    def test_response_shape(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._base_payload())},
            **_auth_headers(),
        )
        body = resp.json()
        self.assertIn("received_subject_id", body)
        self.assertEqual(body["central_version"], 1)
        self.assertIn("received_at", body)

    def test_repush_upserts_and_deletes_orphans(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._base_payload())},
            **_auth_headers(),
        )
        second = self._base_payload()
        second["central_version"] = 2
        second["subject_name"] = "Algebra 1 Updated"
        second["modules"] = []
        second["activities"][0]["related_module_central_ids"] = []
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(second)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        rs = ReceivedCentralSubject.objects.get()
        self.assertEqual(rs.central_version, 2)
        self.assertEqual(rs.subject_name, "Algebra 1 Updated")
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class IngestValidationTests(TestCase):
    def setUp(self):
        self.target = Subject.objects.create(
            subject_name="Algebra 1", subject_code="ALG101",
        )
        SDG.objects.get_or_create(name="Quality Education")
        ActivityType.objects.get_or_create(name="Quiz")
        self.client = Client()

    def _base_payload(self):
        return {
            "central_id": 42,
            "central_version": 1,
            "target_subject_id": self.target.pk,
            "subject_name": "Algebra 1",
            "subject_descriptive_title": "Foundations of Algebra",
            "subject_short_name": "ALG1",
            "subject_description": "Central description",
            "subject_code": "ALG101",
            "subject_type": "Lec",
            "unit": 3,
            "target_grade_level": "Grade 7",
            "target_curriculum": "K-12",
            "target_sdgs": ["Quality Education"],
            "modules": [
                {
                    "central_id": 101,
                    "file_name": "Module 1",
                    "description": "Intro",
                    "order": 0,
                    "url": "",
                    "iframe_code": "",
                }
            ],
            "activities": [
                {
                    "central_id": 201,
                    "activity_name": "Quiz 1",
                    "activity_instruction": "Answer all",
                    "activity_type": "Quiz",
                    "max_score": 100,
                    "time_duration": 30,
                    "passing_score": 75,
                    "passing_score_type": "percentage",
                    "max_retake": 2,
                    "retake_method": "highest",
                    "shuffle_questions": True,
                    "is_graded": True,
                    "related_module_central_ids": [101],
                }
            ],
        }

    def test_unresolved_sdg_returns_422(self):
        payload = self._base_payload()
        payload["target_sdgs"] = ["Not A Real SDG"]
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"], "unresolved_sdgs")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)

    def test_unresolved_activity_type_returns_422(self):
        payload = self._base_payload()
        payload["activities"][0]["activity_type"] = "Made Up"
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"], "unresolved_activity_types")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)

    def test_missing_file_part_returns_400(self):
        payload = self._base_payload()
        payload["modules"][0]["file_part"] = "module_0_file"
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "missing_file_part")

    def test_subject_photo_uploaded(self):
        payload = self._base_payload()
        payload["subject_photo_part"] = "subject_photo"
        image = SimpleUploadedFile(
            "photo.png", b"fake-png-bytes", content_type="image/png",
        )
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload), "subject_photo": image},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        s = ReceivedCentralSubject.objects.get()
        self.assertTrue(s.subject_photo.name)

    def test_module_file_uploaded(self):
        payload = self._base_payload()
        payload["modules"][0]["file_part"] = "module_0_file"
        pdf = SimpleUploadedFile(
            "m.pdf", b"fake-pdf-bytes", content_type="application/pdf",
        )
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload), "module_0_file": pdf},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        m = Module.objects.get(central_source_id=42)
        self.assertTrue(m.file.name)
```

- [ ] **Step 2: Run updated tests**

Run: `env/bin/python manage.py test received_central_content.tests.test_ingest_api --keepdb -v2`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add received_central_content/tests/test_ingest_api.py
git commit -m "test: update Sub-2 ingest tests for native row behavior"
```

---

### Task 8: Update existing delete tests

**Files:**
- Modify: `received_central_content/tests/test_ingest_delete.py`

- [ ] **Step 1: Update delete tests to also verify native row cleanup**

Replace the entire file `received_central_content/tests/test_ingest_delete.py` with:

```python
import json

from django.test import TestCase, override_settings, Client

from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from received_central_content.tests.factories import make_received_subject
from subject.models.sdg_models import SDG
from subject.models.subject_model import Subject


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class IngestDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_no_token_returns_401(self):
        make_received_subject(central_id=42)
        resp = self.client.delete("/api/central/ingest/42/")
        self.assertEqual(resp.status_code, 401)

    def test_delete_cascades(self):
        make_received_subject(central_id=42)
        resp = self.client.delete(
            "/api/central/ingest/42/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)

    def test_delete_unknown_returns_404(self):
        resp = self.client.delete(
            "/api/central/ingest/999/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_clears_native_rows(self):
        target = Subject.objects.create(subject_name="Math", subject_code="M1")
        make_received_subject(central_id=42)
        Module.objects.create(
            subject=target, file_name="Central Mod", order=0, central_source_id=42,
        )
        ActivityType.objects.get_or_create(name="Quiz")
        Activity.objects.create(
            subject=target,
            activity_name="Central Quiz",
            activity_type=ActivityType.objects.get(name="Quiz"),
            central_source_id=42,
        )
        resp = self.client.delete(
            "/api/central/ingest/42/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 0)
```

- [ ] **Step 2: Run updated delete tests**

Run: `env/bin/python manage.py test received_central_content.tests.test_ingest_delete --keepdb -v2`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add received_central_content/tests/test_ingest_delete.py
git commit -m "test: update delete tests to verify native row cleanup"
```

---

### Task 9: Update integration test for native rows

**Files:**
- Modify: `central_content/tests/test_integration_push.py`

- [ ] **Step 1: Update integration test**

Replace the entire file `central_content/tests/test_integration_push.py` with:

```python
from unittest.mock import patch

from django.test import TestCase, override_settings, Client as DjangoClient

from activity.models.activity_model import Activity, ActivityType
from central_content.push import push_subject_to_school, delete_subject_from_school
from central_content.models import PushJob
from central_content.tests.factories import (
    make_binding, make_subject, make_module, make_activity,
    make_publisher, make_school,
)
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from subject.models.sdg_models import SDG
from subject.models.subject_model import Subject


class _FakeResponse:
    def __init__(self, status_code, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}

    def json(self):
        return self._json


def _dispatch_to_school_view(method):
    from django.test.utils import override_settings as _os

    def fake(url, **kwargs):
        parts = url.split("//", 1)[1].split("/", 1)
        path = "/" + parts[1] if len(parts) > 1 else "/"
        headers = {}
        for k, v in (kwargs.get("headers") or {}).items():
            headers["HTTP_" + k.upper().replace("-", "_")] = v
        with _os(ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"]):
            django_client = DjangoClient()
            if method == "post":
                data = dict(kwargs.get("data") or {})
                for k, (name, fh) in (kwargs.get("files") or {}).items():
                    data[k] = fh
                resp = django_client.post(path, data=data, **headers)
            else:
                resp = django_client.delete(path, **headers)
        ct = resp.get("Content-Type", "")
        text = resp.content.decode() if resp.content else ""
        json_data = {}
        if ct.startswith("application/json") and resp.content:
            try:
                json_data = resp.json()
            except Exception:
                pass
        return _FakeResponse(resp.status_code, text=text, json_data=json_data)

    return fake


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class IntegrationPushTests(TestCase):
    def test_full_loop_push_then_delete(self):
        SDG.objects.get_or_create(name="Quality Education")
        ActivityType.objects.get_or_create(name="Quiz")

        native_subject = Subject.objects.create(
            subject_name="Math 101", subject_code="MATH101",
        )

        subject = make_subject(
            subject_name="Algebra 1", version=1, subject_code="ALG101",
        )
        subject.target_sdgs.add(SDG.objects.get(name="Quality Education"))
        module = make_module(central_subject=subject, file_name="Mod 1")
        activity = make_activity(central_subject=subject)
        activity.related_modules.add(module)

        school = make_school(
            base_url="http://testserver",
            api_token="t" * 40,
        )
        binding = make_binding(
            central_subject=subject,
            target_school=school,
            school_subject_id=native_subject.pk,
            school_subject_name="Math 101",
            school_subject_code="MATH101",
        )

        with patch("central_content.push.requests.post", _dispatch_to_school_view("post")):
            job = push_subject_to_school(binding, triggered_by=make_publisher())

        self.assertEqual(
            job.status, "success",
            f"Push failed: {job.response_body} {job.error_message}",
        )
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        received = ReceivedCentralSubject.objects.get()
        self.assertEqual(received.central_id, subject.pk)
        self.assertEqual(received.subject_name, "Algebra 1")

        self.assertEqual(
            Module.objects.filter(
                subject=native_subject, central_source_id=subject.pk,
            ).count(),
            1,
        )
        self.assertEqual(
            Activity.objects.filter(
                subject=native_subject, central_source_id=subject.pk,
            ).count(),
            1,
        )
        native_mod = Module.objects.get(central_source_id=subject.pk)
        self.assertEqual(native_mod.file_name, "Mod 1")
        native_act = Activity.objects.get(central_source_id=subject.pk)
        self.assertIn(native_mod, native_act.additional_modules.all())

        with patch("central_content.push.requests.delete", _dispatch_to_school_view("delete")):
            del_job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(del_job.status, "success")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)
        self.assertEqual(Module.objects.filter(central_source_id=subject.pk).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=subject.pk).count(), 0)
```

- [ ] **Step 2: Run integration test**

Run: `env/bin/python manage.py test central_content.tests.test_integration_push --keepdb -v2`

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add central_content/tests/test_integration_push.py
git commit -m "test: update integration test for native row push/delete"
```

---

### Task 10: Full regression run

- [ ] **Step 1: Run all central_content tests**

Run: `env/bin/python manage.py test central_content --keepdb -v2`

Expected: All Sub-1 and Sub-2 tests pass. No regressions.

- [ ] **Step 2: Run all received_central_content tests**

Run: `env/bin/python manage.py test received_central_content --keepdb -v2`

Expected: All tests pass.

- [ ] **Step 3: Run Django system check**

Run: `env/bin/python manage.py check`

Expected: `System check identified no issues.`

- [ ] **Step 4: Count total tests and compare**

Run: `env/bin/python manage.py test central_content received_central_content --keepdb -v2 2>&1 | tail -5`

Expected: Test count ≥ 142 (original) + new native ingest tests. All pass, zero failures.

- [ ] **Step 5: Final commit (if any fixups needed)**

```bash
git add -A
git commit -m "chore: Sub-3 regression fixes"
```

Only create this commit if fixups were needed. Skip if all tests passed cleanly.
