# Sub-project 2: School Matching & Push — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Sub-project 2 of the Classedge Plus tier — the central-to-school push pipeline. Publishers bind a `CentralSubject` to a specific school's native `Subject`, then push the entire subject → modules → activities tree (plus files) over HTTPS into a new isolated app on the school's Classedge deployment. Re-push on update, unbind cascades, zero changes to the school's native models.

**Architecture:** Central and each school are separate Classedge deployments with separate databases. Central talks to each school via authenticated HTTPS (bearer token). On the school side, a new self-contained app `received_central_content/` receives snapshots into three mirror tables and never touches the school's native `Subject` / `Module` / `Activity` tables. On the central side, three new models (`School`, `SchoolSubjectBinding`, `PushJob`) in the existing `central_content/` app back the matching workspace, push function, and push history UI. Push is synchronous — the Publisher's click blocks until the HTTP call returns. No Celery, no automatic retries.

**Tech Stack:**
- Python 3.12 / Django 5.0.7 (existing)
- Postgres (each deployment has its own DB)
- Django built-in test runner (`env/bin/python manage.py test ...`)
- `requests` library for outbound HTTP (central → school) — already in `requirements.txt`
- `requests_mock` or `responses` for mocking HTTP in unit tests — needs to be added to `requirements.txt` in Task 12
- HTMX + Tailwind via CDN in central templates (already loaded by Sub-1 `base.html`)
- No factory_boy — continue the plain-function factory pattern from Sub-1's `central_content/tests/factories.py`

**Spec reference:** `docs/superpowers/specs/2026-04-16-classedge-school-matching-and-push-design.md`

**Preconditions (not in plan scope, must be true before Task 1):**
- Sub-1 merged into `main` locally (branch `central-content-sub1` — done).
- Working `lms/settings.py` and `lms/settings_central.py` from Sub-1.
- Postgres test DB `test_neondb` and existing migrations applied.
- `env/bin/python manage.py check` passes for both `DJANGO_SETTINGS_MODULE=lms.settings` and `DJANGO_SETTINGS_MODULE=lms.settings_central`.
- A new feature branch `central-content-sub2` created from `main` before Task 1.

**Important conventions carried over from Sub-1:**
- Every view decorated with `@central_role_required(...)` from `central_content/permissions.py`.
- Every state-changing view wraps its logic in `transaction.atomic`.
- Every meaningful action writes exactly one `AuditLogEntry` from `central_content/models/audit_log.py`.
- Tests use the factories in `central_content/tests/factories.py`; extend that file when new factories are needed.
- Never use `python3` — always `env/bin/python`.
- Tests run with `env/bin/python manage.py test central_content received_central_content --keepdb`.

---

## File Structure

**Central side — new files:**

```
classedge/
├── central_content/
│   ├── models/
│   │   ├── school.py                          # School model
│   │   ├── school_subject_binding.py          # SchoolSubjectBinding (+ drift_state helper)
│   │   └── push_job.py                        # PushJob model
│   ├── migrations/
│   │   └── 0006_school_binding_pushjob.py     # (generated)
│   ├── push.py                                # payload builder + push/delete functions
│   ├── views/
│   │   ├── schools.py                         # Schools CRUD views
│   │   ├── matching.py                        # matching workspace + bind/unbind
│   │   ├── push.py                            # push trigger + retry
│   │   └── push_history.py                    # push history list
│   ├── forms.py                               # ADD: SchoolForm (new file if absent, else append)
│   ├── templates/central_content/
│   │   ├── schools/
│   │   │   ├── list.html
│   │   │   ├── form.html
│   │   │   └── token_reveal.html              # shown once after create / regenerate
│   │   ├── matching/
│   │   │   ├── workspace.html
│   │   │   ├── _bindings_table.html           # HTMX partial
│   │   │   └── _unbind_modal.html             # HTMX partial
│   │   └── push_history/
│   │       └── list.html
│   └── tests/
│       ├── test_school_model.py
│       ├── test_binding_model.py
│       ├── test_push_job_model.py
│       ├── test_payload_builder.py
│       ├── test_push_function.py
│       ├── test_delete_function.py
│       ├── test_schools_views.py
│       ├── test_matching_views.py
│       ├── test_push_views.py
│       ├── test_push_history_views.py
│       └── test_integration_push.py
```

**Central side — modified files:**

```
classedge/
├── central_content/
│   ├── models/__init__.py                     # + re-export School, SchoolSubjectBinding, PushJob
│   ├── urls.py                                # + /schools/, /matching/, /push-history/, actions
│   ├── tests/factories.py                    # + make_school, make_binding helpers
│   └── templates/central_content/base.html    # + Schools / Matching / Push History nav entries
├── requirements.txt                            # + responses (HTTP mock library)
```

**School side — new files (added to the SAME Classedge repo under a new app):**

```
classedge/
├── received_central_content/
│   ├── __init__.py
│   ├── apps.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── received_subject.py
│   │   ├── received_module.py
│   │   └── received_activity.py
│   ├── migrations/
│   │   ├── __init__.py
│   │   └── 0001_initial.py                    # (generated)
│   ├── auth.py                                # bearer-token decorator
│   ├── views/
│   │   ├── __init__.py
│   │   ├── catalog.py                         # GET /api/central/subjects/
│   │   └── ingest.py                          # POST + DELETE /api/central/ingest/
│   ├── urls.py
│   └── tests/
│       ├── __init__.py
│       ├── factories.py
│       ├── test_models.py
│       ├── test_auth.py
│       ├── test_catalog_api.py
│       ├── test_ingest_api.py
│       └── test_ingest_delete.py
```

**School side — modified files:**

```
classedge/
├── lms/
│   ├── settings.py                           # + 'received_central_content' in INSTALLED_APPS
│   └── urls.py                               # + include('received_central_content.urls', namespace='received_central_content') at prefix 'api/central/'
├── .env.example                              # + CENTRAL_INGEST_TOKEN=
```

**Note:** The `received_central_content` app lives in the same Classedge repo because each school runs the same Classedge codebase. In production, each school deployment is a separate install of the same repo with its own DB and its own `.env` containing `CENTRAL_INGEST_TOKEN`. The `central_content` app and the `received_central_content` app coexist in the repo but only `central_content` views are mounted when `DJANGO_SETTINGS_MODULE=lms.settings_central`, while only `received_central_content` views are mounted under the default `DJANGO_SETTINGS_MODULE=lms.settings`.

---

## Task order

Tasks 1–3 build the central-side data models. Tasks 4–11 build the entire school-side (app scaffold, models, API, URL wiring) so that central-side integration tests in later tasks have something real to call. Tasks 12–14 build the central-side push functions (which can be unit-tested in isolation with `responses`). Tasks 15–19 build the central-side views and templates. Task 20 wires navigation and permissions. Task 21 is the end-to-end integration smoke test.

---

## Task 1: Central `School` model

**Files:**
- Create: `central_content/models/school.py`
- Create: `central_content/tests/test_school_model.py`
- Modify: `central_content/models/__init__.py` — add `from .school import School`
- Modify: `central_content/tests/factories.py` — add `make_school`
- Generated: `central_content/migrations/0006_school.py`

- [ ] **Step 1: Add `make_school` factory helper**

Append to `central_content/tests/factories.py`:

```python
import secrets

def make_school(
    name="HCCCI",
    base_url="https://classedge.hccci.edu.ph",
    api_token=None,
    is_active=True,
    notes="",
    created_by=None,
):
    from central_content.models import School
    if created_by is None:
        created_by = make_publisher()  # existing helper from Sub-1
    return School.objects.create(
        name=name,
        base_url=base_url,
        api_token=api_token or secrets.token_hex(20),
        is_active=is_active,
        notes=notes,
        created_by=created_by,
    )
```

- [ ] **Step 2: Write the failing tests**

Create `central_content/tests/test_school_model.py`:

```python
import secrets

from django.db import IntegrityError
from django.test import TestCase

from central_content.models import School
from central_content.tests.factories import make_publisher, make_school


class SchoolModelTests(TestCase):
    def test_create_school_generates_token(self):
        publisher = make_publisher()
        school = School.objects.create(
            name="HCCCI",
            base_url="https://classedge.hccci.edu.ph",
            api_token=secrets.token_hex(20),
            created_by=publisher,
        )
        self.assertEqual(len(school.api_token), 40)
        self.assertTrue(school.is_active)
        self.assertEqual(school.notes, "")

    def test_default_is_active_true(self):
        school = make_school()
        self.assertTrue(school.is_active)

    def test_str_is_name(self):
        school = make_school(name="HCCCI")
        self.assertEqual(str(school), "HCCCI")

    def test_name_required(self):
        publisher = make_publisher()
        with self.assertRaises(Exception):
            School.objects.create(
                name="",
                base_url="https://x",
                api_token="t" * 40,
                created_by=publisher,
            ).full_clean()

    def test_created_by_protect(self):
        """Deleting a CentralStaff that created a School must fail."""
        school = make_school()
        with self.assertRaises(Exception):
            school.created_by.delete()
```

- [ ] **Step 3: Run tests — verify they fail**

Run:
```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_school_model --keepdb -v 2
```
Expected: `ImportError: cannot import name 'School'` or similar.

- [ ] **Step 4: Create the model**

Create `central_content/models/school.py`:

```python
# central_content/models/school.py
from django.db import models


class School(models.Model):
    name = models.CharField(max_length=100)
    base_url = models.URLField()
    api_token = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="schools_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_school"
        ordering = ["name"]

    def __str__(self):
        return self.name
```

Update `central_content/models/__init__.py`:

```python
# add this import near the other model imports
from .school import School  # noqa: F401
```

- [ ] **Step 5: Create migration**

Run:
```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py makemigrations central_content
```

Expected output: `Migrations for 'central_content': 0006_school.py - Create model School`.

- [ ] **Step 6: Run tests — verify they pass**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_school_model --keepdb -v 2
```
Expected: 5 tests, OK.

- [ ] **Step 7: Commit**

```bash
git add central_content/models/school.py central_content/models/__init__.py \
    central_content/migrations/0006_school.py \
    central_content/tests/test_school_model.py central_content/tests/factories.py
git commit -m "Add School model for Sub-2 schools registry"
```

---

## Task 2: Central `SchoolSubjectBinding` model

**Files:**
- Create: `central_content/models/school_subject_binding.py`
- Create: `central_content/tests/test_binding_model.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/factories.py` — add `make_binding`
- Generated: `central_content/migrations/0007_schoolsubjectbinding.py`

- [ ] **Step 1: Add `make_binding` factory helper**

Append to `central_content/tests/factories.py`:

```python
def make_binding(
    central_subject=None,
    target_school=None,
    school_subject_id=17,
    school_subject_name="Math 101",
    school_subject_code="MATH101",
    pushed_version=None,
    bound_by=None,
):
    from central_content.models import SchoolSubjectBinding
    if central_subject is None:
        central_subject = make_central_subject()  # existing Sub-1 helper
    if target_school is None:
        target_school = make_school()
    if bound_by is None:
        bound_by = make_publisher()
    return SchoolSubjectBinding.objects.create(
        central_subject=central_subject,
        target_school=target_school,
        school_subject_id=school_subject_id,
        school_subject_name=school_subject_name,
        school_subject_code=school_subject_code,
        pushed_version=pushed_version,
        bound_by=bound_by,
    )
```

- [ ] **Step 2: Write the failing tests**

Create `central_content/tests/test_binding_model.py`:

```python
from django.db import IntegrityError
from django.test import TestCase

from central_content.models import SchoolSubjectBinding
from central_content.tests.factories import (
    make_binding, make_central_subject, make_publisher, make_school,
)


class BindingModelTests(TestCase):
    def test_create_binding_fields(self):
        b = make_binding()
        self.assertIsNone(b.pushed_version)
        self.assertIsNone(b.last_pushed_at)
        self.assertIsNotNone(b.bound_at)

    def test_unique_constraint(self):
        subject = make_central_subject()
        school = make_school()
        make_binding(central_subject=subject, target_school=school)
        with self.assertRaises(IntegrityError):
            make_binding(central_subject=subject, target_school=school)

    def test_drift_state_never_pushed(self):
        b = make_binding(pushed_version=None)
        self.assertEqual(b.drift_state, "never")

    def test_drift_state_up_to_date(self):
        subject = make_central_subject(version=3)
        b = make_binding(central_subject=subject, pushed_version=3)
        self.assertEqual(b.drift_state, "up_to_date")

    def test_drift_state_drift(self):
        subject = make_central_subject(version=5)
        b = make_binding(central_subject=subject, pushed_version=3)
        self.assertEqual(b.drift_state, "drift")

    def test_cascade_from_central_subject(self):
        b = make_binding()
        b.central_subject.delete()
        self.assertFalse(
            SchoolSubjectBinding.objects.filter(pk=b.pk).exists()
        )
```

- [ ] **Step 3: Run tests — verify they fail**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_binding_model --keepdb -v 2
```
Expected: ImportError / model not found.

- [ ] **Step 4: Create the model**

Create `central_content/models/school_subject_binding.py`:

```python
# central_content/models/school_subject_binding.py
from django.db import models


class SchoolSubjectBinding(models.Model):
    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="school_bindings",
    )
    target_school = models.ForeignKey(
        "central_content.School",
        on_delete=models.PROTECT,
        related_name="bindings",
    )
    school_subject_id = models.IntegerField()
    school_subject_name = models.CharField(max_length=200)
    school_subject_code = models.CharField(max_length=30, blank=True)

    pushed_version = models.PositiveIntegerField(null=True, blank=True)
    last_pushed_at = models.DateTimeField(null=True, blank=True)

    bound_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="bindings_created",
    )
    bound_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_school_subject_binding"
        constraints = [
            models.UniqueConstraint(
                fields=["central_subject", "target_school"],
                name="uniq_central_subject_target_school",
            ),
        ]
        ordering = ["target_school", "central_subject"]

    @property
    def drift_state(self) -> str:
        """Return "never" | "up_to_date" | "drift" based on pushed_version."""
        if self.pushed_version is None:
            return "never"
        if self.pushed_version == self.central_subject.version:
            return "up_to_date"
        return "drift"

    def __str__(self):
        return f"{self.central_subject_id}->{self.target_school_id}"
```

Update `central_content/models/__init__.py`:

```python
from .school_subject_binding import SchoolSubjectBinding  # noqa: F401
```

- [ ] **Step 5: Create migration**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py makemigrations central_content
```

Expected: `0007_schoolsubjectbinding.py`.

- [ ] **Step 6: Run tests — verify they pass**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_binding_model --keepdb -v 2
```
Expected: 6 tests, OK.

- [ ] **Step 7: Commit**

```bash
git add central_content/models/school_subject_binding.py \
    central_content/models/__init__.py \
    central_content/migrations/0007_*.py \
    central_content/tests/test_binding_model.py \
    central_content/tests/factories.py
git commit -m "Add SchoolSubjectBinding model with drift_state helper"
```

---

## Task 3: Central `PushJob` model

**Files:**
- Create: `central_content/models/push_job.py`
- Create: `central_content/tests/test_push_job_model.py`
- Modify: `central_content/models/__init__.py`
- Generated: `central_content/migrations/0008_pushjob.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_push_job_model.py`:

```python
from django.test import TestCase
from django.utils import timezone

from central_content.models import PushJob
from central_content.tests.factories import (
    make_binding, make_publisher, make_central_subject, make_school,
)


class PushJobModelTests(TestCase):
    def test_create_success_push_job(self):
        subject = make_central_subject(version=2)
        school = make_school()
        publisher = make_publisher()
        job = PushJob.objects.create(
            central_subject=subject,
            target_school=school,
            kind=PushJob.Kind.PUSH,
            status=PushJob.Status.SUCCESS,
            subject_version=2,
            http_status=200,
            response_body='{"received_subject_id": 1}',
            finished_at=timezone.now(),
            triggered_by=publisher,
        )
        self.assertEqual(job.kind, "push")
        self.assertEqual(job.status, "success")

    def test_create_failed_push_job(self):
        subject = make_central_subject(version=1)
        job = PushJob.objects.create(
            central_subject=subject,
            target_school=make_school(),
            kind=PushJob.Kind.PUSH,
            status=PushJob.Status.FAILED,
            subject_version=1,
            http_status=500,
            error_message="internal server error",
            finished_at=timezone.now(),
            triggered_by=make_publisher(),
        )
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.http_status, 500)

    def test_create_delete_job(self):
        job = PushJob.objects.create(
            central_subject=make_central_subject(),
            target_school=make_school(),
            kind=PushJob.Kind.DELETE,
            status=PushJob.Status.SUCCESS,
            subject_version=1,
            http_status=204,
            finished_at=timezone.now(),
            triggered_by=make_publisher(),
        )
        self.assertEqual(job.kind, "delete")
```

- [ ] **Step 2: Run tests — verify they fail**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_push_job_model --keepdb -v 2
```

- [ ] **Step 3: Create the model**

Create `central_content/models/push_job.py`:

```python
# central_content/models/push_job.py
from django.db import models


class PushJob(models.Model):
    class Kind(models.TextChoices):
        PUSH = "push", "Push"
        DELETE = "delete", "Delete"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="push_jobs",
    )
    target_school = models.ForeignKey(
        "central_content.School",
        on_delete=models.CASCADE,
        related_name="push_jobs",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    subject_version = models.PositiveIntegerField()
    http_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField()
    triggered_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="push_jobs_triggered",
    )

    class Meta:
        app_label = "central_content"
        db_table = "central_content_push_job"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.kind}:{self.status}:{self.central_subject_id}->{self.target_school_id}"
```

Update `central_content/models/__init__.py`:

```python
from .push_job import PushJob  # noqa: F401
```

- [ ] **Step 4: Create migration + run tests**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py makemigrations central_content && \
  env/bin/python manage.py test central_content.tests.test_push_job_model --keepdb -v 2
```
Expected: `0008_pushjob.py` created, 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git add central_content/models/push_job.py \
    central_content/models/__init__.py \
    central_content/migrations/0008_*.py \
    central_content/tests/test_push_job_model.py
git commit -m "Add PushJob model for push history"
```

---

## Task 4: School-side `received_central_content` app scaffold

**Files:**
- Create: `received_central_content/__init__.py` (empty)
- Create: `received_central_content/apps.py`
- Create: `received_central_content/models/__init__.py` (empty for now)
- Create: `received_central_content/migrations/__init__.py` (empty)
- Create: `received_central_content/tests/__init__.py` (empty)
- Modify: `lms/settings.py` — add to `INSTALLED_APPS`

- [ ] **Step 1: Create app skeleton**

Create `received_central_content/__init__.py`:

```python
# empty
```

Create `received_central_content/apps.py`:

```python
from django.apps import AppConfig


class ReceivedCentralContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "received_central_content"
```

Create empty `received_central_content/models/__init__.py`, `received_central_content/migrations/__init__.py`, `received_central_content/tests/__init__.py`.

- [ ] **Step 2: Register app in settings**

Modify `lms/settings.py` (remember this file is gitignored — so each engineer must modify their own). Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "central_content",                # from Sub-1
    "received_central_content",       # Sub-2 — new
]
```

Note: since `lms/settings.py` is gitignored, this task does NOT produce a committable diff for `settings.py`. Document this addition in the commit message and in any handoff notes.

- [ ] **Step 3: Verify Django loads the app**

```
cd ~/classedge && env/bin/python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add received_central_content/
git commit -m "Add received_central_content app scaffold"
```

---

## Task 5: School-side received models (Subject, Module, Activity)

**Files:**
- Create: `received_central_content/models/received_subject.py`
- Create: `received_central_content/models/received_module.py`
- Create: `received_central_content/models/received_activity.py`
- Modify: `received_central_content/models/__init__.py`
- Create: `received_central_content/tests/factories.py`
- Create: `received_central_content/tests/test_models.py`
- Generated: `received_central_content/migrations/0001_initial.py`

- [ ] **Step 1: Create factories**

Create `received_central_content/tests/factories.py`:

```python
from subject.models import SDG
from activity.models import ActivityType


def get_or_create_sdg(name="Quality Education"):
    obj, _ = SDG.objects.get_or_create(name=name)
    return obj


def get_or_create_activity_type(name="Quiz"):
    obj, _ = ActivityType.objects.get_or_create(name=name)
    return obj


def make_received_subject(central_id=42, central_version=1, **kwargs):
    from received_central_content.models import ReceivedCentralSubject
    defaults = dict(
        central_id=central_id,
        central_version=central_version,
        subject_name="Algebra 1",
        subject_descriptive_title="Foundations of Algebra",
        subject_short_name="ALG1",
        subject_description="Central description",
        subject_code="ALG101",
        subject_type="Lec",
        unit=3,
        target_grade_level="Grade 7",
        target_curriculum="K-12",
    )
    defaults.update(kwargs)
    return ReceivedCentralSubject.objects.create(**defaults)


def make_received_module(received_subject=None, central_id=101, **kwargs):
    from received_central_content.models import ReceivedCentralModule
    if received_subject is None:
        received_subject = make_received_subject()
    defaults = dict(
        received_subject=received_subject,
        central_id=central_id,
        file_name="Module 1",
        description="Intro",
        order=0,
        url="",
        iframe_code="",
    )
    defaults.update(kwargs)
    return ReceivedCentralModule.objects.create(**defaults)


def make_received_activity(received_subject=None, central_id=201, **kwargs):
    from received_central_content.models import ReceivedCentralActivity
    if received_subject is None:
        received_subject = make_received_subject()
    activity_type = kwargs.pop("activity_type", None) or get_or_create_activity_type()
    defaults = dict(
        received_subject=received_subject,
        central_id=central_id,
        activity_name="Quiz 1",
        activity_instruction="Answer all",
        activity_type=activity_type,
        max_score=100,
        time_duration=30,
        passing_score=75,
        passing_score_type="percentage",
        max_retake=2,
        retake_method="highest",
        shuffle_questions=True,
        is_graded=True,
    )
    defaults.update(kwargs)
    return ReceivedCentralActivity.objects.create(**defaults)
```

- [ ] **Step 2: Write the failing model tests**

Create `received_central_content/tests/test_models.py`:

```python
from django.db import IntegrityError
from django.test import TestCase

from received_central_content.models import (
    ReceivedCentralSubject, ReceivedCentralModule, ReceivedCentralActivity,
)
from received_central_content.tests.factories import (
    make_received_subject, make_received_module, make_received_activity,
    get_or_create_sdg,
)


class ReceivedModelsTests(TestCase):
    def test_create_received_subject(self):
        s = make_received_subject()
        self.assertEqual(s.central_id, 42)
        self.assertEqual(s.central_version, 1)
        self.assertIsNotNone(s.received_at)
        self.assertIsNotNone(s.last_received_at)

    def test_central_id_unique(self):
        make_received_subject(central_id=42)
        with self.assertRaises(IntegrityError):
            make_received_subject(central_id=42)

    def test_m2m_sdgs(self):
        s = make_received_subject()
        s.target_sdgs.add(get_or_create_sdg("Quality Education"))
        self.assertEqual(s.target_sdgs.count(), 1)

    def test_module_fk_cascade(self):
        m = make_received_module()
        subject_pk = m.received_subject.pk
        m.received_subject.delete()
        self.assertFalse(ReceivedCentralModule.objects.filter(received_subject_id=subject_pk).exists())

    def test_activity_fk_cascade(self):
        a = make_received_activity()
        a.received_subject.delete()
        self.assertEqual(ReceivedCentralActivity.objects.count(), 0)

    def test_activity_related_modules(self):
        subject = make_received_subject()
        m = make_received_module(received_subject=subject)
        a = make_received_activity(received_subject=subject)
        a.related_modules.add(m)
        self.assertEqual(a.related_modules.count(), 1)
```

- [ ] **Step 3: Run tests — verify they fail**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_models --keepdb -v 2
```
Expected: ImportError.

- [ ] **Step 4: Create the three models**

Create `received_central_content/models/received_subject.py`:

```python
# received_central_content/models/received_subject.py
import os
import uuid

from django.db import models


def _received_subject_photo_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("received_central", "subjectPhoto", new_name)


class ReceivedCentralSubject(models.Model):
    central_id = models.IntegerField(unique=True)
    central_version = models.PositiveIntegerField()

    subject_name = models.CharField(max_length=200)
    subject_descriptive_title = models.CharField(max_length=100, blank=True)
    subject_short_name = models.CharField(max_length=30, blank=True)
    subject_photo = models.ImageField(
        upload_to=_received_subject_photo_path, blank=True, null=True,
    )
    subject_description = models.TextField(blank=True)
    subject_code = models.CharField(max_length=30, blank=True)
    subject_type = models.CharField(max_length=10, blank=True)
    unit = models.PositiveIntegerField(default=3)

    target_grade_level = models.CharField(max_length=50, blank=True)
    target_curriculum = models.CharField(max_length=100, blank=True)

    target_sdgs = models.ManyToManyField(
        "subject.SDG", blank=True, related_name="received_central_subjects",
    )

    received_at = models.DateTimeField(auto_now_add=True)
    last_received_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "received_central_content"
        db_table = "received_central_subject"
        ordering = ["-last_received_at"]

    def __str__(self):
        return f"{self.subject_name} (central #{self.central_id})"
```

Create `received_central_content/models/received_module.py`:

```python
# received_central_content/models/received_module.py
import os
import uuid

from django.db import models


def _received_module_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("received_central", "module", new_name)


class ReceivedCentralModule(models.Model):
    received_subject = models.ForeignKey(
        "received_central_content.ReceivedCentralSubject",
        on_delete=models.CASCADE,
        related_name="modules",
    )
    central_id = models.IntegerField(unique=True)

    file_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=_received_module_file_path, blank=True, null=True)
    url = models.URLField(max_length=1500, blank=True)
    iframe_code = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "received_central_content"
        db_table = "received_central_module"
        ordering = ["order"]

    def __str__(self):
        return self.file_name
```

Create `received_central_content/models/received_activity.py`:

```python
# received_central_content/models/received_activity.py
from django.db import models


class ReceivedCentralActivity(models.Model):
    class PassingScoreType(models.TextChoices):
        NUMBER = "number", "Number"
        PERCENTAGE = "percentage", "Percentage"

    class RetakeMethod(models.TextChoices):
        HIGHEST = "highest", "Highest Score"
        LATEST = "latest", "Latest Take"
        AVERAGE = "average", "Average"
        FIRST = "first", "First Attempt"

    received_subject = models.ForeignKey(
        "received_central_content.ReceivedCentralSubject",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    central_id = models.IntegerField(unique=True)

    activity_name = models.CharField(max_length=100)
    activity_instruction = models.TextField(blank=True)
    activity_type = models.ForeignKey(
        "activity.ActivityType", on_delete=models.PROTECT,
        related_name="received_central_activities",
    )

    max_score = models.PositiveIntegerField(default=100)
    time_duration = models.PositiveIntegerField(default=0)
    passing_score = models.FloatField(default=0)
    passing_score_type = models.CharField(
        max_length=10, choices=PassingScoreType.choices, default=PassingScoreType.PERCENTAGE,
    )
    max_retake = models.PositiveIntegerField(default=0)
    retake_method = models.CharField(
        max_length=15, choices=RetakeMethod.choices, default=RetakeMethod.HIGHEST,
    )
    shuffle_questions = models.BooleanField(default=False)
    is_graded = models.BooleanField(default=True)

    related_modules = models.ManyToManyField(
        "received_central_content.ReceivedCentralModule",
        blank=True,
        related_name="related_activities",
    )

    class Meta:
        app_label = "received_central_content"
        db_table = "received_central_activity"
        ordering = ["central_id"]

    def __str__(self):
        return self.activity_name
```

Update `received_central_content/models/__init__.py`:

```python
from .received_subject import ReceivedCentralSubject  # noqa: F401
from .received_module import ReceivedCentralModule  # noqa: F401
from .received_activity import ReceivedCentralActivity  # noqa: F401
```

- [ ] **Step 5: Generate migration**

```
cd ~/classedge && env/bin/python manage.py makemigrations received_central_content
```
Expected: `0001_initial.py` created.

- [ ] **Step 6: Run tests — verify they pass**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_models --keepdb -v 2
```
Expected: 6 tests OK.

- [ ] **Step 7: Commit**

```bash
git add received_central_content/models/ received_central_content/migrations/0001_initial.py \
    received_central_content/tests/factories.py \
    received_central_content/tests/test_models.py \
    received_central_content/tests/__init__.py
git commit -m "Add received_central_content models and migration"
```

---

## Task 6: School-side bearer-token auth decorator

**Files:**
- Create: `received_central_content/auth.py`
- Create: `received_central_content/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `received_central_content/tests/test_auth.py`:

```python
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from received_central_content.auth import require_central_token


@override_settings(CENTRAL_INGEST_TOKEN="correct-token-value")
class RequireCentralTokenTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        @require_central_token
        def view(request):
            return HttpResponse("ok")

        self.view = view

    def test_missing_header_returns_401(self):
        req = self.factory.get("/api/central/subjects/")
        resp = self.view(req)
        self.assertEqual(resp.status_code, 401)

    def test_wrong_token_returns_401(self):
        req = self.factory.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer wrong",
        )
        resp = self.view(req)
        self.assertEqual(resp.status_code, 401)

    def test_correct_token_returns_200(self):
        req = self.factory.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer correct-token-value",
        )
        resp = self.view(req)
        self.assertEqual(resp.status_code, 200)

    @override_settings(CENTRAL_INGEST_TOKEN="")
    def test_empty_server_token_always_401(self):
        """If the server has no token configured, every request is rejected."""
        req = self.factory.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer ",
        )
        resp = self.view(req)
        self.assertEqual(resp.status_code, 401)
```

- [ ] **Step 2: Implement the decorator**

Create `received_central_content/auth.py`:

```python
# received_central_content/auth.py
from functools import wraps

from django.conf import settings
from django.http import JsonResponse


def require_central_token(view_func):
    """Require an Authorization: Bearer <CENTRAL_INGEST_TOKEN> header.

    Returns 401 JsonResponse otherwise. Empty/unset server token also
    always rejects (defense in depth against a misconfigured deployment).
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        server_token = getattr(settings, "CENTRAL_INGEST_TOKEN", "") or ""
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not server_token:
            return JsonResponse({"error": "unauthorized"}, status=401)
        if not header.startswith("Bearer "):
            return JsonResponse({"error": "unauthorized"}, status=401)
        supplied = header[len("Bearer "):].strip()
        if supplied != server_token:
            return JsonResponse({"error": "unauthorized"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped
```

- [ ] **Step 3: Run tests — verify they pass**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_auth --keepdb -v 2
```
Expected: 4 tests OK.

- [ ] **Step 4: Commit**

```bash
git add received_central_content/auth.py received_central_content/tests/test_auth.py
git commit -m "Add bearer-token auth decorator for central ingest endpoints"
```

---

## Task 7: School-side catalog API (`GET /api/central/subjects/`)

**Files:**
- Create: `received_central_content/views/__init__.py`
- Create: `received_central_content/views/catalog.py`
- Create: `received_central_content/tests/test_catalog_api.py`
- Create: `received_central_content/urls.py`
- Modify: `lms/urls.py` — include received_central_content URLs under `api/central/`

- [ ] **Step 1: Write the failing tests**

Create `received_central_content/tests/test_catalog_api.py`:

```python
from django.test import TestCase, override_settings, Client

from subject.models.subject_model import Subject


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class CatalogAPITests(TestCase):
    def setUp(self):
        Subject.objects.create(subject_name="Math 101", subject_code="MATH101")
        Subject.objects.create(subject_name="Geometry", subject_code="MATH201")
        self.client = Client()

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/central/subjects/")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_token_returns_401(self):
        resp = self.client.get(
            "/api/central/subjects/", HTTP_AUTHORIZATION="Bearer wrong",
        )
        self.assertEqual(resp.status_code, 401)

    def test_list_subjects(self):
        resp = self.client.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        names = {row["subject_name"] for row in data}
        self.assertEqual(names, {"Math 101", "Geometry"})
        self.assertIn("id", data[0])
        self.assertIn("subject_code", data[0])

    def test_ordered_by_name(self):
        resp = self.client.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        names = [row["subject_name"] for row in resp.json()]
        self.assertEqual(names, sorted(names))
```

- [ ] **Step 2: Run tests — verify they fail**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_catalog_api --keepdb -v 2
```
Expected: URL not found / 404.

- [ ] **Step 3: Implement the view**

Create `received_central_content/views/__init__.py` (empty).

Create `received_central_content/views/catalog.py`:

```python
# received_central_content/views/catalog.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from received_central_content.auth import require_central_token
from subject.models.subject_model import Subject


@require_http_methods(["GET"])
@require_central_token
def list_subjects(request):
    rows = Subject.objects.order_by("subject_name").values(
        "id", "subject_name", "subject_code",
    )
    return JsonResponse(list(rows), safe=False)
```

- [ ] **Step 4: Create URL routing**

Create `received_central_content/urls.py`:

```python
# received_central_content/urls.py
from django.urls import path

from received_central_content.views import catalog

app_name = "received_central_content"

urlpatterns = [
    path("subjects/", catalog.list_subjects, name="list_subjects"),
]
```

Modify `lms/urls.py` — add to `urlpatterns` (look for the existing `urlpatterns = [...]` list; insert near the bottom alongside other `api/` includes):

```python
from django.urls import path, include

urlpatterns = [
    # ... existing entries ...
    path("api/central/", include("received_central_content.urls")),
]
```

- [ ] **Step 5: Run tests — verify they pass**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_catalog_api --keepdb -v 2
```
Expected: 4 tests OK.

- [ ] **Step 6: Commit**

```bash
git add received_central_content/views/ received_central_content/urls.py \
    received_central_content/tests/test_catalog_api.py lms/urls.py
git commit -m "Add /api/central/subjects/ catalog endpoint"
```

---

## Task 8: School-side ingest API — happy path, upsert, orphan delete

**Files:**
- Create: `received_central_content/views/ingest.py`
- Create: `received_central_content/tests/test_ingest_api.py`
- Modify: `received_central_content/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `received_central_content/tests/test_ingest_api.py`:

```python
import json

from django.test import TestCase, override_settings, Client

from received_central_content.models import (
    ReceivedCentralSubject, ReceivedCentralModule, ReceivedCentralActivity,
)
from received_central_content.tests.factories import (
    get_or_create_sdg, get_or_create_activity_type,
)


def _auth_headers():
    return {"HTTP_AUTHORIZATION": "Bearer " + "t" * 40}


def _base_payload():
    return {
        "central_id": 42,
        "central_version": 1,
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


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class IngestHappyPathTests(TestCase):
    def setUp(self):
        get_or_create_sdg("Quality Education")
        get_or_create_activity_type("Quiz")
        self.client = Client()

    def test_no_token_returns_401(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(_base_payload())},
        )
        self.assertEqual(resp.status_code, 401)

    def test_first_push_creates_rows(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(_base_payload())},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        self.assertEqual(ReceivedCentralModule.objects.count(), 1)
        self.assertEqual(ReceivedCentralActivity.objects.count(), 1)
        subject = ReceivedCentralSubject.objects.get()
        self.assertEqual(subject.central_id, 42)
        self.assertEqual(subject.central_version, 1)
        self.assertEqual(subject.target_sdgs.count(), 1)
        activity = ReceivedCentralActivity.objects.get()
        self.assertEqual(activity.related_modules.count(), 1)

    def test_response_shape(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(_base_payload())},
            **_auth_headers(),
        )
        body = resp.json()
        self.assertIn("received_subject_id", body)
        self.assertEqual(body["central_version"], 1)
        self.assertIn("received_at", body)

    def test_repush_upserts_and_deletes_orphans(self):
        # First push.
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(_base_payload())},
            **_auth_headers(),
        )
        # Second push: bump version, drop the module (orphan it).
        second = _base_payload()
        second["central_version"] = 2
        second["subject_name"] = "Algebra 1 Updated"
        second["modules"] = []
        # remove the activity's reference to the now-deleted module
        second["activities"][0]["related_module_central_ids"] = []
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(second)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        subject = ReceivedCentralSubject.objects.get()
        self.assertEqual(subject.central_version, 2)
        self.assertEqual(subject.subject_name, "Algebra 1 Updated")
        self.assertEqual(ReceivedCentralModule.objects.count(), 0)
        self.assertEqual(ReceivedCentralActivity.objects.count(), 1)
```

- [ ] **Step 2: Run tests — verify they fail**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_ingest_api --keepdb -v 2
```
Expected: URL not found.

- [ ] **Step 3: Implement the ingest view**

Create `received_central_content/views/ingest.py`:

```python
# received_central_content/views/ingest.py
import json

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from activity.models import ActivityType
from received_central_content.auth import require_central_token
from received_central_content.models import (
    ReceivedCentralSubject, ReceivedCentralModule, ReceivedCentralActivity,
)
from subject.models.sdg_models import SDG


def _err(code, error, **extra):
    payload = {"error": error}
    payload.update(extra)
    return JsonResponse(payload, status=code)


def _resolve_sdgs(names):
    if not names:
        return [], []
    rows = list(SDG.objects.filter(name__in=names))
    found = {r.name for r in rows}
    missing = [n for n in names if n not in found]
    return rows, missing


def _resolve_activity_types(names):
    unique = list(set(names))
    rows = list(ActivityType.objects.filter(name__in=unique))
    by_name = {r.name: r for r in rows}
    missing = [n for n in unique if n not in by_name]
    return by_name, missing


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
    if central_id is None or central_version is None:
        return _err(400, "missing_required_fields")

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
            subject, _created = ReceivedCentralSubject.objects.update_or_create(
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
            subject.target_sdgs.set(sdg_rows)

            # Upsert modules + delete orphans
            module_payloads = payload.get("modules") or []
            kept_module_central_ids = {m["central_id"] for m in module_payloads}
            ReceivedCentralModule.objects.filter(
                received_subject=subject,
            ).exclude(central_id__in=kept_module_central_ids).delete()

            module_by_central_id = {}
            for m in module_payloads:
                mod, _ = ReceivedCentralModule.objects.update_or_create(
                    central_id=m["central_id"],
                    defaults={
                        "received_subject": subject,
                        "file_name": m.get("file_name", ""),
                        "description": m.get("description", ""),
                        "url": m.get("url", ""),
                        "iframe_code": m.get("iframe_code", ""),
                        "order": m.get("order", 0),
                    },
                )
                module_by_central_id[m["central_id"]] = mod

            # Upsert activities + delete orphans
            activity_payloads = payload.get("activities") or []
            kept_activity_central_ids = {a["central_id"] for a in activity_payloads}
            ReceivedCentralActivity.objects.filter(
                received_subject=subject,
            ).exclude(central_id__in=kept_activity_central_ids).delete()

            for a in activity_payloads:
                act, _ = ReceivedCentralActivity.objects.update_or_create(
                    central_id=a["central_id"],
                    defaults={
                        "received_subject": subject,
                        "activity_name": a.get("activity_name", ""),
                        "activity_instruction": a.get("activity_instruction", ""),
                        "activity_type": at_by_name[a["activity_type"]],
                        "max_score": a.get("max_score", 100),
                        "time_duration": a.get("time_duration", 0),
                        "passing_score": a.get("passing_score", 0),
                        "passing_score_type": a.get("passing_score_type", "percentage"),
                        "max_retake": a.get("max_retake", 0),
                        "retake_method": a.get("retake_method", "highest"),
                        "shuffle_questions": a.get("shuffle_questions", False),
                        "is_graded": a.get("is_graded", True),
                    },
                )
                related_ids = a.get("related_module_central_ids") or []
                unknown = [cid for cid in related_ids if cid not in module_by_central_id]
                if unknown:
                    raise ValueError(
                        f"unresolved_related_modules:{unknown}"
                    )
                act.related_modules.set(
                    [module_by_central_id[cid] for cid in related_ids]
                )

            # Files: wired in Task 9. For now, ignore file_part refs.
    except ValueError as e:
        message = str(e)
        if message.startswith("unresolved_related_modules:"):
            return _err(422, "unresolved_related_modules", detail=message)
        return _err(500, "server_error", detail=message)

    return JsonResponse(
        {
            "received_subject_id": subject.pk,
            "central_version": subject.central_version,
            "received_at": timezone.now().isoformat(),
        },
        status=200,
    )
```

Modify `received_central_content/urls.py`:

```python
# received_central_content/urls.py
from django.urls import path

from received_central_content.views import catalog, ingest

app_name = "received_central_content"

urlpatterns = [
    path("subjects/", catalog.list_subjects, name="list_subjects"),
    path("ingest/", ingest.ingest_subject, name="ingest_subject"),
]
```

- [ ] **Step 4: Run tests — verify they pass**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_ingest_api --keepdb -v 2
```
Expected: 4 tests OK.

- [ ] **Step 5: Commit**

```bash
git add received_central_content/views/ingest.py received_central_content/urls.py \
    received_central_content/tests/test_ingest_api.py
git commit -m "Add /api/central/ingest/ happy path with upsert and orphan delete"
```

---

## Task 9: School-side ingest — file handling + validation errors

**Files:**
- Modify: `received_central_content/views/ingest.py`
- Modify: `received_central_content/tests/test_ingest_api.py`

- [ ] **Step 1: Add the failing tests**

Append to `received_central_content/tests/test_ingest_api.py`:

```python
from django.core.files.uploadedfile import SimpleUploadedFile


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class IngestValidationTests(TestCase):
    def setUp(self):
        get_or_create_sdg("Quality Education")
        get_or_create_activity_type("Quiz")
        self.client = Client()

    def test_unresolved_sdg_returns_422_and_rolls_back(self):
        payload = _base_payload()
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
        payload = _base_payload()
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
        payload = _base_payload()
        payload["modules"][0]["file_part"] = "module_0_file"
        # don't attach the file part
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "missing_file_part")

    def test_subject_photo_uploaded(self):
        payload = _base_payload()
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
        payload = _base_payload()
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
        m = ReceivedCentralModule.objects.get()
        self.assertTrue(m.file.name)
```

- [ ] **Step 2: Update `ingest_subject` view for files**

Modify `received_central_content/views/ingest.py` — inside the `transaction.atomic()` block, after the activities loop and before the closing of the try:

```python
            # Handle files (inside the same transaction).
            subject_photo_part = payload.get("subject_photo_part")
            if subject_photo_part:
                f = request.FILES.get(subject_photo_part)
                if not f:
                    raise ValueError("missing_file_part:subject_photo")
                subject.subject_photo.save(f.name, f, save=True)

            for i, m in enumerate(module_payloads):
                file_part = m.get("file_part")
                if not file_part:
                    continue
                f = request.FILES.get(file_part)
                if not f:
                    raise ValueError(f"missing_file_part:{file_part}")
                mod = module_by_central_id[m["central_id"]]
                mod.file.save(f.name, f, save=True)
```

And update the exception handler to translate the `missing_file_part` marker into a 400:

```python
    except ValueError as e:
        message = str(e)
        if message.startswith("unresolved_related_modules:"):
            return _err(422, "unresolved_related_modules", detail=message)
        if message.startswith("missing_file_part:"):
            return _err(400, "missing_file_part", detail=message.split(":", 1)[1])
        return _err(500, "server_error", detail=message)
```

- [ ] **Step 3: Run tests — verify they pass**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_ingest_api --keepdb -v 2
```
Expected: 9 tests OK (4 from Task 8 + 5 new).

- [ ] **Step 4: Commit**

```bash
git add received_central_content/views/ingest.py \
    received_central_content/tests/test_ingest_api.py
git commit -m "Add file handling and validation errors to ingest endpoint"
```

---

## Task 10: School-side ingest DELETE

**Files:**
- Modify: `received_central_content/views/ingest.py`
- Modify: `received_central_content/urls.py`
- Create: `received_central_content/tests/test_ingest_delete.py`

- [ ] **Step 1: Write the failing tests**

Create `received_central_content/tests/test_ingest_delete.py`:

```python
from django.test import TestCase, override_settings, Client

from received_central_content.models import ReceivedCentralSubject
from received_central_content.tests.factories import (
    make_received_subject, make_received_module, make_received_activity,
)


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class IngestDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_no_token_returns_401(self):
        make_received_subject(central_id=42)
        resp = self.client.delete("/api/central/ingest/42/")
        self.assertEqual(resp.status_code, 401)

    def test_delete_cascades(self):
        subject = make_received_subject(central_id=42)
        make_received_module(received_subject=subject)
        make_received_activity(received_subject=subject)
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
```

- [ ] **Step 2: Implement the view**

Append to `received_central_content/views/ingest.py`:

```python
@csrf_exempt
@require_http_methods(["DELETE"])
@require_central_token
def delete_subject(request, central_id: int):
    try:
        subject = ReceivedCentralSubject.objects.get(central_id=central_id)
    except ReceivedCentralSubject.DoesNotExist:
        return _err(404, "not_found")
    subject.delete()
    return JsonResponse({}, status=204)
```

Modify `received_central_content/urls.py`:

```python
urlpatterns = [
    path("subjects/", catalog.list_subjects, name="list_subjects"),
    path("ingest/", ingest.ingest_subject, name="ingest_subject"),
    path("ingest/<int:central_id>/", ingest.delete_subject, name="delete_subject"),
]
```

- [ ] **Step 3: Run tests — verify they pass**

```
cd ~/classedge && env/bin/python manage.py test received_central_content.tests.test_ingest_delete --keepdb -v 2
```
Expected: 3 tests OK.

- [ ] **Step 4: Run the full school-side test suite once as a gate**

```
cd ~/classedge && env/bin/python manage.py test received_central_content --keepdb -v 2
```
Expected: all received_central_content tests pass.

- [ ] **Step 5: Commit**

```bash
git add received_central_content/views/ingest.py received_central_content/urls.py \
    received_central_content/tests/test_ingest_delete.py
git commit -m "Add DELETE /api/central/ingest/<id>/ endpoint"
```

---

## Task 11: Install `responses` (HTTP mock lib) + `.env.example` entry

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Add the dependency**

Append to `requirements.txt`:

```
responses==0.25.3
```

- [ ] **Step 2: Install into the venv**

```
cd ~/classedge && env/bin/pip install responses==0.25.3
```

- [ ] **Step 3: Add the env var**

Append to `.env.example`:

```
# Shared bearer token for central -> school push API (Sub-2).
CENTRAL_INGEST_TOKEN=
```

Engineer must also add `CENTRAL_INGEST_TOKEN=some-random-40-char-hex` to their local `.env` (gitignored).

- [ ] **Step 4: Verify imports work**

```
cd ~/classedge && env/bin/python -c "import responses; print(responses.__version__)"
```
Expected: `0.25.3`.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example
git commit -m "Add responses lib and CENTRAL_INGEST_TOKEN env entry"
```

---

## Task 12: Central-side payload builder

**Files:**
- Create: `central_content/push.py`
- Create: `central_content/tests/test_payload_builder.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_payload_builder.py`:

```python
from django.test import TestCase

from central_content.push import build_push_payload
from central_content.tests.factories import (
    make_central_subject, make_central_module, make_central_activity,
    get_or_create_sdg, get_or_create_activity_type,
)


class BuildPushPayloadTests(TestCase):
    def test_basic_subject(self):
        subject = make_central_subject(
            subject_name="Algebra 1",
            version=3,
            subject_code="ALG101",
            unit=3,
        )
        payload, files = build_push_payload(subject)
        self.assertEqual(payload["central_id"], subject.pk)
        self.assertEqual(payload["central_version"], 3)
        self.assertEqual(payload["subject_name"], "Algebra 1")
        self.assertEqual(payload["subject_code"], "ALG101")
        self.assertEqual(payload["modules"], [])
        self.assertEqual(payload["activities"], [])
        self.assertEqual(files, {})

    def test_stripped_fields_not_in_payload(self):
        subject = make_central_subject()
        payload, _ = build_push_payload(subject)
        for forbidden in [
            "id", "state", "created_by", "submitted_by", "reviewed_by",
            "review_notes", "source_notes", "created_at", "updated_at",
        ]:
            self.assertNotIn(
                forbidden, payload,
                f"Field {forbidden!r} must not appear in push payload",
            )

    def test_sdgs_emitted_as_names(self):
        subject = make_central_subject()
        subject.target_sdgs.add(get_or_create_sdg("Quality Education"))
        payload, _ = build_push_payload(subject)
        self.assertEqual(payload["target_sdgs"], ["Quality Education"])

    def test_modules_included(self):
        subject = make_central_subject()
        make_central_module(central_subject=subject, file_name="Mod 1", order=0)
        payload, _ = build_push_payload(subject)
        self.assertEqual(len(payload["modules"]), 1)
        m = payload["modules"][0]
        self.assertEqual(m["file_name"], "Mod 1")
        self.assertEqual(m["order"], 0)
        self.assertIn("central_id", m)

    def test_activity_related_modules_as_central_ids(self):
        subject = make_central_subject()
        module = make_central_module(central_subject=subject)
        activity = make_central_activity(central_subject=subject)
        activity.related_modules.add(module)
        payload, _ = build_push_payload(subject)
        a = payload["activities"][0]
        self.assertEqual(a["related_module_central_ids"], [module.pk])
        self.assertEqual(a["activity_type"], activity.activity_type.name)
```

- [ ] **Step 2: Implement the builder**

Create `central_content/push.py`:

```python
# central_content/push.py
from typing import Any


def build_push_payload(central_subject) -> tuple[dict[str, Any], dict[str, Any]]:
    """Walk a CentralSubject tree and return (json_payload, files_dict).

    files_dict maps multipart part key -> a Django File-like object (opened).
    Callers are responsible for closing the files after the HTTP request.
    """
    files: dict[str, Any] = {}

    modules = list(central_subject.modules.order_by("order", "pk"))
    activities = list(central_subject.activities.prefetch_related("related_modules"))

    module_payloads = []
    for i, m in enumerate(modules):
        entry = {
            "central_id": m.pk,
            "file_name": m.file_name,
            "description": m.description,
            "order": m.order,
            "url": m.url,
            "iframe_code": m.iframe_code,
        }
        if m.file:
            key = f"module_{i}_file"
            entry["file_part"] = key
            files[key] = m.file.open("rb")
        module_payloads.append(entry)

    activity_payloads = []
    for a in activities:
        activity_payloads.append({
            "central_id": a.pk,
            "activity_name": a.activity_name,
            "activity_instruction": a.activity_instruction,
            "activity_type": a.activity_type.name,
            "max_score": a.max_score,
            "time_duration": a.time_duration,
            "passing_score": a.passing_score,
            "passing_score_type": a.passing_score_type,
            "max_retake": a.max_retake,
            "retake_method": a.retake_method,
            "shuffle_questions": a.shuffle_questions,
            "is_graded": a.is_graded,
            "related_module_central_ids": [
                rm.pk for rm in a.related_modules.all()
            ],
        })

    payload: dict[str, Any] = {
        "central_id": central_subject.pk,
        "central_version": central_subject.version,
        "subject_name": central_subject.subject_name,
        "subject_descriptive_title": central_subject.subject_descriptive_title,
        "subject_short_name": central_subject.subject_short_name,
        "subject_description": central_subject.subject_description,
        "subject_code": central_subject.subject_code,
        "subject_type": central_subject.subject_type,
        "unit": central_subject.unit,
        "target_grade_level": central_subject.target_grade_level,
        "target_curriculum": central_subject.target_curriculum,
        "target_sdgs": [sdg.name for sdg in central_subject.target_sdgs.all()],
        "modules": module_payloads,
        "activities": activity_payloads,
    }

    if central_subject.subject_photo:
        payload["subject_photo_part"] = "subject_photo"
        files["subject_photo"] = central_subject.subject_photo.open("rb")

    return payload, files
```

- [ ] **Step 3: Run tests — verify they pass**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_payload_builder --keepdb -v 2
```
Expected: 5 tests OK.

- [ ] **Step 4: Commit**

```bash
git add central_content/push.py central_content/tests/test_payload_builder.py
git commit -m "Add build_push_payload helper for central->school snapshots"
```

---

## Task 13: Central-side `push_subject_to_school` function

**Files:**
- Modify: `central_content/push.py`
- Create: `central_content/tests/test_push_function.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_push_function.py`:

```python
import json

import responses
from requests.exceptions import ConnectionError

from django.test import TestCase
from django.utils import timezone

from central_content.models import PushJob, SchoolSubjectBinding
from central_content.push import push_subject_to_school
from central_content.tests.factories import (
    make_binding, make_central_subject, make_publisher, make_school,
    make_central_module,
)


class PushFunctionTests(TestCase):
    def _setup_binding(self, version=1):
        subject = make_central_subject(version=version)
        school = make_school(base_url="https://school.example.com")
        return make_binding(central_subject=subject, target_school=school)

    @responses.activate
    def test_happy_path_updates_binding_and_creates_success_job(self):
        binding = self._setup_binding(version=3)
        publisher = make_publisher()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"received_subject_id": 99, "central_version": 3, "received_at": "x"},
            status=200,
        )
        job = push_subject_to_school(binding, triggered_by=publisher)
        self.assertEqual(job.status, PushJob.Status.SUCCESS)
        self.assertEqual(job.kind, PushJob.Kind.PUSH)
        self.assertEqual(job.http_status, 200)
        binding.refresh_from_db()
        self.assertEqual(binding.pushed_version, 3)
        self.assertIsNotNone(binding.last_pushed_at)

    @responses.activate
    def test_401_from_school_creates_failed_job(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"error": "unauthorized"},
            status=401,
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 401)
        binding.refresh_from_db()
        self.assertIsNone(binding.pushed_version)

    @responses.activate
    def test_422_unresolved_sdg_creates_failed_job(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"error": "unresolved_sdgs", "names": ["X"]},
            status=422,
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 422)
        self.assertIn("unresolved_sdgs", job.response_body)

    @responses.activate
    def test_5xx_creates_failed_job(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            body="boom", status=500,
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 500)

    @responses.activate
    def test_connection_error_creates_failed_job_no_http_status(self):
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            body=ConnectionError("boom"),
        )
        job = push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertIsNone(job.http_status)
        self.assertIn("boom", job.error_message)

    @responses.activate
    def test_audit_log_written_on_success(self):
        from central_content.models import AuditLogEntry
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"received_subject_id": 1, "central_version": 1, "received_at": "x"},
            status=200,
        )
        push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertTrue(
            AuditLogEntry.objects.filter(action="push").exists()
        )

    @responses.activate
    def test_audit_log_written_on_failure(self):
        from central_content.models import AuditLogEntry
        binding = self._setup_binding()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            status=500,
        )
        push_subject_to_school(binding, triggered_by=make_publisher())
        self.assertTrue(
            AuditLogEntry.objects.filter(action="push_failed").exists()
        )
```

- [ ] **Step 2: Implement the push function**

Append to `central_content/push.py`:

```python
import requests
from django.db import transaction
from django.utils import timezone


PUSH_TIMEOUT_SECONDS = 60


def push_subject_to_school(binding, triggered_by):
    """Build the payload and POST it to the target school.

    Always returns a PushJob. Never raises — HTTP and connection errors are
    captured onto the PushJob. On 2xx, updates binding.pushed_version and
    binding.last_pushed_at in a transaction alongside the PushJob insert.
    """
    from central_content.models import PushJob, AuditLogEntry

    payload, files = build_push_payload(binding.central_subject)
    data = {"payload": __json_dumps(payload)}
    files_for_requests = {k: (getattr(f, "name", k), f) for k, f in files.items()}

    url = binding.target_school.base_url.rstrip("/") + "/api/central/ingest/"
    headers = {"Authorization": f"Bearer {binding.target_school.api_token}"}

    http_status = None
    response_body = ""
    error_message = ""
    try:
        resp = requests.post(
            url, data=data, files=files_for_requests,
            headers=headers, timeout=PUSH_TIMEOUT_SECONDS,
        )
        http_status = resp.status_code
        response_body = (resp.text or "")[:10000]
    except requests.RequestException as e:
        error_message = str(e)[:10000]
    finally:
        for f in files.values():
            try:
                f.close()
            except Exception:
                pass

    with transaction.atomic():
        if http_status is not None and 200 <= http_status < 300:
            binding.pushed_version = binding.central_subject.version
            binding.last_pushed_at = timezone.now()
            binding.save(update_fields=["pushed_version", "last_pushed_at"])
            status = PushJob.Status.SUCCESS
            audit_action = "push"
        else:
            status = PushJob.Status.FAILED
            audit_action = "push_failed"

        job = PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind=PushJob.Kind.PUSH,
            status=status,
            subject_version=binding.central_subject.version,
            http_status=http_status,
            response_body=response_body,
            error_message=error_message,
            finished_at=timezone.now(),
            triggered_by=triggered_by,
        )
        AuditLogEntry.objects.create(
            actor=triggered_by,
            action=audit_action,
            subject_type="SchoolSubjectBinding",
            subject_id=binding.pk,
            details={
                "central_subject_id": binding.central_subject_id,
                "target_school_id": binding.target_school_id,
                "http_status": http_status,
                "error_message": error_message,
            },
        )

    return job


def __json_dumps(payload):
    import json
    return json.dumps(payload)
```

Note: the exact `AuditLogEntry` signature depends on Sub-1. If Sub-1's `AuditLogEntry` takes different kwargs than `actor=`, `action=`, `subject_type=`, `subject_id=`, `details=`, adapt the call to match the Sub-1 definition before writing the test. Grep for `class AuditLogEntry` in `central_content/models/audit_log.py` and match its fields.

- [ ] **Step 3: Run tests — verify they pass**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_push_function --keepdb -v 2
```
Expected: 7 tests OK.

- [ ] **Step 4: Commit**

```bash
git add central_content/push.py central_content/tests/test_push_function.py
git commit -m "Add push_subject_to_school function with error capture"
```

---

## Task 14: Central-side `delete_subject_from_school` function

**Files:**
- Modify: `central_content/push.py`
- Create: `central_content/tests/test_delete_function.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_delete_function.py`:

```python
import responses
from requests.exceptions import ConnectionError

from django.test import TestCase

from central_content.models import PushJob, SchoolSubjectBinding
from central_content.push import delete_subject_from_school
from central_content.tests.factories import (
    make_binding, make_publisher,
)


class DeleteFunctionTests(TestCase):
    @responses.activate
    def test_204_is_success(self):
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, status=204)
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.SUCCESS)
        self.assertEqual(job.kind, PushJob.Kind.DELETE)
        self.assertEqual(job.http_status, 204)

    @responses.activate
    def test_404_treated_as_success(self):
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, json={"error": "not_found"}, status=404)
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.SUCCESS)
        self.assertEqual(job.http_status, 404)

    @responses.activate
    def test_connection_error_is_failure(self):
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, body=ConnectionError("boom"))
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertIsNone(job.http_status)
        self.assertIn("boom", job.error_message)

    @responses.activate
    def test_500_is_failure(self):
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        url = f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/"
        responses.add(responses.DELETE, url, status=500)
        job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(job.status, PushJob.Status.FAILED)
        self.assertEqual(job.http_status, 500)
```

- [ ] **Step 2: Implement the delete function**

Append to `central_content/push.py`:

```python
def delete_subject_from_school(binding, triggered_by):
    """DELETE the received subject on the target school. Idempotent on 404."""
    from central_content.models import PushJob, AuditLogEntry

    url = (
        binding.target_school.base_url.rstrip("/")
        + f"/api/central/ingest/{binding.central_subject_id}/"
    )
    headers = {"Authorization": f"Bearer {binding.target_school.api_token}"}

    http_status = None
    response_body = ""
    error_message = ""
    try:
        resp = requests.delete(url, headers=headers, timeout=PUSH_TIMEOUT_SECONDS)
        http_status = resp.status_code
        response_body = (resp.text or "")[:10000]
    except requests.RequestException as e:
        error_message = str(e)[:10000]

    success = http_status is not None and (
        200 <= http_status < 300 or http_status == 404
    )
    with transaction.atomic():
        job = PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind=PushJob.Kind.DELETE,
            status=PushJob.Status.SUCCESS if success else PushJob.Status.FAILED,
            subject_version=binding.central_subject.version,
            http_status=http_status,
            response_body=response_body,
            error_message=error_message,
            finished_at=timezone.now(),
            triggered_by=triggered_by,
        )
        AuditLogEntry.objects.create(
            actor=triggered_by,
            action="unbind" if success else "unbind_failed",
            subject_type="SchoolSubjectBinding",
            subject_id=binding.pk,
            details={
                "central_subject_id": binding.central_subject_id,
                "target_school_id": binding.target_school_id,
                "http_status": http_status,
                "error_message": error_message,
            },
        )
    return job
```

- [ ] **Step 3: Run tests — verify they pass**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_delete_function --keepdb -v 2
```
Expected: 4 tests OK.

- [ ] **Step 4: Commit**

```bash
git add central_content/push.py central_content/tests/test_delete_function.py
git commit -m "Add delete_subject_from_school helper"
```

---

## Task 15: Central-side Schools CRUD views + templates

**Files:**
- Create: `central_content/views/schools.py`
- Create: `central_content/forms.py` (or append `SchoolForm` to existing)
- Create: `central_content/templates/central_content/schools/list.html`
- Create: `central_content/templates/central_content/schools/form.html`
- Create: `central_content/templates/central_content/schools/token_reveal.html`
- Create: `central_content/tests/test_schools_views.py`
- Modify: `central_content/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_schools_views.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse

from central_content.models import School
from central_content.tests.factories import (
    make_publisher, make_editor, make_reviewer, make_school,
)


def _login(client, staff):
    """Sub-1 CentralStaff login helper — mirror whatever Sub-1 tests use."""
    session = client.session
    session["central_staff_id"] = staff.pk
    session.save()
    return client


class SchoolsViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_list_requires_login(self):
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_list_publisher_sees_page(self):
        _login(self.client, make_publisher())
        make_school(name="HCCCI")
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HCCCI")

    def test_list_reviewer_read_only(self):
        _login(self.client, make_reviewer())
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Add school")

    def test_list_editor_forbidden(self):
        _login(self.client, make_editor())
        resp = self.client.get("/schools/")
        self.assertEqual(resp.status_code, 403)

    def test_create_publisher(self):
        _login(self.client, make_publisher())
        resp = self.client.post("/schools/new", {
            "name": "New School",
            "base_url": "https://new.example.com",
            "notes": "",
            "is_active": "on",
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(School.objects.filter(name="New School").exists())
        school = School.objects.get(name="New School")
        self.assertEqual(len(school.api_token), 40)
        # Token reveal page should show the token
        self.assertContains(resp, school.api_token)

    def test_create_editor_forbidden(self):
        _login(self.client, make_editor())
        resp = self.client.post("/schools/new", {"name": "X", "base_url": "https://x"})
        self.assertEqual(resp.status_code, 403)

    def test_edit_updates_fields(self):
        _login(self.client, make_publisher())
        school = make_school(name="Old Name")
        resp = self.client.post(f"/schools/{school.pk}/edit", {
            "name": "New Name",
            "base_url": school.base_url,
            "notes": "",
            "is_active": "on",
        }, follow=True)
        school.refresh_from_db()
        self.assertEqual(school.name, "New Name")

    def test_regenerate_token(self):
        _login(self.client, make_publisher())
        school = make_school()
        old_token = school.api_token
        resp = self.client.post(
            f"/schools/{school.pk}/regenerate-token", follow=True,
        )
        school.refresh_from_db()
        self.assertNotEqual(school.api_token, old_token)
        self.assertEqual(len(school.api_token), 40)
```

Note: The `_login` helper mimics whatever Sub-1 tests do to authenticate a `CentralStaff`. Before writing this task, inspect the existing Sub-1 `test_view_*.py` files and copy their login helper verbatim rather than reinventing it.

- [ ] **Step 2: Add `SchoolForm`**

Check if `central_content/forms.py` exists. If it exists, append. If not, create it.

```python
# central_content/forms.py  (append or create)
from django import forms

from central_content.models import School


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "base_url", "is_active", "notes"]
```

- [ ] **Step 3: Implement the views**

Create `central_content/views/schools.py`:

```python
# central_content/views/schools.py
import secrets

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from central_content.forms import SchoolForm
from central_content.models import AuditLogEntry, School
from central_content.permissions import central_role_required


def _get_staff(request):
    """Return the logged-in CentralStaff or None — mirror Sub-1 helper."""
    from central_content.models import CentralStaff
    staff_id = request.session.get("central_staff_id")
    if not staff_id:
        return None
    return CentralStaff.objects.filter(pk=staff_id).first()


@central_role_required("publisher", "reviewer")
def school_list(request):
    staff = _get_staff(request)
    can_edit = staff.role == "publisher"
    schools = School.objects.all().order_by("name")
    return render(
        request,
        "central_content/schools/list.html",
        {"schools": schools, "can_edit": can_edit},
    )


@central_role_required("publisher")
def school_create(request):
    if request.method == "POST":
        form = SchoolForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                school = form.save(commit=False)
                school.api_token = secrets.token_hex(20)
                school.created_by = _get_staff(request)
                school.save()
                AuditLogEntry.objects.create(
                    actor=_get_staff(request),
                    action="school_created",
                    subject_type="School",
                    subject_id=school.pk,
                    details={"name": school.name, "base_url": school.base_url},
                )
            return render(
                request,
                "central_content/schools/token_reveal.html",
                {"school": school},
            )
    else:
        form = SchoolForm()
    return render(
        request,
        "central_content/schools/form.html",
        {"form": form, "mode": "create"},
    )


@central_role_required("publisher")
def school_edit(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    if request.method == "POST":
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                AuditLogEntry.objects.create(
                    actor=_get_staff(request),
                    action="school_edited",
                    subject_type="School",
                    subject_id=school.pk,
                    details={"changed": list(form.changed_data)},
                )
            return redirect("school_list")
    else:
        form = SchoolForm(instance=school)
    return render(
        request,
        "central_content/schools/form.html",
        {"form": form, "mode": "edit", "school": school},
    )


@central_role_required("publisher")
@require_http_methods(["POST"])
def school_regenerate_token(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    with transaction.atomic():
        school.api_token = secrets.token_hex(20)
        school.save(update_fields=["api_token", "updated_at"])
        AuditLogEntry.objects.create(
            actor=_get_staff(request),
            action="token_regen",
            subject_type="School",
            subject_id=school.pk,
            details={},
        )
    return render(
        request,
        "central_content/schools/token_reveal.html",
        {"school": school, "regenerated": True},
    )
```

Note on `@central_role_required`: Sub-1 defines this decorator in `central_content/permissions.py`. When multiple roles are accepted (publisher + reviewer), pass them as varargs. Inspect the Sub-1 implementation to confirm the signature before writing; if it only takes one role, update the decorator OR gate the reviewer case with a second `if` in the view.

- [ ] **Step 4: Create templates**

Create `central_content/templates/central_content/schools/list.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Schools{% endblock %}
{% block content %}
<div class="p-6">
  <div class="flex items-center justify-between mb-4">
    <h1 class="text-2xl font-semibold">Schools</h1>
    {% if can_edit %}
      <a href="{% url 'school_create' %}" class="btn btn-primary">Add school</a>
    {% endif %}
  </div>
  <table class="min-w-full bg-gray-900 text-sm">
    <thead><tr class="text-left">
      <th class="p-2">Name</th>
      <th class="p-2">Base URL</th>
      <th class="p-2">Active</th>
      {% if can_edit %}<th class="p-2">Actions</th>{% endif %}
    </tr></thead>
    <tbody>
    {% for s in schools %}
      <tr class="border-t border-gray-700">
        <td class="p-2">{{ s.name }}</td>
        <td class="p-2"><code>{{ s.base_url }}</code></td>
        <td class="p-2">{{ s.is_active|yesno:"yes,no" }}</td>
        {% if can_edit %}
          <td class="p-2">
            <a href="{% url 'school_edit' s.pk %}">Edit</a>
            &middot;
            <form method="post" action="{% url 'school_regenerate_token' s.pk %}" style="display:inline">
              {% csrf_token %}
              <button type="submit">Regenerate token</button>
            </form>
          </td>
        {% endif %}
      </tr>
    {% empty %}
      <tr><td colspan="4" class="p-4 text-gray-400">No schools yet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

Create `central_content/templates/central_content/schools/form.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{{ mode|title }} school{% endblock %}
{% block content %}
<div class="p-6 max-w-lg">
  <h1 class="text-2xl font-semibold mb-4">
    {% if mode == "create" %}Add school{% else %}Edit {{ school.name }}{% endif %}
  </h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Save</button>
    <a href="{% url 'school_list' %}">Cancel</a>
  </form>
</div>
{% endblock %}
```

Create `central_content/templates/central_content/schools/token_reveal.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}School token{% endblock %}
{% block content %}
<div class="p-6 max-w-lg">
  <h1 class="text-2xl font-semibold mb-4">
    {% if regenerated %}Token regenerated{% else %}School created{% endif %}
  </h1>
  <p class="mb-4">
    Copy this token into the school's <code>.env</code> as
    <code>CENTRAL_INGEST_TOKEN</code>. This is the only time it will be shown.
  </p>
  <pre class="bg-black p-3 select-all">{{ school.api_token }}</pre>
  <a href="{% url 'school_list' %}" class="btn btn-primary mt-4 inline-block">Done</a>
</div>
{% endblock %}
```

- [ ] **Step 5: Wire URLs**

Modify `central_content/urls.py` — append to `urlpatterns`:

```python
from central_content.views import schools as schools_views

urlpatterns += [
    path("schools/", schools_views.school_list, name="school_list"),
    path("schools/new", schools_views.school_create, name="school_create"),
    path("schools/<int:school_id>/edit", schools_views.school_edit, name="school_edit"),
    path(
        "schools/<int:school_id>/regenerate-token",
        schools_views.school_regenerate_token,
        name="school_regenerate_token",
    ),
]
```

- [ ] **Step 6: Run tests**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_schools_views --keepdb -v 2
```
Expected: 8 tests OK.

- [ ] **Step 7: Commit**

```bash
git add central_content/views/schools.py central_content/forms.py \
    central_content/templates/central_content/schools/ \
    central_content/urls.py central_content/tests/test_schools_views.py
git commit -m "Add Schools registry CRUD + token reveal views"
```

---

## Task 16: Matching workspace view (render + catalog fetch)

**Files:**
- Create: `central_content/views/matching.py`
- Create: `central_content/templates/central_content/matching/workspace.html`
- Create: `central_content/templates/central_content/matching/_bindings_table.html`
- Create: `central_content/tests/test_matching_views.py`
- Modify: `central_content/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_matching_views.py`:

```python
import responses

from django.test import TestCase, Client

from central_content.tests.factories import (
    make_publisher, make_editor, make_reviewer, make_school,
    make_central_subject, make_binding,
)


def _login(client, staff):
    session = client.session
    session["central_staff_id"] = staff.pk
    session.save()
    return client


class MatchingWorkspaceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_publisher_sees_workspace(self):
        _login(self.client, make_publisher())
        make_school(name="HCCCI")
        resp = self.client.get("/matching/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "HCCCI")

    def test_editor_forbidden(self):
        _login(self.client, make_editor())
        make_school(name="HCCCI")
        resp = self.client.get("/matching/")
        self.assertEqual(resp.status_code, 403)

    def test_reviewer_read_only(self):
        _login(self.client, make_reviewer())
        make_school(name="HCCCI")
        resp = self.client.get("/matching/")
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'data-action="bind"')

    @responses.activate
    def test_school_catalog_fetched(self):
        _login(self.client, make_publisher())
        school = make_school(name="HCCCI", base_url="https://school.example.com")
        responses.add(
            responses.GET,
            "https://school.example.com/api/central/subjects/",
            json=[
                {"id": 17, "subject_name": "Math 101", "subject_code": "MATH101"},
            ],
            status=200,
        )
        resp = self.client.get(f"/matching/?school={school.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Math 101")

    @responses.activate
    def test_school_catalog_error_shows_message(self):
        _login(self.client, make_publisher())
        school = make_school(base_url="https://school.example.com")
        responses.add(
            responses.GET,
            "https://school.example.com/api/central/subjects/",
            status=500,
        )
        resp = self.client.get(f"/matching/?school={school.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Unable to fetch school subject list")

    def test_bindings_listed_for_school(self):
        _login(self.client, make_publisher())
        school = make_school(base_url="https://school.example.com")
        subject = make_central_subject(subject_name="Algebra 1", version=3)
        make_binding(central_subject=subject, target_school=school, pushed_version=2)
        # Stub catalog to avoid network
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://school.example.com/api/central/subjects/",
                json=[], status=200,
            )
            resp = self.client.get(f"/matching/?school={school.pk}")
        self.assertContains(resp, "Algebra 1")
        self.assertContains(resp, "Drift")
```

- [ ] **Step 2: Implement the view**

Create `central_content/views/matching.py`:

```python
# central_content/views/matching.py
import requests

from django.contrib import messages
from django.shortcuts import render

from central_content.models import (
    CentralSubject, School, SchoolSubjectBinding,
)
from central_content.permissions import central_role_required


def _fetch_school_catalog(school) -> tuple[list, str | None]:
    """Return (catalog_rows, error_message). Error is user-facing text."""
    try:
        resp = requests.get(
            school.base_url.rstrip("/") + "/api/central/subjects/",
            headers={"Authorization": f"Bearer {school.api_token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return [], f"Unable to fetch school subject list (status {resp.status_code})."
        return resp.json(), None
    except requests.RequestException as e:
        return [], f"Unable to fetch school subject list ({e})."


@central_role_required("publisher", "reviewer")
def matching_workspace(request):
    from central_content.views.schools import _get_staff
    staff = _get_staff(request)
    can_bind = staff.role == "publisher"

    schools = School.objects.filter(is_active=True).order_by("name")
    school_id = request.GET.get("school")
    selected_school = None
    if school_id:
        selected_school = schools.filter(pk=school_id).first()
    elif schools:
        selected_school = schools.first()

    catalog_rows, catalog_error = ([], None)
    bindings = []
    bound_school_subject_ids = set()
    bound_central_subject_ids = set()

    if selected_school:
        catalog_rows, catalog_error = _fetch_school_catalog(selected_school)
        bindings = list(
            SchoolSubjectBinding.objects
            .filter(target_school=selected_school)
            .select_related("central_subject")
        )
        bound_school_subject_ids = {b.school_subject_id for b in bindings}
        bound_central_subject_ids = {b.central_subject_id for b in bindings}

    central_subjects = list(
        CentralSubject.objects.filter(state="approved").order_by("subject_name")
    )

    return render(
        request,
        "central_content/matching/workspace.html",
        {
            "schools": schools,
            "selected_school": selected_school,
            "central_subjects": central_subjects,
            "catalog_rows": catalog_rows,
            "catalog_error": catalog_error,
            "bindings": bindings,
            "bound_school_subject_ids": bound_school_subject_ids,
            "bound_central_subject_ids": bound_central_subject_ids,
            "can_bind": can_bind,
        },
    )
```

- [ ] **Step 3: Create templates**

Create `central_content/templates/central_content/matching/workspace.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Matching{% endblock %}
{% block content %}
<div class="p-6">
  <div class="flex items-center justify-between mb-4">
    <h1 class="text-2xl font-semibold">Matching</h1>
    <form method="get" class="flex gap-2 items-center">
      <label>School:
        <select name="school" onchange="this.form.submit()">
          {% for s in schools %}
            <option value="{{ s.pk }}" {% if s.pk == selected_school.pk %}selected{% endif %}>{{ s.name }}</option>
          {% endfor %}
        </select>
      </label>
      <a href="{% url 'school_create' %}">Add school</a>
    </form>
  </div>

  {% if catalog_error %}
    <div class="bg-red-900 p-3 mb-4">{{ catalog_error }}</div>
  {% endif %}

  {% if selected_school %}
    <form method="post" action="{% url 'binding_create' %}" class="grid grid-cols-2 gap-4 mb-6">
      {% csrf_token %}
      <input type="hidden" name="school_id" value="{{ selected_school.pk }}">
      <div>
        <div class="label">Central subjects (approved)</div>
        {% for cs in central_subjects %}
          <label class="block p-2 {% if cs.pk in bound_central_subject_ids %}opacity-40{% endif %}">
            <input type="radio" name="central_subject_id" value="{{ cs.pk }}"
              {% if cs.pk in bound_central_subject_ids %}disabled{% endif %}>
            {{ cs.subject_name }} · v{{ cs.version }}
          </label>
        {% empty %}
          <p class="text-gray-400">No approved central subjects yet.</p>
        {% endfor %}
      </div>
      <div>
        <div class="label">{{ selected_school.name }} subjects</div>
        {% for row in catalog_rows %}
          <label class="block p-2 {% if row.id in bound_school_subject_ids %}opacity-40{% endif %}">
            <input type="radio" name="school_subject_id" value="{{ row.id }}"
              {% if row.id in bound_school_subject_ids %}disabled{% endif %}
              data-name="{{ row.subject_name }}" data-code="{{ row.subject_code }}">
            {{ row.subject_name }} — {{ row.subject_code }}
          </label>
        {% empty %}
          <p class="text-gray-400">No subjects returned.</p>
        {% endfor %}
      </div>
      {% if can_bind %}
        <div class="col-span-2">
          <button type="submit" data-action="bind" class="btn btn-primary">Bind selected</button>
        </div>
      {% endif %}
    </form>

    {% include "central_content/matching/_bindings_table.html" %}
  {% else %}
    <p class="text-gray-400">No active school selected.</p>
  {% endif %}
</div>
{% endblock %}
```

Create `central_content/templates/central_content/matching/_bindings_table.html`:

```html
<h2 class="text-xl mt-6 mb-2">Current bindings for {{ selected_school.name }}</h2>
<table class="min-w-full text-sm">
  <thead><tr class="text-left">
    <th class="p-2">Central subject</th>
    <th class="p-2">School subject</th>
    <th class="p-2">Status</th>
    <th class="p-2">Actions</th>
  </tr></thead>
  <tbody>
  {% for b in bindings %}
    <tr class="border-t border-gray-700">
      <td class="p-2">{{ b.central_subject.subject_name }} (v{{ b.central_subject.version }})</td>
      <td class="p-2">{{ b.school_subject_name }}</td>
      <td class="p-2">
        {% if b.drift_state == "never" %}
          <span class="text-gray-400">Not pushed</span>
        {% elif b.drift_state == "up_to_date" %}
          <span class="text-green-400">Up to date · v{{ b.pushed_version }}</span>
        {% else %}
          <span class="text-amber-400">Drift — pushed v{{ b.pushed_version }}, current v{{ b.central_subject.version }}</span>
        {% endif %}
      </td>
      <td class="p-2">
        {% if can_bind %}
          <form method="post" action="{% url 'binding_push' b.pk %}" style="display:inline">
            {% csrf_token %}
            <button type="submit">
              {% if b.drift_state == "never" %}Push{% elif b.drift_state == "drift" %}Push update{% else %}Re-push{% endif %}
            </button>
          </form>
          <a href="{% url 'binding_unbind_confirm' b.pk %}">Unbind</a>
        {% endif %}
      </td>
    </tr>
  {% empty %}
    <tr><td colspan="4" class="p-4 text-gray-400">No bindings yet.</td></tr>
  {% endfor %}
  </tbody>
</table>
```

- [ ] **Step 4: Wire URL**

Modify `central_content/urls.py` — append:

```python
from central_content.views import matching as matching_views

urlpatterns += [
    path("matching/", matching_views.matching_workspace, name="matching_workspace"),
]
```

- [ ] **Step 5: Run tests — partial, since bind/push/unbind routes don't exist yet**

Some tests reference routes `binding_create`, `binding_push`, `binding_unbind_confirm` that don't exist until Tasks 17-18. Add placeholder stubs in `central_content/urls.py` pointing at `matching_views.matching_workspace` temporarily, OR mark the last test with `@skip` until those tasks land.

Preferred: add the placeholder URL names pointing at a temporary `not_implemented_501` view so the template's `{% url %}` tags resolve:

```python
# central_content/views/matching.py (temporary stub at bottom)
from django.http import HttpResponse
def _not_implemented(request, *args, **kwargs):
    return HttpResponse("not implemented", status=501)
```

```python
# central_content/urls.py — add with the matching_workspace entry
urlpatterns += [
    path("matching/", matching_views.matching_workspace, name="matching_workspace"),
    path("matching/bind", matching_views._not_implemented, name="binding_create"),
    path("matching/push/<int:binding_id>", matching_views._not_implemented, name="binding_push"),
    path("matching/unbind-confirm/<int:binding_id>", matching_views._not_implemented, name="binding_unbind_confirm"),
]
```

Task 17 and 18 will replace these stubs with real views.

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_matching_views --keepdb -v 2
```
Expected: 6 tests OK.

- [ ] **Step 6: Commit**

```bash
git add central_content/views/matching.py \
    central_content/templates/central_content/matching/ \
    central_content/urls.py \
    central_content/tests/test_matching_views.py
git commit -m "Add matching workspace view with school catalog fetch"
```

---

## Task 17: Bind action + Unbind confirmation

**Files:**
- Modify: `central_content/views/matching.py`
- Create: `central_content/templates/central_content/matching/_unbind_modal.html`
- Create: `central_content/templates/central_content/matching/unbind_confirm.html`
- Modify: `central_content/urls.py`
- Create: `central_content/tests/test_bind_unbind_views.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_bind_unbind_views.py`:

```python
import responses

from django.test import TestCase, Client

from central_content.models import SchoolSubjectBinding, PushJob
from central_content.tests.factories import (
    make_publisher, make_editor, make_school, make_central_subject, make_binding,
)


def _login(client, staff):
    session = client.session
    session["central_staff_id"] = staff.pk
    session.save()


class BindActionTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_bind_creates_row(self):
        _login(self.client, make_publisher())
        school = make_school()
        subject = make_central_subject()
        resp = self.client.post(
            "/matching/bind",
            {
                "school_id": school.pk,
                "central_subject_id": subject.pk,
                "school_subject_id": 17,
                "school_subject_name": "Math 101",
                "school_subject_code": "MATH101",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            SchoolSubjectBinding.objects.filter(
                central_subject=subject, target_school=school
            ).exists()
        )

    def test_bind_editor_forbidden(self):
        _login(self.client, make_editor())
        resp = self.client.post("/matching/bind", {
            "school_id": 1, "central_subject_id": 1, "school_subject_id": 1,
            "school_subject_name": "x", "school_subject_code": "x",
        })
        self.assertEqual(resp.status_code, 403)

    def test_bind_duplicate_rejected(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        resp = self.client.post(
            "/matching/bind",
            {
                "school_id": binding.target_school.pk,
                "central_subject_id": binding.central_subject.pk,
                "school_subject_id": 99,
                "school_subject_name": "Other",
                "school_subject_code": "OTH",
            },
            follow=True,
        )
        self.assertEqual(
            SchoolSubjectBinding.objects.filter(
                central_subject=binding.central_subject,
                target_school=binding.target_school,
            ).count(),
            1,
        )


class UnbindFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_unbind_confirm_page_requires_typed_name(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        resp = self.client.get(f"/matching/unbind-confirm/{binding.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, binding.central_subject.subject_name)

    @responses.activate
    def test_unbind_success_deletes_binding(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        responses.add(
            responses.DELETE,
            f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/",
            status=204,
        )
        resp = self.client.post(
            f"/matching/unbind/{binding.pk}",
            {"confirm_name": binding.central_subject.subject_name},
            follow=True,
        )
        self.assertFalse(
            SchoolSubjectBinding.objects.filter(pk=binding.pk).exists()
        )
        self.assertTrue(
            PushJob.objects.filter(kind="delete", status="success").exists()
        )

    @responses.activate
    def test_unbind_school_500_keeps_binding(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        responses.add(
            responses.DELETE,
            f"https://school.example.com/api/central/ingest/{binding.central_subject_id}/",
            status=500,
        )
        self.client.post(
            f"/matching/unbind/{binding.pk}",
            {"confirm_name": binding.central_subject.subject_name},
        )
        self.assertTrue(
            SchoolSubjectBinding.objects.filter(pk=binding.pk).exists()
        )

    def test_unbind_wrong_name_rejected(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        resp = self.client.post(
            f"/matching/unbind/{binding.pk}",
            {"confirm_name": "WRONG"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(
            SchoolSubjectBinding.objects.filter(pk=binding.pk).exists()
        )
```

- [ ] **Step 2: Implement bind + unbind views**

Append to `central_content/views/matching.py` (and remove the temporary `_not_implemented` stubs referenced in Task 16):

```python
from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from central_content.models import (
    AuditLogEntry, CentralSubject, School, SchoolSubjectBinding,
)
from central_content.push import delete_subject_from_school


@central_role_required("publisher")
@require_http_methods(["POST"])
def binding_create(request):
    from central_content.views.schools import _get_staff
    school = get_object_or_404(School, pk=request.POST["school_id"])
    central_subject = get_object_or_404(
        CentralSubject, pk=request.POST["central_subject_id"], state="approved",
    )
    school_subject_id = int(request.POST["school_subject_id"])
    school_subject_name = request.POST.get("school_subject_name", "")
    school_subject_code = request.POST.get("school_subject_code", "")
    staff = _get_staff(request)
    with transaction.atomic():
        binding, created = SchoolSubjectBinding.objects.get_or_create(
            central_subject=central_subject,
            target_school=school,
            defaults={
                "school_subject_id": school_subject_id,
                "school_subject_name": school_subject_name,
                "school_subject_code": school_subject_code,
                "bound_by": staff,
            },
        )
        if created:
            AuditLogEntry.objects.create(
                actor=staff,
                action="bind",
                subject_type="SchoolSubjectBinding",
                subject_id=binding.pk,
                details={
                    "central_subject_id": central_subject.pk,
                    "target_school_id": school.pk,
                },
            )
    return redirect(f"/matching/?school={school.pk}")


@central_role_required("publisher")
def binding_unbind_confirm(request, binding_id):
    binding = get_object_or_404(SchoolSubjectBinding, pk=binding_id)
    return render(
        request,
        "central_content/matching/unbind_confirm.html",
        {"binding": binding},
    )


@central_role_required("publisher")
@require_http_methods(["POST"])
def binding_unbind(request, binding_id):
    from central_content.views.schools import _get_staff
    binding = get_object_or_404(SchoolSubjectBinding, pk=binding_id)
    confirm_name = request.POST.get("confirm_name", "")
    if confirm_name != binding.central_subject.subject_name:
        return HttpResponseBadRequest("Confirmation name did not match.")

    staff = _get_staff(request)
    job = delete_subject_from_school(binding, triggered_by=staff)
    if job.status == "success":
        school_id = binding.target_school_id
        binding.delete()
        return redirect(f"/matching/?school={school_id}")
    # Failed: keep binding, show error
    return render(
        request,
        "central_content/matching/unbind_confirm.html",
        {"binding": binding, "error": job.error_message or f"HTTP {job.http_status}"},
    )
```

Remove the temporary `_not_implemented` function.

- [ ] **Step 3: Update URLs**

Modify `central_content/urls.py` — replace the Task-16 stubs:

```python
urlpatterns += [
    path("matching/bind", matching_views.binding_create, name="binding_create"),
    path(
        "matching/unbind-confirm/<int:binding_id>",
        matching_views.binding_unbind_confirm,
        name="binding_unbind_confirm",
    ),
    path(
        "matching/unbind/<int:binding_id>",
        matching_views.binding_unbind,
        name="binding_unbind",
    ),
]
```

- [ ] **Step 4: Create confirmation template**

Create `central_content/templates/central_content/matching/unbind_confirm.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Unbind confirmation{% endblock %}
{% block content %}
<div class="p-6 max-w-lg">
  <h1 class="text-2xl font-semibold mb-4">Unbind subject</h1>
  <p class="mb-4">
    This will delete <strong>{{ binding.central_subject.subject_name }}</strong>
    and all its modules and activities from <strong>{{ binding.target_school.name }}</strong>.
    Teachers who have scheduled content from this subject will lose it.
  </p>
  {% if error %}
    <div class="bg-red-900 p-3 mb-4">Push failed: {{ error }}</div>
  {% endif %}
  <form method="post" action="{% url 'binding_unbind' binding.pk %}">
    {% csrf_token %}
    <p>Type <code>{{ binding.central_subject.subject_name }}</code> to confirm:</p>
    <input type="text" name="confirm_name" class="mock-input" autofocus>
    <button type="submit" class="btn btn-danger mt-2">Delete from {{ binding.target_school.name }}</button>
    <a href="{% url 'matching_workspace' %}?school={{ binding.target_school_id }}">Cancel</a>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 5: Run tests**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_bind_unbind_views --keepdb -v 2
```
Expected: 7 tests OK.

- [ ] **Step 6: Commit**

```bash
git add central_content/views/matching.py central_content/urls.py \
    central_content/templates/central_content/matching/unbind_confirm.html \
    central_content/tests/test_bind_unbind_views.py
git commit -m "Add bind action and unbind confirmation with cascade delete"
```

---

## Task 18: Push trigger view (+ retry)

**Files:**
- Modify: `central_content/views/matching.py`
- Modify: `central_content/urls.py`
- Create: `central_content/tests/test_push_views.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_push_views.py`:

```python
import responses

from django.test import TestCase, Client

from central_content.models import PushJob
from central_content.tests.factories import (
    make_publisher, make_editor, make_binding,
)


def _login(client, staff):
    session = client.session
    session["central_staff_id"] = staff.pk
    session.save()


class BindingPushViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_editor_forbidden(self):
        _login(self.client, make_editor())
        resp = self.client.post("/matching/push/1")
        self.assertEqual(resp.status_code, 403)

    @responses.activate
    def test_push_success(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            json={"received_subject_id": 1, "central_version": 1, "received_at": "x"},
            status=200,
        )
        resp = self.client.post(f"/matching/push/{binding.pk}", follow=True)
        self.assertEqual(resp.status_code, 200)
        binding.refresh_from_db()
        self.assertIsNotNone(binding.pushed_version)
        self.assertTrue(
            PushJob.objects.filter(kind="push", status="success").exists()
        )

    @responses.activate
    def test_push_failure_recorded(self):
        _login(self.client, make_publisher())
        binding = make_binding()
        binding.target_school.base_url = "https://school.example.com"
        binding.target_school.save()
        responses.add(
            responses.POST,
            "https://school.example.com/api/central/ingest/",
            status=500,
        )
        resp = self.client.post(f"/matching/push/{binding.pk}", follow=True)
        self.assertEqual(resp.status_code, 200)
        binding.refresh_from_db()
        self.assertIsNone(binding.pushed_version)
        self.assertTrue(
            PushJob.objects.filter(kind="push", status="failed").exists()
        )
```

- [ ] **Step 2: Implement the push view**

Append to `central_content/views/matching.py`:

```python
from central_content.push import push_subject_to_school


@central_role_required("publisher")
@require_http_methods(["POST"])
def binding_push(request, binding_id):
    from central_content.views.schools import _get_staff
    binding = get_object_or_404(SchoolSubjectBinding, pk=binding_id)
    job = push_subject_to_school(binding, triggered_by=_get_staff(request))
    if job.status == "success":
        messages.success(request, f"Pushed {binding.central_subject.subject_name} to {binding.target_school.name}.")
    else:
        messages.error(
            request,
            f"Push failed ({job.http_status}): {job.error_message or job.response_body[:200]}",
        )
    return redirect(f"/matching/?school={binding.target_school_id}")
```

- [ ] **Step 3: Wire URL**

Modify `central_content/urls.py`:

```python
urlpatterns += [
    path(
        "matching/push/<int:binding_id>",
        matching_views.binding_push,
        name="binding_push",
    ),
]
```

(Replace the Task-16 `_not_implemented` stub for `binding_push`.)

- [ ] **Step 4: Run tests**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_push_views --keepdb -v 2
```
Expected: 3 tests OK.

- [ ] **Step 5: Commit**

```bash
git add central_content/views/matching.py central_content/urls.py \
    central_content/tests/test_push_views.py
git commit -m "Add binding push view that triggers HTTP push to school"
```

---

## Task 19: Push history view + template

**Files:**
- Create: `central_content/views/push_history.py`
- Create: `central_content/templates/central_content/push_history/list.html`
- Create: `central_content/tests/test_push_history_views.py`
- Modify: `central_content/urls.py`

- [ ] **Step 1: Write the failing tests**

Create `central_content/tests/test_push_history_views.py`:

```python
from django.test import TestCase, Client
from django.utils import timezone

from central_content.models import PushJob
from central_content.tests.factories import (
    make_publisher, make_reviewer, make_editor, make_binding,
)


def _login(client, staff):
    session = client.session
    session["central_staff_id"] = staff.pk
    session.save()


class PushHistoryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        binding = make_binding()
        self.binding = binding
        PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind="push",
            status="success",
            subject_version=binding.central_subject.version,
            http_status=200,
            finished_at=timezone.now(),
            triggered_by=make_publisher(),
        )
        PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind="push",
            status="failed",
            subject_version=binding.central_subject.version,
            http_status=500,
            error_message="boom",
            finished_at=timezone.now(),
            triggered_by=make_publisher(),
        )

    def test_publisher_sees_all_rows(self):
        _login(self.client, make_publisher())
        resp = self.client.get("/push-history/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "boom")
        self.assertContains(resp, "200")
        self.assertContains(resp, "500")

    def test_reviewer_sees_all_rows(self):
        _login(self.client, make_reviewer())
        resp = self.client.get("/push-history/")
        self.assertEqual(resp.status_code, 200)

    def test_editor_forbidden(self):
        _login(self.client, make_editor())
        resp = self.client.get("/push-history/")
        self.assertEqual(resp.status_code, 403)

    def test_filter_by_status(self):
        _login(self.client, make_publisher())
        resp = self.client.get("/push-history/?status=failed")
        self.assertContains(resp, "boom")
        self.assertNotContains(resp, "200")  # success row's http_status not visible
```

- [ ] **Step 2: Implement the view**

Create `central_content/views/push_history.py`:

```python
# central_content/views/push_history.py
from django.shortcuts import render

from central_content.models import PushJob, School
from central_content.permissions import central_role_required


@central_role_required("publisher", "reviewer")
def push_history_list(request):
    jobs = PushJob.objects.select_related(
        "central_subject", "target_school", "triggered_by",
    ).all()
    school_id = request.GET.get("school")
    if school_id:
        jobs = jobs.filter(target_school_id=school_id)
    status = request.GET.get("status")
    if status:
        jobs = jobs.filter(status=status)
    kind = request.GET.get("kind")
    if kind:
        jobs = jobs.filter(kind=kind)
    schools = School.objects.order_by("name")
    return render(
        request,
        "central_content/push_history/list.html",
        {
            "jobs": jobs[:200],
            "schools": schools,
            "filter_school": school_id,
            "filter_status": status,
            "filter_kind": kind,
        },
    )
```

- [ ] **Step 3: Create the template**

Create `central_content/templates/central_content/push_history/list.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Push history{% endblock %}
{% block content %}
<div class="p-6">
  <h1 class="text-2xl font-semibold mb-4">Push history</h1>
  <form method="get" class="flex gap-2 mb-4">
    <select name="school">
      <option value="">All schools</option>
      {% for s in schools %}
        <option value="{{ s.pk }}" {% if filter_school == s.pk|stringformat:'s' %}selected{% endif %}>{{ s.name }}</option>
      {% endfor %}
    </select>
    <select name="status">
      <option value="">Any status</option>
      <option value="success" {% if filter_status == "success" %}selected{% endif %}>Success</option>
      <option value="failed" {% if filter_status == "failed" %}selected{% endif %}>Failed</option>
    </select>
    <select name="kind">
      <option value="">Any kind</option>
      <option value="push" {% if filter_kind == "push" %}selected{% endif %}>Push</option>
      <option value="delete" {% if filter_kind == "delete" %}selected{% endif %}>Delete</option>
    </select>
    <button type="submit">Filter</button>
  </form>
  <table class="min-w-full text-sm">
    <thead><tr class="text-left">
      <th class="p-2">When</th>
      <th class="p-2">Kind</th>
      <th class="p-2">Status</th>
      <th class="p-2">Subject</th>
      <th class="p-2">School</th>
      <th class="p-2">HTTP</th>
      <th class="p-2">Detail</th>
    </tr></thead>
    <tbody>
    {% for j in jobs %}
      <tr class="border-t border-gray-700">
        <td class="p-2">{{ j.started_at|date:"Y-m-d H:i" }}</td>
        <td class="p-2">{{ j.kind }}</td>
        <td class="p-2 {% if j.status == 'failed' %}text-red-400{% else %}text-green-400{% endif %}">{{ j.status }}</td>
        <td class="p-2">{{ j.central_subject.subject_name }} (v{{ j.subject_version }})</td>
        <td class="p-2">{{ j.target_school.name }}</td>
        <td class="p-2">{% if j.status == 'failed' %}{{ j.http_status|default_if_none:"-" }}{% endif %}</td>
        <td class="p-2">
          {% if j.error_message %}{{ j.error_message|truncatechars:120 }}{% endif %}
          {% if j.response_body and j.status == 'failed' %}<details><summary>body</summary><pre>{{ j.response_body|truncatechars:500 }}</pre></details>{% endif %}
        </td>
      </tr>
    {% empty %}
      <tr><td colspan="7" class="p-4 text-gray-400">No push jobs yet.</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

- [ ] **Step 4: Wire URL**

Modify `central_content/urls.py`:

```python
from central_content.views import push_history as push_history_views

urlpatterns += [
    path("push-history/", push_history_views.push_history_list, name="push_history_list"),
]
```

- [ ] **Step 5: Run tests**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_push_history_views --keepdb -v 2
```
Expected: 4 tests OK.

- [ ] **Step 6: Commit**

```bash
git add central_content/views/push_history.py \
    central_content/templates/central_content/push_history/ \
    central_content/urls.py \
    central_content/tests/test_push_history_views.py
git commit -m "Add push history list view with filters"
```

---

## Task 20: Navigation update + permission gating on base.html

**Files:**
- Modify: `central_content/templates/central_content/base.html`

- [ ] **Step 1: Inspect current nav**

Read `central_content/templates/central_content/base.html` to locate the existing nav block. Sub-1 added a nav with entries like "Dashboard", "Subjects", "Staff". The new nav entries are added adjacent to those.

- [ ] **Step 2: Add three nav entries with role gating**

Inside the nav block, add (adapting class names to match Sub-1's existing markup):

```html
{% if request.central_staff.role == "publisher" or request.central_staff.role == "reviewer" %}
  <a href="{% url 'school_list' %}">Schools</a>
  <a href="{% url 'matching_workspace' %}">Matching</a>
  <a href="{% url 'push_history_list' %}">Push history</a>
{% endif %}
```

If the Sub-1 templates use a different attribute (e.g., `user.central_staff` instead of `request.central_staff`), match that. Grep `central_content/templates/` for `role ==` to find the existing pattern and mirror it.

- [ ] **Step 3: Run the full central test suite**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content --keepdb -v 2
```
Expected: all central_content tests pass.

- [ ] **Step 4: Commit**

```bash
git add central_content/templates/central_content/base.html
git commit -m "Add Sub-2 navigation entries with role gating"
```

---

## Task 21: End-to-end integration smoke test

**Files:**
- Create: `central_content/tests/test_integration_push.py`

- [ ] **Step 1: Write the integration test**

The integration test exercises the full loop inside one Python process. Instead of making a real HTTP call, it stubs `requests.post` / `requests.delete` to dispatch directly to the school-side Django view handlers using Django's test `Client`. This validates that the central payload builder and the school-side ingest view agree on the wire format.

Create `central_content/tests/test_integration_push.py`:

```python
import json
from unittest.mock import patch

from django.test import TestCase, override_settings, Client as DjangoClient

from central_content.push import (
    push_subject_to_school, delete_subject_from_school,
)
from central_content.models import PushJob, SchoolSubjectBinding
from central_content.tests.factories import (
    make_binding, make_central_subject, make_central_module,
    make_central_activity, make_publisher, make_school,
    get_or_create_activity_type, get_or_create_sdg,
)


class _FakeResponse:
    def __init__(self, status_code, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}

    def json(self):
        return self._json


def _dispatch_to_school_view(method):
    """Return a fake requests.<method> that routes through Django test client.

    Needed because push_subject_to_school calls requests.post() against the
    school URL. In-process, we swap that call for an actual Django Client
    invocation of the same URL, which hits the real ingest/delete view.
    """
    django_client = DjangoClient()
    def fake(url, **kwargs):
        path = url.split("//", 1)[1].split("/", 1)[1]  # drop scheme+host
        path = "/" + path
        headers = {}
        for k, v in (kwargs.get("headers") or {}).items():
            headers["HTTP_" + k.upper().replace("-", "_")] = v
        if method == "post":
            data = kwargs.get("data") or {}
            files = kwargs.get("files") or {}
            combined = dict(data)
            for k, (_name, fh) in files.items():
                combined[k] = fh
            resp = django_client.post(path, data=combined, **headers)
        else:
            resp = django_client.delete(path, **headers)
        return _FakeResponse(
            resp.status_code,
            text=resp.content.decode() if resp.content else "",
            json_data=(resp.json() if resp["Content-Type"].startswith("application/json") else {})
            if resp.content else {},
        )
    return fake


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class IntegrationPushTests(TestCase):
    def test_full_loop_push_then_delete(self):
        from received_central_content.models import ReceivedCentralSubject
        get_or_create_sdg("Quality Education")
        get_or_create_activity_type("Quiz")

        subject = make_central_subject(
            subject_name="Algebra 1", version=1, subject_code="ALG101",
        )
        subject.target_sdgs.add(get_or_create_sdg())
        module = make_central_module(central_subject=subject, file_name="Mod 1")
        activity = make_central_activity(central_subject=subject)
        activity.related_modules.add(module)

        school = make_school(
            base_url="http://testserver",
            api_token="t" * 40,
        )
        binding = make_binding(central_subject=subject, target_school=school)

        with patch("central_content.push.requests.post", _dispatch_to_school_view("post")):
            job = push_subject_to_school(binding, triggered_by=make_publisher())

        self.assertEqual(job.status, "success", job.response_body)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        received = ReceivedCentralSubject.objects.get()
        self.assertEqual(received.central_id, subject.pk)
        self.assertEqual(received.subject_name, "Algebra 1")
        self.assertEqual(received.modules.count(), 1)
        self.assertEqual(received.activities.count(), 1)

        # Now delete via the integration path.
        with patch("central_content.push.requests.delete", _dispatch_to_school_view("delete")):
            del_job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(del_job.status, "success")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)
```

- [ ] **Step 2: Run the test**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content.tests.test_integration_push --keepdb -v 2
```
Expected: 1 test OK.

Note: the payload builder assumes file fields may be attached. If this test fails because the CentralSubject factory doesn't populate `subject_photo` / module `file`, that's expected — the builder must gracefully omit `*_part` keys when the field is empty. The payload builder implementation in Task 12 already checks `if m.file:` and `if central_subject.subject_photo:` so empty files are skipped.

- [ ] **Step 3: Run the entire Sub-2 test suite as a final gate**

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central \
  env/bin/python manage.py test central_content received_central_content --keepdb -v 2
```
Expected: ~50-60 new tests pass, Sub-1's 65 tests still pass, nothing else breaks.

- [ ] **Step 4: Commit**

```bash
git add central_content/tests/test_integration_push.py
git commit -m "Add end-to-end integration smoke test for push + delete"
```

---

## Final verification

Once all tasks complete:

- [ ] Run the full Classedge test suite to make sure Sub-2 hasn't broken anything in other apps:

```
cd ~/classedge && env/bin/python manage.py test --keepdb -v 1
```

- [ ] Run `manage.py check` under both settings modules:

```
cd ~/classedge && env/bin/python manage.py check
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central env/bin/python manage.py check
```

- [ ] Run `makemigrations --dry-run` to verify no un-generated migration drift:

```
cd ~/classedge && DJANGO_SETTINGS_MODULE=lms.settings_central env/bin/python manage.py makemigrations --dry-run
```

- [ ] Smoke test in a browser (optional but recommended):
  1. Start the central portal: `DJANGO_SETTINGS_MODULE=lms.settings_central env/bin/python manage.py runserver 8001`
  2. In a second terminal, start the school side on a different port: `env/bin/python manage.py runserver 8000`
  3. Add a `School` row pointing at `http://localhost:8000`.
  4. Copy the generated token and set `CENTRAL_INGEST_TOKEN` in `.env`; restart the school process.
  5. Create an approved central subject.
  6. Open `/matching/?school=<id>` in the central portal, bind it to a school subject, push.
  7. Verify the `ReceivedCentralSubject` row exists on the school side (shell: `env/bin/python manage.py shell -c "from received_central_content.models import ReceivedCentralSubject; print(ReceivedCentralSubject.objects.all())"`).

Once all tasks are green and the smoke test is done, merge `central-content-sub2` into `main` locally, push to `personal/main`, and update memory.
