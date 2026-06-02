# Central Catalog & Portal Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Sub-project 1 of the Classedge Plus tier — a new Django app `central_content/` served on subdomain `central.classedge.app`, with `CentralStaff` auth, three-role permissions, a `draft → in_review → approved` state machine, and a portal UI for manually authoring central subjects, modules, and activities.

**Architecture:** New Django app inside the existing Classedge repo sharing the same Postgres DB. A new settings module `lms/settings_central.py` (sibling of the gitignored `lms/settings.py`) overrides `ROOT_URLCONF`, `ALLOWED_HOSTS`, and session cookie domain so the central portal runs on its own subdomain with its own cookies. Data models mirror Classedge's content-bearing fields and add central-only metadata (state, version, audit trail). Portal UI uses Django templates + HTMX (loaded via CDN, no new pip deps) + Tailwind (loaded via CDN).

**Tech Stack:**
- Python 3.12 / Django 5.0.7 (existing)
- Postgres (existing, shared DB)
- Django built-in test runner (`python manage.py test`) — matches existing `tests.py` convention in each Classedge app
- No factory_boy — test fixtures built with plain helper functions in `tests/factories.py`
- HTMX 1.9 via CDN `<script>` tag in base template
- Tailwind via CDN during Sub-project 1 (production build pipeline deferred)

**Spec reference:** `docs/superpowers/specs/2026-04-15-classedge-central-catalog-portal-design.md`

**Preconditions (not in plan scope, must be true before Task 1):**
- Working `lms/settings.py` on the engineer's machine (gitignored, created from `.env.example`) that successfully boots the existing Classedge app (`python manage.py check` passes).
- Postgres DB running and migrated for the existing Classedge apps.
- Engineer's DNS or `/etc/hosts` has `central.classedge.app` (or chosen local equivalent like `central.localhost`) pointed at 127.0.0.1 for local testing.

---

## File Structure

**New files (created by this plan):**

```
classedge/
├── lms/
│   └── settings_central.py                       # new settings module for central subdomain
├── central_content/                              # new Django app
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py                                  # (empty stub)
│   ├── urls.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── central_staff.py                      # CentralStaff user model
│   │   ├── central_subject.py                    # CentralSubject model
│   │   ├── central_module.py                     # CentralModule model
│   │   ├── central_activity.py                   # CentralActivity model
│   │   └── audit_log.py                          # AuditLogEntry model
│   ├── migrations/
│   │   └── 0001_initial.py                       # (generated)
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── create_central_staff.py
│   ├── auth_backends.py                          # CentralStaffAuthBackend
│   ├── permissions.py                            # decorator + DRF permission class
│   ├── state_machine.py                          # transition helpers + exceptions
│   ├── forms.py                                  # Django forms for central content
│   ├── views/
│   │   ├── __init__.py
│   │   ├── auth.py                               # login/logout
│   │   ├── dashboard.py
│   │   ├── subjects.py
│   │   ├── modules.py
│   │   ├── activities.py
│   │   └── staff.py
│   ├── templates/
│   │   └── central_content/
│   │       ├── base.html
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       ├── subjects/
│   │       │   ├── list.html
│   │       │   ├── detail.html
│   │       │   ├── form.html
│   │       │   └── history.html
│   │       ├── modules/
│   │       │   ├── detail.html
│   │       │   └── form.html
│   │       ├── activities/
│   │       │   ├── detail.html
│   │       │   └── form.html
│   │       └── staff/
│   │           ├── list.html
│   │           └── form.html
│   └── tests/
│       ├── __init__.py
│       ├── factories.py
│       ├── test_models.py
│       ├── test_state_machine.py
│       ├── test_permissions.py
│       ├── test_auth.py
│       ├── test_views_subjects.py
│       ├── test_views_modules.py
│       ├── test_views_activities.py
│       ├── test_views_staff.py
│       ├── test_views_dashboard.py
│       └── test_audit_log.py
```

**Modified files:**

- `lms/settings.py` (gitignored local file) — add `'central_content'` to `INSTALLED_APPS`. This change is documented in the plan but the edit lives only on the engineer's machine; no commit includes it.

No other existing Classedge files are modified.

---

## Task 1: Scaffold the `central_content` Django app

**Files:**
- Create: `central_content/__init__.py` (empty)
- Create: `central_content/apps.py`
- Create: `central_content/admin.py` (empty stub)
- Create: `central_content/models/__init__.py` (empty for now)
- Create: `central_content/tests/__init__.py` (empty)
- Modify: `lms/settings.py` (local only — add `'central_content'` to `INSTALLED_APPS`)

- [ ] **Step 1: Create the empty app package**

```bash
mkdir -p central_content/models central_content/tests
touch central_content/__init__.py central_content/models/__init__.py central_content/tests/__init__.py
```

- [ ] **Step 2: Create `central_content/apps.py`**

```python
# central_content/apps.py
from django.apps import AppConfig


class CentralContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "central_content"
    verbose_name = "Central Content"
```

- [ ] **Step 3: Create `central_content/admin.py` as an empty stub**

```python
# central_content/admin.py
# Central models are managed through the portal UI, not Django admin.
```

- [ ] **Step 4: Register the app in `lms/settings.py`**

In `lms/settings.py`, find the `INSTALLED_APPS` list and append `'central_content'` to the end. This edit is local only (the file is gitignored).

- [ ] **Step 5: Verify Django discovers the app**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 6: Commit**

```bash
git add central_content/__init__.py central_content/apps.py central_content/admin.py central_content/models/__init__.py central_content/tests/__init__.py
git commit -m "central_content: scaffold Django app"
```

---

## Task 2: Create the `lms/settings_central.py` settings module

**Files:**
- Create: `lms/settings_central.py`

- [ ] **Step 1: Write the failing test**

Create `central_content/tests/test_settings.py`:

```python
# central_content/tests/test_settings.py
import importlib
import os

from django.test import SimpleTestCase


class CentralSettingsTests(SimpleTestCase):
    def test_central_settings_module_imports(self):
        os.environ["DJANGO_SETTINGS_MODULE"] = "lms.settings_central"
        module = importlib.import_module("lms.settings_central")
        self.assertEqual(module.ROOT_URLCONF, "central_content.urls")
        self.assertIn("central.classedge.app", module.ALLOWED_HOSTS)
        self.assertEqual(module.SESSION_COOKIE_DOMAIN, "central.classedge.app")
        self.assertEqual(module.SESSION_COOKIE_NAME, "central_sessionid")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test central_content.tests.test_settings -v 2`
Expected: `ModuleNotFoundError: No module named 'lms.settings_central'` OR `AttributeError` on missing attributes.

- [ ] **Step 3: Create `lms/settings_central.py`**

```python
# lms/settings_central.py
"""Settings module for the central content portal subdomain.

Inherits from lms.settings and overrides only what differs for the
central.classedge.app deployment. Lives alongside the gitignored
lms/settings.py — the gitignore pattern is the exact filename, so this
sibling module is safe to commit.
"""
from lms.settings import *  # noqa: F401,F403

ROOT_URLCONF = "central_content.urls"

ALLOWED_HOSTS = [
    "central.classedge.app",
    "central.localhost",
    "localhost",
    "127.0.0.1",
]

SESSION_COOKIE_DOMAIN = "central.classedge.app"
SESSION_COOKIE_NAME = "central_sessionid"
CSRF_COOKIE_NAME = "central_csrftoken"

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login"

AUTHENTICATION_BACKENDS = [
    "central_content.auth_backends.CentralStaffAuthBackend",
]

TEMPLATES[0]["DIRS"] = list(TEMPLATES[0].get("DIRS", []))  # force a mutable list
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test central_content.tests.test_settings -v 2`
Expected: `OK` (1 test).

- [ ] **Step 5: Commit**

```bash
git add lms/settings_central.py central_content/tests/test_settings.py
git commit -m "central_content: add settings_central module for subdomain deployment"
```

---

## Task 3: `CentralStaff` model

**Files:**
- Create: `central_content/models/central_staff.py`
- Modify: `central_content/models/__init__.py`
- Create: `central_content/tests/test_models.py`
- Generated: `central_content/migrations/0001_initial.py` (initial)

- [ ] **Step 1: Write the failing test**

Create `central_content/tests/test_models.py`:

```python
# central_content/tests/test_models.py
from django.db import IntegrityError
from django.test import TestCase

from central_content.models import CentralStaff


class CentralStaffModelTests(TestCase):
    def test_create_editor(self):
        staff = CentralStaff.objects.create_user(
            email="editor@example.com",
            full_name="Edna Editor",
            password="testpass123",
            role=CentralStaff.Role.EDITOR,
        )
        self.assertEqual(staff.role, "editor")
        self.assertTrue(staff.is_active)
        self.assertTrue(staff.check_password("testpass123"))

    def test_email_unique(self):
        CentralStaff.objects.create_user(
            email="dup@example.com",
            full_name="A",
            password="x",
            role=CentralStaff.Role.EDITOR,
        )
        with self.assertRaises(IntegrityError):
            CentralStaff.objects.create_user(
                email="dup@example.com",
                full_name="B",
                password="y",
                role=CentralStaff.Role.EDITOR,
            )

    def test_role_choices_enforced(self):
        staff = CentralStaff.objects.create_user(
            email="pub@example.com",
            full_name="Paula Publisher",
            password="x",
            role=CentralStaff.Role.PUBLISHER,
        )
        staff.role = "superking"
        with self.assertRaises(Exception):
            staff.full_clean()

    def test_str(self):
        staff = CentralStaff.objects.create_user(
            email="a@b.com", full_name="A B", password="x",
            role=CentralStaff.Role.REVIEWER,
        )
        self.assertIn("a@b.com", str(staff))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `ImportError: cannot import name 'CentralStaff'`.

- [ ] **Step 3: Create `central_content/models/central_staff.py`**

```python
# central_content/models/central_staff.py
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone


class CentralStaffManager(models.Manager):
    def create_user(self, email, full_name, password, role):
        if not email:
            raise ValueError("Email is required")
        staff = self.model(
            email=email.lower().strip(),
            full_name=full_name,
            role=role,
        )
        staff.set_password(password)
        staff.save()
        return staff


class CentralStaff(models.Model):
    class Role(models.TextChoices):
        EDITOR = "editor", "Editor"
        REVIEWER = "reviewer", "Reviewer"
        PUBLISHER = "publisher", "Publisher"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = CentralStaffManager()

    class Meta:
        app_label = "central_content"
        db_table = "central_content_staff"
        ordering = ["email"]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # ---- Django auth-ish shims (enough for request.user.is_authenticated) ----
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def get_session_auth_hash(self):
        from django.contrib.auth.hashers import make_password
        return make_password(self.password)[:64]
```

- [ ] **Step 4: Expose the model in `central_content/models/__init__.py`**

```python
# central_content/models/__init__.py
from .central_staff import CentralStaff

__all__ = ["CentralStaff"]
```

- [ ] **Step 5: Create the initial migration**

Run: `python manage.py makemigrations central_content`
Expected: `Migrations for 'central_content': 0001_initial.py - Create model CentralStaff`.

- [ ] **Step 6: Apply the migration**

Run: `python manage.py migrate central_content`
Expected: `Applying central_content.0001_initial... OK`.

- [ ] **Step 7: Run the model tests**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `OK` (4 tests).

- [ ] **Step 8: Commit**

```bash
git add central_content/models/central_staff.py central_content/models/__init__.py central_content/migrations/0001_initial.py central_content/tests/test_models.py
git commit -m "central_content: add CentralStaff model with Editor/Reviewer/Publisher roles"
```

---

## Task 4: `AuditLogEntry` model

**Files:**
- Create: `central_content/models/audit_log.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/test_models.py`
- Generated: new migration

- [ ] **Step 1: Extend the failing tests**

Append to `central_content/tests/test_models.py`:

```python
from django.contrib.contenttypes.models import ContentType
from central_content.models import AuditLogEntry


class AuditLogEntryModelTests(TestCase):
    def setUp(self):
        self.staff = CentralStaff.objects.create_user(
            email="actor@example.com", full_name="Actor", password="x",
            role=CentralStaff.Role.REVIEWER,
        )

    def test_create_entry(self):
        ct = ContentType.objects.get_for_model(CentralStaff)
        entry = AuditLogEntry.objects.create(
            content_type=ct,
            object_id=self.staff.id,
            from_state="draft",
            to_state="in_review",
            actor=self.staff,
            notes="submitted for review",
        )
        self.assertEqual(entry.from_state, "draft")
        self.assertEqual(entry.to_state, "in_review")
        self.assertIsNotNone(entry.created_at)

    def test_actor_protect(self):
        """Deleting a staff user with audit history should be blocked."""
        from django.db.models import ProtectedError
        ct = ContentType.objects.get_for_model(CentralStaff)
        AuditLogEntry.objects.create(
            content_type=ct, object_id=1,
            from_state="draft", to_state="in_review",
            actor=self.staff,
        )
        with self.assertRaises(ProtectedError):
            self.staff.delete()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_models.AuditLogEntryModelTests -v 2`
Expected: `ImportError: cannot import name 'AuditLogEntry'`.

- [ ] **Step 3: Create `central_content/models/audit_log.py`**

```python
# central_content/models/audit_log.py
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class AuditLogEntry(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    from_state = models.CharField(max_length=20)
    to_state = models.CharField(max_length=20)
    actor = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="audit_entries",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.from_state} -> {self.to_state} by {self.actor_id}"
```

- [ ] **Step 4: Export the model**

Update `central_content/models/__init__.py`:

```python
# central_content/models/__init__.py
from .central_staff import CentralStaff
from .audit_log import AuditLogEntry

__all__ = ["CentralStaff", "AuditLogEntry"]
```

- [ ] **Step 5: Generate and apply the migration**

Run: `python manage.py makemigrations central_content`
Expected: new migration `0002_auditlogentry.py`.

Run: `python manage.py migrate central_content`
Expected: `OK`.

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `OK` (6 tests now).

- [ ] **Step 7: Commit**

```bash
git add central_content/models/audit_log.py central_content/models/__init__.py central_content/migrations/0002_auditlogentry.py central_content/tests/test_models.py
git commit -m "central_content: add AuditLogEntry for state transition history"
```

---

## Task 5: `CentralSubject` model

**Files:**
- Create: `central_content/models/central_subject.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/test_models.py`
- Generated: new migration

- [ ] **Step 1: Extend the failing tests**

Append to `central_content/tests/test_models.py`:

```python
from central_content.models import CentralSubject


class CentralSubjectModelTests(TestCase):
    def setUp(self):
        self.creator = CentralStaff.objects.create_user(
            email="creator@example.com", full_name="Creator", password="x",
            role=CentralStaff.Role.EDITOR,
        )

    def test_create_draft(self):
        subj = CentralSubject.objects.create(
            subject_name="Grade 7 Mathematics",
            target_grade_level="Grade 7",
            target_curriculum="K-12 DepEd Philippines",
            created_by=self.creator,
        )
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.version, 1)
        self.assertIsNotNone(subj.created_at)
        self.assertIn("Grade 7", str(subj))

    def test_created_by_protected(self):
        from django.db.models import ProtectedError
        CentralSubject.objects.create(
            subject_name="X", created_by=self.creator,
        )
        with self.assertRaises(ProtectedError):
            self.creator.delete()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_models.CentralSubjectModelTests -v 2`
Expected: `ImportError: cannot import name 'CentralSubject'`.

- [ ] **Step 3: Create `central_content/models/central_subject.py`**

```python
# central_content/models/central_subject.py
import os
import uuid

from django.db import models


def _subject_photo_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("central", "subjectPhoto", new_name)


class CentralSubject(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"

    class SubjectType(models.TextChoices):
        LEC = "Lec", "Lec"
        LAB = "Lab", "Lab"

    # Content-bearing (will be copied to school tenant in Sub-project 2)
    subject_name = models.CharField(max_length=200)
    subject_descriptive_title = models.CharField(max_length=100, blank=True)
    subject_short_name = models.CharField(max_length=30, blank=True)
    subject_photo = models.ImageField(upload_to=_subject_photo_path, blank=True, null=True)
    subject_description = models.TextField(blank=True)
    subject_code = models.CharField(max_length=30, blank=True)
    subject_type = models.CharField(max_length=10, choices=SubjectType.choices, blank=True)
    unit = models.PositiveIntegerField(default=3)
    target_sdgs = models.ManyToManyField("subject.SDG", blank=True, related_name="central_subjects")

    # Central-only metadata
    target_grade_level = models.CharField(max_length=50, blank=True)
    target_curriculum = models.CharField(max_length=100, blank=True)
    version = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)

    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="subjects_created",
    )
    submitted_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="subjects_submitted",
    )
    reviewed_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="subjects_reviewed",
    )
    review_notes = models.TextField(blank=True)
    source_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_subject"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.subject_name
```

- [ ] **Step 4: Export it**

```python
# central_content/models/__init__.py
from .central_staff import CentralStaff
from .audit_log import AuditLogEntry
from .central_subject import CentralSubject

__all__ = ["CentralStaff", "AuditLogEntry", "CentralSubject"]
```

- [ ] **Step 5: Generate and apply the migration**

Run: `python manage.py makemigrations central_content`
Expected: `0003_centralsubject.py`.

Run: `python manage.py migrate central_content`
Expected: `OK`.

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `OK` (8 tests now).

- [ ] **Step 7: Commit**

```bash
git add central_content/models/central_subject.py central_content/models/__init__.py central_content/migrations/0003_centralsubject.py central_content/tests/test_models.py
git commit -m "central_content: add CentralSubject model"
```

---

## Task 6: `CentralModule` model

**Files:**
- Create: `central_content/models/central_module.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/test_models.py`
- Generated: new migration

- [ ] **Step 1: Extend the failing tests**

Append to `central_content/tests/test_models.py`:

```python
from central_content.models import CentralModule


class CentralModuleModelTests(TestCase):
    def setUp(self):
        self.creator = CentralStaff.objects.create_user(
            email="c@example.com", full_name="C", password="x",
            role=CentralStaff.Role.EDITOR,
        )
        self.subject = CentralSubject.objects.create(
            subject_name="Grade 7 Math", created_by=self.creator,
        )

    def test_create_module(self):
        m = CentralModule.objects.create(
            central_subject=self.subject,
            file_name="Lesson 1: Introduction",
            description="Intro to integers",
            order=0,
            created_by=self.creator,
        )
        self.assertEqual(m.state, "draft")
        self.assertEqual(m.central_subject, self.subject)

    def test_ordering_by_order(self):
        for i in range(3):
            CentralModule.objects.create(
                central_subject=self.subject,
                file_name=f"L{i}", order=2 - i, created_by=self.creator,
            )
        ordered = list(self.subject.modules.all().values_list("order", flat=True))
        self.assertEqual(ordered, [0, 1, 2])

    def test_cascade_on_subject_delete(self):
        CentralModule.objects.create(
            central_subject=self.subject, file_name="L1", created_by=self.creator,
        )
        self.subject.delete()
        self.assertEqual(CentralModule.objects.count(), 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_models.CentralModuleModelTests -v 2`
Expected: `ImportError`.

- [ ] **Step 3: Create `central_content/models/central_module.py`**

```python
# central_content/models/central_module.py
import os
import uuid

from django.db import models


def _module_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("central", "module", new_name)


class CentralModule(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="modules",
    )

    file_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=_module_file_path, blank=True, null=True)
    url = models.URLField(max_length=1500, blank=True)
    iframe_code = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="modules_created",
    )
    reviewed_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="modules_reviewed",
    )
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_module"
        ordering = ["order"]

    def __str__(self):
        return self.file_name
```

- [ ] **Step 4: Export it**

```python
# central_content/models/__init__.py
from .central_staff import CentralStaff
from .audit_log import AuditLogEntry
from .central_subject import CentralSubject
from .central_module import CentralModule

__all__ = ["CentralStaff", "AuditLogEntry", "CentralSubject", "CentralModule"]
```

- [ ] **Step 5: Generate and apply the migration**

Run: `python manage.py makemigrations central_content && python manage.py migrate central_content`
Expected: `0004_centralmodule.py` then `OK`.

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `OK` (11 tests).

- [ ] **Step 7: Commit**

```bash
git add central_content/models/central_module.py central_content/models/__init__.py central_content/migrations/0004_centralmodule.py central_content/tests/test_models.py
git commit -m "central_content: add CentralModule model"
```

---

## Task 7: `CentralActivity` model

**Files:**
- Create: `central_content/models/central_activity.py`
- Modify: `central_content/models/__init__.py`
- Modify: `central_content/tests/test_models.py`
- Generated: new migration

- [ ] **Step 1: Extend the failing tests**

Append to `central_content/tests/test_models.py`:

```python
from central_content.models import CentralActivity
from activity.models.activity_model import ActivityType


class CentralActivityModelTests(TestCase):
    def setUp(self):
        self.creator = CentralStaff.objects.create_user(
            email="c@example.com", full_name="C", password="x",
            role=CentralStaff.Role.EDITOR,
        )
        self.subject = CentralSubject.objects.create(
            subject_name="S", created_by=self.creator,
        )
        self.atype, _ = ActivityType.objects.get_or_create(name="Quiz")

    def test_create_activity(self):
        act = CentralActivity.objects.create(
            central_subject=self.subject,
            activity_name="Unit 1 Quiz",
            activity_type=self.atype,
            max_score=50,
            created_by=self.creator,
        )
        self.assertEqual(act.state, "draft")
        self.assertEqual(act.passing_score_type, "percentage")
        self.assertEqual(act.retake_method, "highest")

    def test_related_modules_m2m(self):
        m = CentralModule.objects.create(
            central_subject=self.subject, file_name="L1", created_by=self.creator,
        )
        act = CentralActivity.objects.create(
            central_subject=self.subject, activity_name="Q",
            activity_type=self.atype, created_by=self.creator,
        )
        act.related_modules.add(m)
        self.assertIn(m, act.related_modules.all())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_models.CentralActivityModelTests -v 2`
Expected: `ImportError`.

- [ ] **Step 3: Create `central_content/models/central_activity.py`**

```python
# central_content/models/central_activity.py
from django.db import models


class CentralActivity(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"

    class PassingScoreType(models.TextChoices):
        NUMBER = "number", "Number"
        PERCENTAGE = "percentage", "Percentage"

    class RetakeMethod(models.TextChoices):
        HIGHEST = "highest", "Highest Score"
        LATEST = "latest", "Latest Take"
        AVERAGE = "average", "Average"
        FIRST = "first", "First Attempt"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="activities",
    )
    related_modules = models.ManyToManyField(
        "central_content.CentralModule",
        blank=True,
        related_name="related_activities",
    )

    activity_name = models.CharField(max_length=100)
    activity_instruction = models.TextField(blank=True)
    activity_type = models.ForeignKey(
        "activity.ActivityType", on_delete=models.PROTECT,
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

    state = models.CharField(max_length=20, choices=State.choices, default=State.DRAFT)
    created_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="activities_created",
    )
    reviewed_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="activities_reviewed",
    )
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_activity"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.activity_name
```

- [ ] **Step 4: Export it**

```python
# central_content/models/__init__.py
from .central_staff import CentralStaff
from .audit_log import AuditLogEntry
from .central_subject import CentralSubject
from .central_module import CentralModule
from .central_activity import CentralActivity

__all__ = [
    "CentralStaff", "AuditLogEntry", "CentralSubject",
    "CentralModule", "CentralActivity",
]
```

- [ ] **Step 5: Generate and apply the migration**

Run: `python manage.py makemigrations central_content && python manage.py migrate central_content`
Expected: `0005_centralactivity.py` then `OK`.

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `OK` (13 tests).

- [ ] **Step 7: Commit**

```bash
git add central_content/models/central_activity.py central_content/models/__init__.py central_content/migrations/0005_centralactivity.py central_content/tests/test_models.py
git commit -m "central_content: add CentralActivity model"
```

---

## Task 8: Test factories helper

**Files:**
- Create: `central_content/tests/factories.py`

- [ ] **Step 1: Create the factories module**

```python
# central_content/tests/factories.py
"""Plain helper functions for building test fixtures.

No external factory library — just thin constructors with sane defaults.
"""
from central_content.models import (
    CentralStaff,
    CentralSubject,
    CentralModule,
    CentralActivity,
)


_COUNTER = {"n": 0}


def _next():
    _COUNTER["n"] += 1
    return _COUNTER["n"]


def make_staff(role=CentralStaff.Role.EDITOR, email=None, password="testpass"):
    n = _next()
    email = email or f"user{n}@example.com"
    return CentralStaff.objects.create_user(
        email=email,
        full_name=f"User {n}",
        password=password,
        role=role,
    )


def make_editor(**kw):
    return make_staff(role=CentralStaff.Role.EDITOR, **kw)


def make_reviewer(**kw):
    return make_staff(role=CentralStaff.Role.REVIEWER, **kw)


def make_publisher(**kw):
    return make_staff(role=CentralStaff.Role.PUBLISHER, **kw)


def make_subject(created_by=None, state=CentralSubject.State.DRAFT, **kw):
    created_by = created_by or make_editor()
    defaults = {
        "subject_name": f"Subject {_next()}",
        "target_grade_level": "Grade 7",
        "target_curriculum": "K-12 DepEd",
        "created_by": created_by,
        "state": state,
    }
    defaults.update(kw)
    return CentralSubject.objects.create(**defaults)


def make_module(central_subject=None, created_by=None,
                state=CentralModule.State.DRAFT, **kw):
    created_by = created_by or make_editor()
    central_subject = central_subject or make_subject(created_by=created_by)
    defaults = {
        "central_subject": central_subject,
        "file_name": f"Lesson {_next()}",
        "created_by": created_by,
        "state": state,
    }
    defaults.update(kw)
    return CentralModule.objects.create(**defaults)


def make_activity(central_subject=None, created_by=None,
                  state=CentralActivity.State.DRAFT, **kw):
    from activity.models.activity_model import ActivityType
    atype, _ = ActivityType.objects.get_or_create(name="Quiz")
    created_by = created_by or make_editor()
    central_subject = central_subject or make_subject(created_by=created_by)
    defaults = {
        "central_subject": central_subject,
        "activity_name": f"Activity {_next()}",
        "activity_type": atype,
        "created_by": created_by,
        "state": state,
    }
    defaults.update(kw)
    return CentralActivity.objects.create(**defaults)
```

- [ ] **Step 2: Run the existing model tests to confirm nothing broke**

Run: `python manage.py test central_content.tests.test_models -v 2`
Expected: `OK` (13 tests).

- [ ] **Step 3: Commit**

```bash
git add central_content/tests/factories.py
git commit -m "central_content: add tests/factories helpers"
```

---

## Task 9: State machine transition helpers

**Files:**
- Create: `central_content/state_machine.py`
- Create: `central_content/tests/test_state_machine.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_state_machine.py
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from central_content.models import (
    AuditLogEntry,
    CentralModule,
    CentralSubject,
)
from central_content.state_machine import (
    IllegalTransition,
    UnresolvedChildren,
    submit_for_review,
    approve,
    request_changes,
    reopen,
)
from central_content.tests.factories import (
    make_editor,
    make_reviewer,
    make_publisher,
    make_subject,
    make_module,
)


class SubjectStateMachineTests(TestCase):
    def test_submit_sets_in_review_and_logs(self):
        editor = make_editor()
        subj = make_subject(created_by=editor)
        submit_for_review(subj, actor=editor)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "in_review")
        self.assertEqual(subj.submitted_by, editor)
        ct = ContentType.objects.get_for_model(CentralSubject)
        entry = AuditLogEntry.objects.get(content_type=ct, object_id=subj.id)
        self.assertEqual((entry.from_state, entry.to_state), ("draft", "in_review"))

    def test_cannot_submit_non_draft(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        with self.assertRaises(IllegalTransition):
            submit_for_review(subj, actor=reviewer)

    def test_approve_requires_all_children_approved(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        make_module(central_subject=subj, state=CentralModule.State.DRAFT)
        with self.assertRaises(UnresolvedChildren):
            approve(subj, actor=reviewer)

    def test_approve_succeeds_when_children_approved(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        make_module(central_subject=subj, state=CentralModule.State.APPROVED)
        approve(subj, actor=reviewer)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "approved")
        self.assertEqual(subj.reviewed_by, reviewer)

    def test_request_changes_returns_to_draft_with_notes(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        request_changes(subj, actor=reviewer, notes="fix typos")
        subj.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.review_notes, "fix typos")

    def test_reopen_bumps_version_and_reverts_children(self):
        publisher = make_publisher()
        subj = make_subject(state=CentralSubject.State.APPROVED)
        child = make_module(central_subject=subj, state=CentralModule.State.APPROVED)
        original_version = subj.version
        reopen(subj, actor=publisher)
        subj.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.version, original_version + 1)
        self.assertEqual(child.state, "draft")

    def test_illegal_reopen_by_editor(self):
        editor = make_editor()
        subj = make_subject(state=CentralSubject.State.APPROVED)
        with self.assertRaises(IllegalTransition):
            reopen(subj, actor=editor)


class ModuleStateMachineTests(TestCase):
    def test_module_submit_approve_cycle(self):
        editor = make_editor()
        reviewer = make_reviewer()
        m = make_module(created_by=editor)
        submit_for_review(m, actor=editor)
        m.refresh_from_db()
        self.assertEqual(m.state, "in_review")
        approve(m, actor=reviewer)
        m.refresh_from_db()
        self.assertEqual(m.state, "approved")
        self.assertEqual(m.reviewed_by, reviewer)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_state_machine -v 2`
Expected: `ImportError: No module named 'central_content.state_machine'`.

- [ ] **Step 3: Create `central_content/state_machine.py`**

```python
# central_content/state_machine.py
"""State machine transitions for central content records.

Each transition is a function taking the record and the acting CentralStaff.
Success mutates the record (in DB) and writes one AuditLogEntry.
Failures raise IllegalTransition or UnresolvedChildren — no partial writes.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from central_content.models import (
    AuditLogEntry,
    CentralActivity,
    CentralModule,
    CentralStaff,
    CentralSubject,
)


class IllegalTransition(Exception):
    """Raised when a transition is not allowed for the current state or role."""


class UnresolvedChildren(Exception):
    """Raised when approving a subject that still has non-approved children."""

    def __init__(self, subject, blocking):
        self.subject = subject
        self.blocking = list(blocking)
        names = ", ".join(str(b) for b in self.blocking[:5])
        super().__init__(
            f"Cannot approve {subject}: {len(self.blocking)} child(ren) "
            f"still draft or in_review ({names}...)"
        )


_DRAFT = "draft"
_IN_REVIEW = "in_review"
_APPROVED = "approved"

_SUBMIT_ROLES = {CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER}
_REVIEW_ROLES = {CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER}
_REOPEN_ROLES = {CentralStaff.Role.PUBLISHER}


def _log(record, actor, from_state, to_state, notes=""):
    AuditLogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(type(record)),
        object_id=record.id,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        notes=notes,
    )


def _require_role(actor, allowed, action):
    if actor.role not in allowed:
        raise IllegalTransition(
            f"Role '{actor.role}' cannot perform action '{action}'"
        )


def _require_state(record, allowed, action):
    if record.state not in allowed:
        raise IllegalTransition(
            f"Cannot {action} from state '{record.state}'"
        )


@transaction.atomic
def submit_for_review(record, actor):
    _require_role(actor, _SUBMIT_ROLES, "submit")
    _require_state(record, {_DRAFT}, "submit")
    record.state = _IN_REVIEW
    if isinstance(record, CentralSubject):
        record.submitted_by = actor
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _DRAFT, _IN_REVIEW)


@transaction.atomic
def approve(record, actor):
    _require_role(actor, _REVIEW_ROLES, "approve")
    _require_state(record, {_IN_REVIEW}, "approve")

    if isinstance(record, CentralSubject):
        blocking = list(record.modules.exclude(state=_APPROVED)) + \
                   list(record.activities.exclude(state=_APPROVED))
        if blocking:
            raise UnresolvedChildren(record, blocking)

    record.state = _APPROVED
    record.reviewed_by = actor
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _IN_REVIEW, _APPROVED)


@transaction.atomic
def request_changes(record, actor, notes=""):
    _require_role(actor, _REVIEW_ROLES, "request_changes")
    _require_state(record, {_IN_REVIEW}, "request_changes")
    record.state = _DRAFT
    record.reviewed_by = actor
    record.review_notes = notes
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _IN_REVIEW, _DRAFT, notes=notes)


@transaction.atomic
def reopen(record, actor):
    _require_role(actor, _REOPEN_ROLES, "reopen")
    _require_state(record, {_APPROVED}, "reopen")
    record.state = _DRAFT
    if isinstance(record, CentralSubject):
        record.version += 1
        record.modules.update(state=_DRAFT)
        record.activities.update(state=_DRAFT)
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _APPROVED, _DRAFT)


def _save_fields(record):
    """Return the minimal update_fields for a transition save."""
    fields = ["state", "updated_at"]
    if isinstance(record, CentralSubject):
        fields += ["submitted_by", "reviewed_by", "review_notes", "version"]
    elif isinstance(record, (CentralModule, CentralActivity)):
        fields += ["reviewed_by", "review_notes"]
    return fields
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python manage.py test central_content.tests.test_state_machine -v 2`
Expected: `OK` (8 tests).

- [ ] **Step 5: Commit**

```bash
git add central_content/state_machine.py central_content/tests/test_state_machine.py
git commit -m "central_content: add state machine with audit log writes"
```

---

## Task 10: Permission layer

**Files:**
- Create: `central_content/permissions.py`
- Create: `central_content/tests/test_permissions.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_permissions.py
from django.http import HttpRequest, HttpResponse
from django.test import TestCase

from central_content.permissions import central_role_required, IsCentralStaff
from central_content.models import CentralStaff
from central_content.tests.factories import (
    make_editor, make_reviewer, make_publisher,
)


class RoleDecoratorTests(TestCase):
    def _request_for(self, user):
        req = HttpRequest()
        req.user = user
        return req

    def test_allows_matching_role(self):
        @central_role_required(CentralStaff.Role.PUBLISHER)
        def view(request):
            return HttpResponse("ok")

        resp = view(self._request_for(make_publisher()))
        self.assertEqual(resp.status_code, 200)

    def test_rejects_other_role(self):
        @central_role_required(CentralStaff.Role.PUBLISHER)
        def view(request):
            return HttpResponse("ok")

        resp = view(self._request_for(make_editor()))
        self.assertEqual(resp.status_code, 403)

    def test_rejects_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        @central_role_required(CentralStaff.Role.EDITOR)
        def view(request):
            return HttpResponse("ok")

        req = HttpRequest()
        req.user = AnonymousUser()
        resp = view(req)
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_multiple_roles_allowed(self):
        @central_role_required(
            CentralStaff.Role.REVIEWER,
            CentralStaff.Role.PUBLISHER,
        )
        def view(request):
            return HttpResponse("ok")

        self.assertEqual(view(self._request_for(make_reviewer())).status_code, 200)
        self.assertEqual(view(self._request_for(make_publisher())).status_code, 200)
        self.assertEqual(view(self._request_for(make_editor())).status_code, 403)


class IsCentralStaffTests(TestCase):
    def test_rejects_non_central_staff(self):
        from django.contrib.auth.models import AnonymousUser
        req = HttpRequest()
        req.user = AnonymousUser()
        perm = IsCentralStaff()
        self.assertFalse(perm.has_permission(req, None))

    def test_accepts_central_staff(self):
        req = HttpRequest()
        req.user = make_editor()
        perm = IsCentralStaff()
        self.assertTrue(perm.has_permission(req, None))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_permissions -v 2`
Expected: `ImportError`.

- [ ] **Step 3: Create `central_content/permissions.py`**

```python
# central_content/permissions.py
from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect

from central_content.models import CentralStaff


def central_role_required(*allowed_roles):
    """Decorator restricting a view to CentralStaff users with one of the
    given roles. Anonymous users are redirected to /login. CentralStaff
    with a non-matching role get 403.
    """
    allowed = set(allowed_roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if not user or not isinstance(user, CentralStaff):
                return redirect("/login")
            if user.role not in allowed:
                return HttpResponseForbidden("Forbidden")
            return view_func(request, *args, **kwargs)
        return _wrapped

    return decorator


class IsCentralStaff:
    """DRF permission class. Allows any request whose user is a CentralStaff
    instance. Role-specific gating is layered on via central_role_required
    on top-level views, or via DRF per-action logic.
    """

    def has_permission(self, request, view):
        return isinstance(getattr(request, "user", None), CentralStaff)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test central_content.tests.test_permissions -v 2`
Expected: `OK` (6 tests).

- [ ] **Step 5: Commit**

```bash
git add central_content/permissions.py central_content/tests/test_permissions.py
git commit -m "central_content: add role decorator and DRF permission class"
```

---

## Task 11: Auth backend + login/logout views + URL skeleton

**Files:**
- Create: `central_content/auth_backends.py`
- Create: `central_content/urls.py`
- Create: `central_content/views/__init__.py`
- Create: `central_content/views/auth.py`
- Create: `central_content/templates/central_content/base.html`
- Create: `central_content/templates/central_content/login.html`
- Create: `central_content/tests/test_auth.py`
- Create: `central_content/management/__init__.py`
- Create: `central_content/management/commands/__init__.py`
- Create: `central_content/management/commands/create_central_staff.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_auth.py
from django.core.management import call_command
from django.test import TestCase, override_settings

from central_content.models import CentralStaff


@override_settings(ROOT_URLCONF="central_content.urls")
class CentralAuthTests(TestCase):
    def test_login_page_renders(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Email")

    def test_login_success(self):
        CentralStaff.objects.create_user(
            email="editor@example.com", full_name="Ed", password="pw12345",
            role=CentralStaff.Role.EDITOR,
        )
        resp = self.client.post(
            "/login",
            {"email": "editor@example.com", "password": "pw12345"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")

    def test_login_failure(self):
        CentralStaff.objects.create_user(
            email="e@example.com", full_name="E", password="correct",
            role=CentralStaff.Role.EDITOR,
        )
        resp = self.client.post(
            "/login", {"email": "e@example.com", "password": "wrong"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Invalid")

    def test_logout_clears_session(self):
        CentralStaff.objects.create_user(
            email="u@example.com", full_name="U", password="pw",
            role=CentralStaff.Role.EDITOR,
        )
        self.client.post("/login", {"email": "u@example.com", "password": "pw"})
        resp = self.client.post("/logout")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/login")


class CreateCentralStaffCommandTests(TestCase):
    def test_command_creates_user(self):
        call_command(
            "create_central_staff",
            email="boot@example.com",
            full_name="Boot",
            role="publisher",
            password="bootpw123",
        )
        staff = CentralStaff.objects.get(email="boot@example.com")
        self.assertEqual(staff.role, "publisher")
        self.assertTrue(staff.check_password("bootpw123"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_auth -v 2`
Expected: import errors or 404s (no urls/views yet).

- [ ] **Step 3: Create `central_content/auth_backends.py`**

```python
# central_content/auth_backends.py
from central_content.models import CentralStaff


class CentralStaffAuthBackend:
    """Authenticates against CentralStaff. Wired in lms.settings_central."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        try:
            staff = CentralStaff.objects.get(email=email.lower().strip())
        except CentralStaff.DoesNotExist:
            return None
        if not staff.is_active:
            return None
        if staff.check_password(password):
            return staff
        return None

    def get_user(self, user_id):
        try:
            return CentralStaff.objects.get(pk=user_id, is_active=True)
        except CentralStaff.DoesNotExist:
            return None
```

- [ ] **Step 4: Create `central_content/views/__init__.py`** (empty)

```python
# central_content/views/__init__.py
```

- [ ] **Step 5: Create `central_content/views/auth.py`**

```python
# central_content/views/auth.py
from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from django.shortcuts import render

from central_content.auth_backends import CentralStaffAuthBackend


def login_view(request):
    error = None
    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        backend = CentralStaffAuthBackend()
        user = backend.authenticate(request, email=email, password=password)
        if user:
            user.backend = "central_content.auth_backends.CentralStaffAuthBackend"
            login(request, user)
            return HttpResponseRedirect("/")
        error = "Invalid email or password"
    return render(request, "central_content/login.html", {"error": error})


def logout_view(request):
    logout(request)
    return HttpResponseRedirect("/login")
```

- [ ] **Step 6: Create `central_content/urls.py`**

```python
# central_content/urls.py
from django.urls import path

from central_content.views import auth as auth_views

urlpatterns = [
    path("login", auth_views.login_view, name="central_login"),
    path("logout", auth_views.logout_view, name="central_logout"),
    # additional routes added by subsequent tasks
]
```

- [ ] **Step 7: Create `central_content/templates/central_content/base.html`**

```html
<!-- central_content/templates/central_content/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Central Content{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-900">
    {% if request.user.is_authenticated %}
    <nav class="bg-white border-b border-gray-200 px-6 py-3 flex gap-4">
        <a href="/" class="font-semibold">Central</a>
        <a href="/subjects/">Subjects</a>
        {% if request.user.role == "publisher" %}<a href="/staff/">Staff</a>{% endif %}
        <form action="/logout" method="post" class="ml-auto">{% csrf_token %}
            <button type="submit">Logout ({{ request.user.email }})</button>
        </form>
    </nav>
    {% endif %}
    <main class="max-w-6xl mx-auto p-6">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 8: Create `central_content/templates/central_content/login.html`**

```html
<!-- central_content/templates/central_content/login.html -->
{% extends "central_content/base.html" %}
{% block title %}Login - Central Content{% endblock %}
{% block content %}
<div class="max-w-sm mx-auto bg-white p-6 rounded shadow">
    <h1 class="text-xl font-semibold mb-4">Central Content Portal</h1>
    {% if error %}<p class="text-red-600 mb-3">{{ error }}</p>{% endif %}
    <form method="post">
        {% csrf_token %}
        <label class="block mb-3">
            <span class="block text-sm">Email</span>
            <input type="email" name="email" class="w-full border rounded p-2" required>
        </label>
        <label class="block mb-3">
            <span class="block text-sm">Password</span>
            <input type="password" name="password" class="w-full border rounded p-2" required>
        </label>
        <button type="submit" class="w-full bg-blue-600 text-white rounded py-2">Sign in</button>
    </form>
</div>
{% endblock %}
```

- [ ] **Step 9: Create the management command scaffolding**

```bash
mkdir -p central_content/management/commands
touch central_content/management/__init__.py central_content/management/commands/__init__.py
```

- [ ] **Step 10: Create `central_content/management/commands/create_central_staff.py`**

```python
# central_content/management/commands/create_central_staff.py
from django.core.management.base import BaseCommand, CommandError

from central_content.models import CentralStaff


class Command(BaseCommand):
    help = "Create a CentralStaff user (bootstrap the first Publisher)."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--full-name", dest="full_name", required=True)
        parser.add_argument(
            "--role", required=True,
            choices=[c.value for c in CentralStaff.Role],
        )
        parser.add_argument("--password", required=True)

    def handle(self, *, email, full_name, role, password, **kwargs):
        if CentralStaff.objects.filter(email=email.lower()).exists():
            raise CommandError(f"User with email {email} already exists")
        staff = CentralStaff.objects.create_user(
            email=email, full_name=full_name, password=password, role=role,
        )
        self.stdout.write(self.style.SUCCESS(f"Created {staff}"))
```

- [ ] **Step 11: Run the tests**

Run: `python manage.py test central_content.tests.test_auth -v 2`
Expected: `OK` (5 tests).

- [ ] **Step 12: Commit**

```bash
git add central_content/auth_backends.py central_content/urls.py central_content/views/__init__.py central_content/views/auth.py central_content/templates/central_content/base.html central_content/templates/central_content/login.html central_content/management/__init__.py central_content/management/commands/__init__.py central_content/management/commands/create_central_staff.py central_content/tests/test_auth.py
git commit -m "central_content: auth backend, login/logout, base template, bootstrap command"
```

---

## Task 12: Subject list + detail views (read-only)

**Files:**
- Create: `central_content/views/subjects.py`
- Modify: `central_content/urls.py`
- Create: `central_content/templates/central_content/subjects/list.html`
- Create: `central_content/templates/central_content/subjects/detail.html`
- Create: `central_content/tests/test_views_subjects.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_views_subjects.py
from django.test import TestCase, override_settings

from central_content.models import CentralSubject
from central_content.tests.factories import (
    make_editor, make_reviewer, make_publisher,
    make_subject, make_module, make_activity,
)


@override_settings(ROOT_URLCONF="central_content.urls")
class SubjectListViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.client.post("/login", {"email": "ed@example.com", "password": "pw"})

    def test_list_requires_login(self):
        self.client.post("/logout")
        resp = self.client.get("/subjects/")
        self.assertEqual(resp.status_code, 302)

    def test_list_shows_subjects(self):
        make_subject(subject_name="Grade 7 Math", created_by=self.editor)
        make_subject(subject_name="Grade 8 Science", created_by=self.editor)
        resp = self.client.get("/subjects/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Grade 7 Math")
        self.assertContains(resp, "Grade 8 Science")

    def test_list_filter_by_state(self):
        make_subject(subject_name="A", created_by=self.editor,
                     state=CentralSubject.State.DRAFT)
        make_subject(subject_name="B", created_by=self.editor,
                     state=CentralSubject.State.APPROVED)
        resp = self.client.get("/subjects/?state=approved")
        self.assertContains(resp, "B")
        self.assertNotContains(resp, ">A<")


@override_settings(ROOT_URLCONF="central_content.urls")
class SubjectDetailViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.client.post("/login", {"email": "ed@example.com", "password": "pw"})

    def test_detail_shows_children(self):
        subj = make_subject(subject_name="X", created_by=self.editor)
        make_module(central_subject=subj, created_by=self.editor,
                    file_name="Lesson One")
        make_activity(central_subject=subj, created_by=self.editor,
                      activity_name="Quiz One")
        resp = self.client.get(f"/subjects/{subj.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "X")
        self.assertContains(resp, "Lesson One")
        self.assertContains(resp, "Quiz One")

    def test_detail_404(self):
        resp = self.client.get("/subjects/99999/")
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_subjects -v 2`
Expected: 404s / `NoReverseMatch`.

- [ ] **Step 3: Create `central_content/views/subjects.py`**

```python
# central_content/views/subjects.py
from django.shortcuts import get_object_or_404, render

from central_content.models import CentralSubject
from central_content.permissions import central_role_required
from central_content.models import CentralStaff


_ALL_ROLES = (
    CentralStaff.Role.EDITOR,
    CentralStaff.Role.REVIEWER,
    CentralStaff.Role.PUBLISHER,
)


@central_role_required(*_ALL_ROLES)
def subject_list(request):
    qs = CentralSubject.objects.all().select_related("created_by")
    state = request.GET.get("state")
    if state in dict(CentralSubject.State.choices):
        qs = qs.filter(state=state)
    q = request.GET.get("q")
    if q:
        qs = qs.filter(subject_name__icontains=q)
    return render(
        request,
        "central_content/subjects/list.html",
        {"subjects": qs, "current_state": state, "q": q or ""},
    )


@central_role_required(*_ALL_ROLES)
def subject_detail(request, subject_id: int):
    subj = get_object_or_404(
        CentralSubject.objects.prefetch_related("modules", "activities"),
        pk=subject_id,
    )
    return render(
        request,
        "central_content/subjects/detail.html",
        {
            "subject": subj,
            "modules": subj.modules.all(),
            "activities": subj.activities.all(),
        },
    )
```

- [ ] **Step 4: Wire URLs**

Update `central_content/urls.py`:

```python
# central_content/urls.py
from django.urls import path

from central_content.views import auth as auth_views
from central_content.views import subjects as subject_views

urlpatterns = [
    path("login", auth_views.login_view, name="central_login"),
    path("logout", auth_views.logout_view, name="central_logout"),

    path("subjects/", subject_views.subject_list, name="subject_list"),
    path("subjects/<int:subject_id>/", subject_views.subject_detail, name="subject_detail"),
]
```

- [ ] **Step 5: Create `central_content/templates/central_content/subjects/list.html`**

```html
<!-- central_content/templates/central_content/subjects/list.html -->
{% extends "central_content/base.html" %}
{% block title %}Subjects{% endblock %}
{% block content %}
<div class="flex justify-between items-center mb-4">
    <h1 class="text-2xl font-semibold">Subjects</h1>
    <a href="/subjects/new" class="bg-blue-600 text-white px-4 py-2 rounded">New subject</a>
</div>
<form method="get" class="mb-4 flex gap-2">
    <input type="text" name="q" value="{{ q }}" placeholder="Search name..." class="border rounded p-2 flex-1">
    <select name="state" class="border rounded p-2">
        <option value="">All states</option>
        <option value="draft" {% if current_state == "draft" %}selected{% endif %}>Draft</option>
        <option value="in_review" {% if current_state == "in_review" %}selected{% endif %}>In Review</option>
        <option value="approved" {% if current_state == "approved" %}selected{% endif %}>Approved</option>
    </select>
    <button type="submit" class="border rounded px-4">Filter</button>
</form>
<table class="w-full bg-white rounded shadow">
    <thead class="text-left bg-gray-100">
        <tr><th class="p-3">Name</th><th>Grade</th><th>State</th><th>Updated</th></tr>
    </thead>
    <tbody>
        {% for s in subjects %}
        <tr class="border-t">
            <td class="p-3"><a href="/subjects/{{ s.id }}/" class="text-blue-700">{{ s.subject_name }}</a></td>
            <td>{{ s.target_grade_level }}</td>
            <td><span class="px-2 py-1 rounded bg-gray-200 text-xs">{{ s.state }}</span></td>
            <td>{{ s.updated_at|date:"Y-m-d H:i" }}</td>
        </tr>
        {% empty %}
        <tr><td colspan="4" class="p-6 text-center text-gray-500">No subjects yet.</td></tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

- [ ] **Step 6: Create `central_content/templates/central_content/subjects/detail.html`**

```html
<!-- central_content/templates/central_content/subjects/detail.html -->
{% extends "central_content/base.html" %}
{% block title %}{{ subject.subject_name }}{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-4">
    <div>
        <h1 class="text-2xl font-semibold">{{ subject.subject_name }}</h1>
        <p class="text-gray-600">{{ subject.target_grade_level }} · {{ subject.target_curriculum }}</p>
    </div>
    <span class="px-3 py-1 rounded bg-gray-200 text-sm">{{ subject.state }}</span>
</div>

<div class="mb-6 bg-white p-4 rounded shadow">
    <h2 class="font-semibold mb-2">Overview</h2>
    <p>{{ subject.subject_description|default:"No description." }}</p>
    <p class="text-sm text-gray-500 mt-2">Version {{ subject.version }} · Created by {{ subject.created_by.full_name }}</p>
    {% if subject.state == "draft" %}
    <a href="/subjects/{{ subject.id }}/edit" class="inline-block mt-3 text-blue-700">Edit</a>
    {% endif %}
</div>

<div class="mb-6 bg-white p-4 rounded shadow">
    <div class="flex justify-between items-center mb-2">
        <h2 class="font-semibold">Modules</h2>
        <a href="/subjects/{{ subject.id }}/modules/new" class="text-blue-700">+ New module</a>
    </div>
    <ul>
    {% for m in modules %}
        <li class="border-t py-2"><a href="/subjects/{{ subject.id }}/modules/{{ m.id }}/" class="text-blue-700">{{ m.file_name }}</a> <span class="text-xs text-gray-500">[{{ m.state }}]</span></li>
    {% empty %}
        <li class="text-gray-500 py-2">No modules yet.</li>
    {% endfor %}
    </ul>
</div>

<div class="bg-white p-4 rounded shadow">
    <div class="flex justify-between items-center mb-2">
        <h2 class="font-semibold">Activities</h2>
        <a href="/subjects/{{ subject.id }}/activities/new" class="text-blue-700">+ New activity</a>
    </div>
    <ul>
    {% for a in activities %}
        <li class="border-t py-2"><a href="/subjects/{{ subject.id }}/activities/{{ a.id }}/" class="text-blue-700">{{ a.activity_name }}</a> <span class="text-xs text-gray-500">[{{ a.state }}]</span></li>
    {% empty %}
        <li class="text-gray-500 py-2">No activities yet.</li>
    {% endfor %}
    </ul>
</div>
{% endblock %}
```

- [ ] **Step 7: Run the tests**

Run: `python manage.py test central_content.tests.test_views_subjects -v 2`
Expected: `OK` (5 tests).

- [ ] **Step 8: Commit**

```bash
git add central_content/views/subjects.py central_content/urls.py central_content/templates/central_content/subjects/ central_content/tests/test_views_subjects.py
git commit -m "central_content: subject list and detail views"
```

---

## Task 13: Subject create/edit views + forms

**Files:**
- Create: `central_content/forms.py`
- Modify: `central_content/views/subjects.py`
- Modify: `central_content/urls.py`
- Create: `central_content/templates/central_content/subjects/form.html`
- Modify: `central_content/tests/test_views_subjects.py`

- [ ] **Step 1: Extend the failing tests**

Append to `central_content/tests/test_views_subjects.py`:

```python
@override_settings(ROOT_URLCONF="central_content.urls")
class SubjectCreateEditTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.client.post("/login", {"email": "ed@example.com", "password": "pw"})

    def test_create_form_renders(self):
        resp = self.client.get("/subjects/new")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Subject name")

    def test_create_submits(self):
        resp = self.client.post("/subjects/new", {
            "subject_name": "New Subject",
            "target_grade_level": "Grade 7",
            "target_curriculum": "K-12",
            "subject_description": "desc",
            "unit": "3",
        })
        self.assertEqual(resp.status_code, 302)
        s = CentralSubject.objects.get(subject_name="New Subject")
        self.assertEqual(s.state, "draft")
        self.assertEqual(s.created_by, self.editor)

    def test_edit_blocked_when_not_draft(self):
        subj = make_subject(state=CentralSubject.State.APPROVED,
                            created_by=self.editor)
        resp = self.client.get(f"/subjects/{subj.id}/edit")
        self.assertEqual(resp.status_code, 400)

    def test_edit_persists(self):
        subj = make_subject(subject_name="Old", created_by=self.editor)
        self.client.post(f"/subjects/{subj.id}/edit", {
            "subject_name": "New",
            "target_grade_level": subj.target_grade_level,
            "target_curriculum": subj.target_curriculum,
            "subject_description": "d",
            "unit": "3",
        })
        subj.refresh_from_db()
        self.assertEqual(subj.subject_name, "New")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_subjects.SubjectCreateEditTests -v 2`
Expected: 404s.

- [ ] **Step 3: Create `central_content/forms.py`**

```python
# central_content/forms.py
from django import forms

from central_content.models import CentralSubject, CentralModule, CentralActivity


class CentralSubjectForm(forms.ModelForm):
    class Meta:
        model = CentralSubject
        fields = [
            "subject_name",
            "subject_descriptive_title",
            "subject_short_name",
            "subject_code",
            "subject_type",
            "subject_description",
            "unit",
            "target_grade_level",
            "target_curriculum",
            "source_notes",
        ]
        widgets = {
            "subject_description": forms.Textarea(attrs={"rows": 4}),
            "source_notes": forms.Textarea(attrs={"rows": 2}),
        }


class CentralModuleForm(forms.ModelForm):
    class Meta:
        model = CentralModule
        fields = ["file_name", "description", "url", "iframe_code", "order"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class CentralActivityForm(forms.ModelForm):
    class Meta:
        model = CentralActivity
        fields = [
            "activity_name",
            "activity_type",
            "activity_instruction",
            "max_score",
            "time_duration",
            "passing_score",
            "passing_score_type",
            "max_retake",
            "retake_method",
            "shuffle_questions",
            "is_graded",
        ]
        widgets = {"activity_instruction": forms.Textarea(attrs={"rows": 4})}
```

- [ ] **Step 4: Add create/edit views to `central_content/views/subjects.py`**

Append to the file:

```python
from django.http import HttpResponseBadRequest, HttpResponseRedirect

from central_content.forms import CentralSubjectForm


@central_role_required(*_ALL_ROLES)
def subject_create(request):
    if request.method == "POST":
        form = CentralSubjectForm(request.POST)
        if form.is_valid():
            subj = form.save(commit=False)
            subj.created_by = request.user
            subj.save()
            return HttpResponseRedirect(f"/subjects/{subj.id}/")
    else:
        form = CentralSubjectForm()
    return render(
        request,
        "central_content/subjects/form.html",
        {"form": form, "subject": None},
    )


@central_role_required(*_ALL_ROLES)
def subject_edit(request, subject_id: int):
    subj = get_object_or_404(CentralSubject, pk=subject_id)
    if subj.state != CentralSubject.State.DRAFT:
        return HttpResponseBadRequest("Can only edit drafts")
    if request.method == "POST":
        form = CentralSubjectForm(request.POST, instance=subj)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(f"/subjects/{subj.id}/")
    else:
        form = CentralSubjectForm(instance=subj)
    return render(
        request,
        "central_content/subjects/form.html",
        {"form": form, "subject": subj},
    )
```

- [ ] **Step 5: Wire the new URLs**

Update `central_content/urls.py` to add:

```python
    path("subjects/new", subject_views.subject_create, name="subject_create"),
    path("subjects/<int:subject_id>/edit", subject_views.subject_edit, name="subject_edit"),
```

(Place these lines in `urlpatterns` before `subject_detail` to avoid `new` being captured as an integer. Django resolves `<int:>` strictly so ordering is not critical, but keep `new` before `<int:>` for readability.)

- [ ] **Step 6: Create `central_content/templates/central_content/subjects/form.html`**

```html
<!-- central_content/templates/central_content/subjects/form.html -->
{% extends "central_content/base.html" %}
{% block title %}{% if subject %}Edit{% else %}New{% endif %} Subject{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">
    {% if subject %}Edit subject{% else %}New subject{% endif %}
</h1>
<form method="post" class="bg-white p-6 rounded shadow space-y-4 max-w-2xl">
    {% csrf_token %}
    {% for field in form %}
    <label class="block">
        <span class="block text-sm font-medium">{{ field.label }}</span>
        {{ field }}
        {% if field.errors %}<p class="text-red-600 text-sm">{{ field.errors.0 }}</p>{% endif %}
    </label>
    {% endfor %}
    <div class="flex gap-2">
        <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
        <a href="{% if subject %}/subjects/{{ subject.id }}/{% else %}/subjects/{% endif %}" class="px-4 py-2">Cancel</a>
    </div>
</form>
{% endblock %}
```

- [ ] **Step 7: Run the tests**

Run: `python manage.py test central_content.tests.test_views_subjects -v 2`
Expected: `OK` (9 tests total).

- [ ] **Step 8: Commit**

```bash
git add central_content/forms.py central_content/views/subjects.py central_content/urls.py central_content/templates/central_content/subjects/form.html central_content/tests/test_views_subjects.py
git commit -m "central_content: subject create/edit views with form"
```

---

## Task 14: Subject state-transition endpoints

**Files:**
- Modify: `central_content/views/subjects.py`
- Modify: `central_content/urls.py`
- Modify: `central_content/tests/test_views_subjects.py`

- [ ] **Step 1: Extend the failing tests**

Append to `central_content/tests/test_views_subjects.py`:

```python
@override_settings(ROOT_URLCONF="central_content.urls")
class SubjectTransitionViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.reviewer = make_reviewer(email="rev@example.com", password="pw")
        self.publisher = make_publisher(email="pub@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_submit_moves_to_in_review(self):
        self._login("ed@example.com")
        subj = make_subject(created_by=self.editor)
        resp = self.client.post(f"/subjects/{subj.id}/submit")
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "in_review")

    def test_approve_by_editor_forbidden(self):
        self._login("ed@example.com")
        subj = make_subject(state=CentralSubject.State.IN_REVIEW,
                            created_by=self.editor)
        resp = self.client.post(f"/subjects/{subj.id}/approve")
        self.assertEqual(resp.status_code, 403)

    def test_approve_by_reviewer(self):
        self._login("rev@example.com")
        subj = make_subject(state=CentralSubject.State.IN_REVIEW,
                            created_by=self.editor)
        resp = self.client.post(f"/subjects/{subj.id}/approve")
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "approved")

    def test_request_changes_by_reviewer(self):
        self._login("rev@example.com")
        subj = make_subject(state=CentralSubject.State.IN_REVIEW,
                            created_by=self.editor)
        resp = self.client.post(
            f"/subjects/{subj.id}/request-changes",
            {"notes": "please fix"},
        )
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.review_notes, "please fix")

    def test_reopen_publisher_only(self):
        subj = make_subject(state=CentralSubject.State.APPROVED,
                            created_by=self.editor)
        self._login("rev@example.com")
        resp = self.client.post(f"/subjects/{subj.id}/reopen")
        self.assertEqual(resp.status_code, 403)

        self._login("pub@example.com")
        resp = self.client.post(f"/subjects/{subj.id}/reopen")
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.version, 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_subjects.SubjectTransitionViewTests -v 2`
Expected: 404s.

- [ ] **Step 3: Add transition views to `central_content/views/subjects.py`**

Append:

```python
from central_content import state_machine
from central_content.state_machine import (
    IllegalTransition, UnresolvedChildren,
)


_REVIEW_ROLES = (CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)
_PUBLISHER_ONLY = (CentralStaff.Role.PUBLISHER,)


def _transition_response(request, subject_id, transition_fn, **kwargs):
    subj = get_object_or_404(CentralSubject, pk=subject_id)
    try:
        transition_fn(subj, actor=request.user, **kwargs)
    except (IllegalTransition, UnresolvedChildren) as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(f"/subjects/{subj.id}/")


@central_role_required(*_ALL_ROLES)
def subject_submit(request, subject_id: int):
    return _transition_response(request, subject_id, state_machine.submit_for_review)


@central_role_required(*_REVIEW_ROLES)
def subject_approve(request, subject_id: int):
    return _transition_response(request, subject_id, state_machine.approve)


@central_role_required(*_REVIEW_ROLES)
def subject_request_changes(request, subject_id: int):
    notes = request.POST.get("notes", "")
    return _transition_response(
        request, subject_id, state_machine.request_changes, notes=notes,
    )


@central_role_required(*_PUBLISHER_ONLY)
def subject_reopen(request, subject_id: int):
    return _transition_response(request, subject_id, state_machine.reopen)
```

- [ ] **Step 4: Wire the new URLs**

Add to `central_content/urls.py`:

```python
    path("subjects/<int:subject_id>/submit", subject_views.subject_submit, name="subject_submit"),
    path("subjects/<int:subject_id>/approve", subject_views.subject_approve, name="subject_approve"),
    path("subjects/<int:subject_id>/request-changes", subject_views.subject_request_changes, name="subject_request_changes"),
    path("subjects/<int:subject_id>/reopen", subject_views.subject_reopen, name="subject_reopen"),
```

- [ ] **Step 5: Run the tests**

Run: `python manage.py test central_content.tests.test_views_subjects -v 2`
Expected: `OK` (14 tests total).

- [ ] **Step 6: Commit**

```bash
git add central_content/views/subjects.py central_content/urls.py central_content/tests/test_views_subjects.py
git commit -m "central_content: subject state transition endpoints"
```

---

## Task 15: Module CRUD + transitions

**Files:**
- Create: `central_content/views/modules.py`
- Modify: `central_content/urls.py`
- Create: `central_content/templates/central_content/modules/detail.html`
- Create: `central_content/templates/central_content/modules/form.html`
- Create: `central_content/tests/test_views_modules.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_views_modules.py
from django.test import TestCase, override_settings

from central_content.models import CentralModule, CentralSubject
from central_content.tests.factories import (
    make_editor, make_reviewer,
    make_subject, make_module,
)


@override_settings(ROOT_URLCONF="central_content.urls")
class ModuleViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="e@example.com", password="pw")
        self.reviewer = make_reviewer(email="r@example.com", password="pw")
        self.subject = make_subject(created_by=self.editor)
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})

    def test_new_form(self):
        resp = self.client.get(f"/subjects/{self.subject.id}/modules/new")
        self.assertEqual(resp.status_code, 200)

    def test_create_module(self):
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/new", {
            "file_name": "L1",
            "description": "d",
            "url": "",
            "iframe_code": "",
            "order": "0",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CentralModule.objects.filter(central_subject=self.subject,
                                         file_name="L1").exists()
        )

    def test_edit_blocked_when_not_draft(self):
        m = make_module(central_subject=self.subject, created_by=self.editor,
                        state=CentralModule.State.APPROVED)
        resp = self.client.get(f"/subjects/{self.subject.id}/modules/{m.id}/edit")
        self.assertEqual(resp.status_code, 400)

    def test_submit_transition(self):
        m = make_module(central_subject=self.subject, created_by=self.editor)
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/{m.id}/submit")
        self.assertEqual(resp.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.state, "in_review")

    def test_approve_by_editor_forbidden(self):
        m = make_module(central_subject=self.subject, created_by=self.editor,
                        state=CentralModule.State.IN_REVIEW)
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/{m.id}/approve")
        self.assertEqual(resp.status_code, 403)

    def test_approve_by_reviewer(self):
        self.client.post("/login", {"email": "r@example.com", "password": "pw"})
        m = make_module(central_subject=self.subject, created_by=self.editor,
                        state=CentralModule.State.IN_REVIEW)
        resp = self.client.post(f"/subjects/{self.subject.id}/modules/{m.id}/approve")
        self.assertEqual(resp.status_code, 302)
        m.refresh_from_db()
        self.assertEqual(m.state, "approved")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_modules -v 2`
Expected: 404s.

- [ ] **Step 3: Create `central_content/views/modules.py`**

```python
# central_content/views/modules.py
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content import state_machine
from central_content.forms import CentralModuleForm
from central_content.models import CentralModule, CentralStaff, CentralSubject
from central_content.permissions import central_role_required
from central_content.state_machine import IllegalTransition


_ALL = (CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)
_REVIEW = (CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)


def _get_subject(subject_id):
    return get_object_or_404(CentralSubject, pk=subject_id)


def _get_module(subject_id, module_id):
    return get_object_or_404(
        CentralModule, pk=module_id, central_subject_id=subject_id,
    )


@central_role_required(*_ALL)
def module_create(request, subject_id: int):
    subject = _get_subject(subject_id)
    if request.method == "POST":
        form = CentralModuleForm(request.POST, request.FILES)
        if form.is_valid():
            m = form.save(commit=False)
            m.central_subject = subject
            m.created_by = request.user
            m.save()
            return HttpResponseRedirect(f"/subjects/{subject.id}/")
    else:
        form = CentralModuleForm()
    return render(
        request, "central_content/modules/form.html",
        {"form": form, "subject": subject, "module": None},
    )


@central_role_required(*_ALL)
def module_detail(request, subject_id: int, module_id: int):
    subject = _get_subject(subject_id)
    module = _get_module(subject_id, module_id)
    return render(
        request, "central_content/modules/detail.html",
        {"subject": subject, "module": module},
    )


@central_role_required(*_ALL)
def module_edit(request, subject_id: int, module_id: int):
    subject = _get_subject(subject_id)
    module = _get_module(subject_id, module_id)
    if module.state != CentralModule.State.DRAFT:
        return HttpResponseBadRequest("Can only edit drafts")
    if request.method == "POST":
        form = CentralModuleForm(request.POST, request.FILES, instance=module)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                f"/subjects/{subject.id}/modules/{module.id}/"
            )
    else:
        form = CentralModuleForm(instance=module)
    return render(
        request, "central_content/modules/form.html",
        {"form": form, "subject": subject, "module": module},
    )


def _module_transition(request, subject_id, module_id, fn, **kwargs):
    module = _get_module(subject_id, module_id)
    try:
        fn(module, actor=request.user, **kwargs)
    except IllegalTransition as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(f"/subjects/{subject_id}/modules/{module.id}/")


@central_role_required(*_ALL)
def module_submit(request, subject_id: int, module_id: int):
    return _module_transition(request, subject_id, module_id, state_machine.submit_for_review)


@central_role_required(*_REVIEW)
def module_approve(request, subject_id: int, module_id: int):
    return _module_transition(request, subject_id, module_id, state_machine.approve)


@central_role_required(*_REVIEW)
def module_request_changes(request, subject_id: int, module_id: int):
    notes = request.POST.get("notes", "")
    return _module_transition(
        request, subject_id, module_id,
        state_machine.request_changes, notes=notes,
    )
```

- [ ] **Step 4: Wire URLs**

Add to `central_content/urls.py` (import `modules as module_views` and append):

```python
from central_content.views import modules as module_views

# ... in urlpatterns ...
    path("subjects/<int:subject_id>/modules/new", module_views.module_create, name="module_create"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/", module_views.module_detail, name="module_detail"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/edit", module_views.module_edit, name="module_edit"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/submit", module_views.module_submit, name="module_submit"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/approve", module_views.module_approve, name="module_approve"),
    path("subjects/<int:subject_id>/modules/<int:module_id>/request-changes", module_views.module_request_changes, name="module_request_changes"),
```

- [ ] **Step 5: Create the module templates**

`central_content/templates/central_content/modules/form.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{% if module %}Edit{% else %}New{% endif %} module{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">
    {% if module %}Edit module{% else %}New module{% endif %} — {{ subject.subject_name }}
</h1>
<form method="post" enctype="multipart/form-data" class="bg-white p-6 rounded shadow max-w-2xl space-y-4">
    {% csrf_token %}
    {% for field in form %}
    <label class="block">
        <span class="block text-sm font-medium">{{ field.label }}</span>
        {{ field }}
        {% if field.errors %}<p class="text-red-600 text-sm">{{ field.errors.0 }}</p>{% endif %}
    </label>
    {% endfor %}
    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
    <a href="/subjects/{{ subject.id }}/" class="px-4 py-2">Cancel</a>
</form>
{% endblock %}
```

`central_content/templates/central_content/modules/detail.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{{ module.file_name }}{% endblock %}
{% block content %}
<nav class="text-sm text-gray-500 mb-2">
    <a href="/subjects/{{ subject.id }}/" class="text-blue-700">{{ subject.subject_name }}</a> &raquo; Module
</nav>
<h1 class="text-2xl font-semibold">{{ module.file_name }}</h1>
<p class="text-gray-600">State: {{ module.state }}</p>

<div class="bg-white p-4 rounded shadow mt-4">
    <p>{{ module.description|default:"No description." }}</p>
    {% if module.url %}<p><a href="{{ module.url }}" class="text-blue-700">External link</a></p>{% endif %}
    {% if module.file %}<p><a href="{{ module.file.url }}" class="text-blue-700">Attached file</a></p>{% endif %}
    {% if module.review_notes %}
    <div class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
        <strong>Review notes:</strong> {{ module.review_notes }}
    </div>
    {% endif %}
</div>

<div class="mt-4 flex gap-2">
    {% if module.state == "draft" %}
    <a href="/subjects/{{ subject.id }}/modules/{{ module.id }}/edit" class="border px-3 py-1 rounded">Edit</a>
    <form method="post" action="/subjects/{{ subject.id }}/modules/{{ module.id }}/submit">
        {% csrf_token %}<button class="bg-blue-600 text-white px-3 py-1 rounded">Submit for review</button>
    </form>
    {% elif module.state == "in_review" %}
    {% if request.user.role == "reviewer" or request.user.role == "publisher" %}
    <form method="post" action="/subjects/{{ subject.id }}/modules/{{ module.id }}/approve">
        {% csrf_token %}<button class="bg-green-600 text-white px-3 py-1 rounded">Approve</button>
    </form>
    <form method="post" action="/subjects/{{ subject.id }}/modules/{{ module.id }}/request-changes">
        {% csrf_token %}
        <input type="text" name="notes" placeholder="Notes" class="border p-1">
        <button class="bg-yellow-500 text-white px-3 py-1 rounded">Request changes</button>
    </form>
    {% endif %}
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_views_modules -v 2`
Expected: `OK` (6 tests).

- [ ] **Step 7: Commit**

```bash
git add central_content/views/modules.py central_content/urls.py central_content/templates/central_content/modules/ central_content/tests/test_views_modules.py
git commit -m "central_content: module CRUD and transition views"
```

---

## Task 16: Activity CRUD + transitions

**Files:**
- Create: `central_content/views/activities.py`
- Modify: `central_content/urls.py`
- Create: `central_content/templates/central_content/activities/detail.html`
- Create: `central_content/templates/central_content/activities/form.html`
- Create: `central_content/tests/test_views_activities.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_views_activities.py
from django.test import TestCase, override_settings

from activity.models.activity_model import ActivityType
from central_content.models import CentralActivity
from central_content.tests.factories import (
    make_editor, make_reviewer, make_subject, make_activity,
)


@override_settings(ROOT_URLCONF="central_content.urls")
class ActivityViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="e@example.com", password="pw")
        self.reviewer = make_reviewer(email="r@example.com", password="pw")
        self.subject = make_subject(created_by=self.editor)
        self.atype, _ = ActivityType.objects.get_or_create(name="Quiz")
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})

    def test_new_form_renders(self):
        resp = self.client.get(f"/subjects/{self.subject.id}/activities/new")
        self.assertEqual(resp.status_code, 200)

    def test_create_activity(self):
        resp = self.client.post(f"/subjects/{self.subject.id}/activities/new", {
            "activity_name": "Q1",
            "activity_type": self.atype.id,
            "activity_instruction": "",
            "max_score": "100",
            "time_duration": "0",
            "passing_score": "50",
            "passing_score_type": "percentage",
            "max_retake": "0",
            "retake_method": "highest",
            "is_graded": "on",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CentralActivity.objects.filter(
                central_subject=self.subject, activity_name="Q1"
            ).exists()
        )

    def test_submit_and_approve_cycle(self):
        act = make_activity(central_subject=self.subject, created_by=self.editor)
        self.client.post(f"/subjects/{self.subject.id}/activities/{act.id}/submit")
        act.refresh_from_db()
        self.assertEqual(act.state, "in_review")

        self.client.post("/login", {"email": "r@example.com", "password": "pw"})
        self.client.post(f"/subjects/{self.subject.id}/activities/{act.id}/approve")
        act.refresh_from_db()
        self.assertEqual(act.state, "approved")

    def test_edit_blocked_when_not_draft(self):
        act = make_activity(central_subject=self.subject, created_by=self.editor,
                            state=CentralActivity.State.APPROVED)
        resp = self.client.get(
            f"/subjects/{self.subject.id}/activities/{act.id}/edit"
        )
        self.assertEqual(resp.status_code, 400)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_activities -v 2`
Expected: 404s.

- [ ] **Step 3: Create `central_content/views/activities.py`**

```python
# central_content/views/activities.py
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content import state_machine
from central_content.forms import CentralActivityForm
from central_content.models import CentralActivity, CentralStaff, CentralSubject
from central_content.permissions import central_role_required
from central_content.state_machine import IllegalTransition


_ALL = (CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)
_REVIEW = (CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)


def _get_subject(sid):
    return get_object_or_404(CentralSubject, pk=sid)


def _get_activity(sid, aid):
    return get_object_or_404(
        CentralActivity, pk=aid, central_subject_id=sid,
    )


@central_role_required(*_ALL)
def activity_create(request, subject_id: int):
    subject = _get_subject(subject_id)
    if request.method == "POST":
        form = CentralActivityForm(request.POST)
        if form.is_valid():
            act = form.save(commit=False)
            act.central_subject = subject
            act.created_by = request.user
            act.save()
            return HttpResponseRedirect(f"/subjects/{subject.id}/")
    else:
        form = CentralActivityForm()
    return render(
        request, "central_content/activities/form.html",
        {"form": form, "subject": subject, "activity": None},
    )


@central_role_required(*_ALL)
def activity_detail(request, subject_id: int, activity_id: int):
    subject = _get_subject(subject_id)
    activity = _get_activity(subject_id, activity_id)
    return render(
        request, "central_content/activities/detail.html",
        {"subject": subject, "activity": activity},
    )


@central_role_required(*_ALL)
def activity_edit(request, subject_id: int, activity_id: int):
    subject = _get_subject(subject_id)
    activity = _get_activity(subject_id, activity_id)
    if activity.state != CentralActivity.State.DRAFT:
        return HttpResponseBadRequest("Can only edit drafts")
    if request.method == "POST":
        form = CentralActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(
                f"/subjects/{subject.id}/activities/{activity.id}/"
            )
    else:
        form = CentralActivityForm(instance=activity)
    return render(
        request, "central_content/activities/form.html",
        {"form": form, "subject": subject, "activity": activity},
    )


def _transition(request, sid, aid, fn, **kw):
    activity = _get_activity(sid, aid)
    try:
        fn(activity, actor=request.user, **kw)
    except IllegalTransition as exc:
        return HttpResponseBadRequest(str(exc))
    return HttpResponseRedirect(f"/subjects/{sid}/activities/{activity.id}/")


@central_role_required(*_ALL)
def activity_submit(request, subject_id: int, activity_id: int):
    return _transition(request, subject_id, activity_id, state_machine.submit_for_review)


@central_role_required(*_REVIEW)
def activity_approve(request, subject_id: int, activity_id: int):
    return _transition(request, subject_id, activity_id, state_machine.approve)


@central_role_required(*_REVIEW)
def activity_request_changes(request, subject_id: int, activity_id: int):
    notes = request.POST.get("notes", "")
    return _transition(
        request, subject_id, activity_id,
        state_machine.request_changes, notes=notes,
    )
```

- [ ] **Step 4: Wire URLs**

Add to `central_content/urls.py` (import `activities as activity_views`):

```python
    path("subjects/<int:subject_id>/activities/new", activity_views.activity_create, name="activity_create"),
    path("subjects/<int:subject_id>/activities/<int:activity_id>/", activity_views.activity_detail, name="activity_detail"),
    path("subjects/<int:subject_id>/activities/<int:activity_id>/edit", activity_views.activity_edit, name="activity_edit"),
    path("subjects/<int:subject_id>/activities/<int:activity_id>/submit", activity_views.activity_submit, name="activity_submit"),
    path("subjects/<int:subject_id>/activities/<int:activity_id>/approve", activity_views.activity_approve, name="activity_approve"),
    path("subjects/<int:subject_id>/activities/<int:activity_id>/request-changes", activity_views.activity_request_changes, name="activity_request_changes"),
```

- [ ] **Step 5: Create activity templates**

`central_content/templates/central_content/activities/form.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{% if activity %}Edit{% else %}New{% endif %} activity{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">
    {% if activity %}Edit activity{% else %}New activity{% endif %} — {{ subject.subject_name }}
</h1>
<form method="post" class="bg-white p-6 rounded shadow max-w-2xl space-y-4">
    {% csrf_token %}
    {% for field in form %}
    <label class="block">
        <span class="block text-sm font-medium">{{ field.label }}</span>
        {{ field }}
        {% if field.errors %}<p class="text-red-600 text-sm">{{ field.errors.0 }}</p>{% endif %}
    </label>
    {% endfor %}
    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
    <a href="/subjects/{{ subject.id }}/" class="px-4 py-2">Cancel</a>
</form>
{% endblock %}
```

`central_content/templates/central_content/activities/detail.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{{ activity.activity_name }}{% endblock %}
{% block content %}
<nav class="text-sm text-gray-500 mb-2">
    <a href="/subjects/{{ subject.id }}/" class="text-blue-700">{{ subject.subject_name }}</a> &raquo; Activity
</nav>
<h1 class="text-2xl font-semibold">{{ activity.activity_name }}</h1>
<p class="text-gray-600">State: {{ activity.state }} · Type: {{ activity.activity_type }}</p>
<div class="bg-white p-4 rounded shadow mt-4">
    <p>{{ activity.activity_instruction|default:"No instruction." }}</p>
    <ul class="text-sm text-gray-600 mt-2">
        <li>Max score: {{ activity.max_score }}</li>
        <li>Passing: {{ activity.passing_score }} ({{ activity.passing_score_type }})</li>
        <li>Retakes: {{ activity.max_retake }} ({{ activity.retake_method }})</li>
    </ul>
    {% if activity.review_notes %}
    <div class="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded">
        <strong>Review notes:</strong> {{ activity.review_notes }}
    </div>
    {% endif %}
</div>
<div class="mt-4 flex gap-2">
    {% if activity.state == "draft" %}
    <a href="/subjects/{{ subject.id }}/activities/{{ activity.id }}/edit" class="border px-3 py-1 rounded">Edit</a>
    <form method="post" action="/subjects/{{ subject.id }}/activities/{{ activity.id }}/submit">
        {% csrf_token %}<button class="bg-blue-600 text-white px-3 py-1 rounded">Submit for review</button>
    </form>
    {% elif activity.state == "in_review" %}
    {% if request.user.role == "reviewer" or request.user.role == "publisher" %}
    <form method="post" action="/subjects/{{ subject.id }}/activities/{{ activity.id }}/approve">
        {% csrf_token %}<button class="bg-green-600 text-white px-3 py-1 rounded">Approve</button>
    </form>
    <form method="post" action="/subjects/{{ subject.id }}/activities/{{ activity.id }}/request-changes">
        {% csrf_token %}
        <input type="text" name="notes" placeholder="Notes" class="border p-1">
        <button class="bg-yellow-500 text-white px-3 py-1 rounded">Request changes</button>
    </form>
    {% endif %}
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_views_activities -v 2`
Expected: `OK` (4 tests).

- [ ] **Step 7: Commit**

```bash
git add central_content/views/activities.py central_content/urls.py central_content/templates/central_content/activities/ central_content/tests/test_views_activities.py
git commit -m "central_content: activity CRUD and transition views"
```

---

## Task 17: Staff management views (Publisher only)

**Files:**
- Create: `central_content/views/staff.py`
- Modify: `central_content/urls.py`
- Create: `central_content/templates/central_content/staff/list.html`
- Create: `central_content/templates/central_content/staff/form.html`
- Create: `central_content/tests/test_views_staff.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_views_staff.py
from django.test import TestCase, override_settings

from central_content.models import CentralStaff
from central_content.tests.factories import (
    make_editor, make_publisher,
)


@override_settings(ROOT_URLCONF="central_content.urls")
class StaffViewTests(TestCase):
    def setUp(self):
        self.pub = make_publisher(email="p@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_editor_cannot_access(self):
        make_editor(email="ed@example.com", password="pw")
        self._login("ed@example.com")
        resp = self.client.get("/staff/")
        self.assertEqual(resp.status_code, 403)

    def test_publisher_list(self):
        self._login("p@example.com")
        resp = self.client.get("/staff/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "p@example.com")

    def test_publisher_create(self):
        self._login("p@example.com")
        resp = self.client.post("/staff/new", {
            "email": "new@example.com",
            "full_name": "New One",
            "role": "editor",
            "password": "initialpw",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CentralStaff.objects.filter(email="new@example.com").exists())

    def test_publisher_deactivate(self):
        target = make_editor(email="t@example.com", password="pw")
        self._login("p@example.com")
        resp = self.client.post(f"/staff/{target.id}/edit", {
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": "",  # unchecked
        })
        self.assertEqual(resp.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_active)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_staff -v 2`
Expected: 404s.

- [ ] **Step 3: Create `central_content/views/staff.py`**

```python
# central_content/views/staff.py
from django import forms
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from central_content.models import CentralStaff
from central_content.permissions import central_role_required


class CentralStaffCreateForm(forms.Form):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=CentralStaff.Role.choices)
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)


class CentralStaffEditForm(forms.Form):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=150)
    role = forms.ChoiceField(choices=CentralStaff.Role.choices)
    is_active = forms.BooleanField(required=False)


@central_role_required(CentralStaff.Role.PUBLISHER)
def staff_list(request):
    staff = CentralStaff.objects.all()
    return render(request, "central_content/staff/list.html", {"staff": staff})


@central_role_required(CentralStaff.Role.PUBLISHER)
def staff_create(request):
    if request.method == "POST":
        form = CentralStaffCreateForm(request.POST)
        if form.is_valid():
            CentralStaff.objects.create_user(
                email=form.cleaned_data["email"],
                full_name=form.cleaned_data["full_name"],
                password=form.cleaned_data["password"],
                role=form.cleaned_data["role"],
            )
            return HttpResponseRedirect("/staff/")
    else:
        form = CentralStaffCreateForm()
    return render(request, "central_content/staff/form.html",
                  {"form": form, "target": None})


@central_role_required(CentralStaff.Role.PUBLISHER)
def staff_edit(request, staff_id: int):
    target = get_object_or_404(CentralStaff, pk=staff_id)
    if request.method == "POST":
        form = CentralStaffEditForm(request.POST)
        if form.is_valid():
            target.email = form.cleaned_data["email"]
            target.full_name = form.cleaned_data["full_name"]
            target.role = form.cleaned_data["role"]
            target.is_active = form.cleaned_data["is_active"]
            target.save()
            return HttpResponseRedirect("/staff/")
    else:
        form = CentralStaffEditForm(initial={
            "email": target.email,
            "full_name": target.full_name,
            "role": target.role,
            "is_active": target.is_active,
        })
    return render(request, "central_content/staff/form.html",
                  {"form": form, "target": target})
```

- [ ] **Step 4: Wire URLs**

Add to `central_content/urls.py`:

```python
from central_content.views import staff as staff_views

# in urlpatterns:
    path("staff/", staff_views.staff_list, name="staff_list"),
    path("staff/new", staff_views.staff_create, name="staff_create"),
    path("staff/<int:staff_id>/edit", staff_views.staff_edit, name="staff_edit"),
```

- [ ] **Step 5: Create templates**

`central_content/templates/central_content/staff/list.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Staff{% endblock %}
{% block content %}
<div class="flex justify-between mb-4">
    <h1 class="text-2xl font-semibold">Central Staff</h1>
    <a href="/staff/new" class="bg-blue-600 text-white px-4 py-2 rounded">New staff</a>
</div>
<table class="w-full bg-white rounded shadow">
    <thead class="bg-gray-100"><tr><th class="p-3 text-left">Email</th><th>Name</th><th>Role</th><th>Active</th><th></th></tr></thead>
    <tbody>
    {% for s in staff %}
    <tr class="border-t">
        <td class="p-3">{{ s.email }}</td>
        <td>{{ s.full_name }}</td>
        <td>{{ s.role }}</td>
        <td>{{ s.is_active|yesno:"yes,no" }}</td>
        <td><a href="/staff/{{ s.id }}/edit" class="text-blue-700">Edit</a></td>
    </tr>
    {% endfor %}
    </tbody>
</table>
{% endblock %}
```

`central_content/templates/central_content/staff/form.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{% if target %}Edit{% else %}New{% endif %} staff{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">{% if target %}Edit{% else %}New{% endif %} staff</h1>
<form method="post" class="bg-white p-6 rounded shadow max-w-md space-y-4">
    {% csrf_token %}
    {% for field in form %}
    <label class="block">
        <span class="block text-sm font-medium">{{ field.label }}</span>
        {{ field }}
        {% if field.errors %}<p class="text-red-600 text-sm">{{ field.errors.0 }}</p>{% endif %}
    </label>
    {% endfor %}
    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">Save</button>
    <a href="/staff/" class="px-4 py-2">Cancel</a>
</form>
{% endblock %}
```

- [ ] **Step 6: Run the tests**

Run: `python manage.py test central_content.tests.test_views_staff -v 2`
Expected: `OK` (4 tests).

- [ ] **Step 7: Commit**

```bash
git add central_content/views/staff.py central_content/urls.py central_content/templates/central_content/staff/ central_content/tests/test_views_staff.py
git commit -m "central_content: publisher-only staff management views"
```

---

## Task 18: Dashboard view + audit log view

**Files:**
- Create: `central_content/views/dashboard.py`
- Modify: `central_content/urls.py`
- Create: `central_content/templates/central_content/dashboard.html`
- Create: `central_content/templates/central_content/subjects/history.html`
- Modify: `central_content/views/subjects.py` (add subject history view)
- Create: `central_content/tests/test_views_dashboard.py`
- Create: `central_content/tests/test_audit_log.py`

- [ ] **Step 1: Write the failing tests**

```python
# central_content/tests/test_views_dashboard.py
from django.test import TestCase, override_settings

from central_content.models import CentralSubject
from central_content.tests.factories import make_editor, make_subject


@override_settings(ROOT_URLCONF="central_content.urls")
class DashboardTests(TestCase):
    def test_requires_login(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)

    def test_shows_counts(self):
        editor = make_editor(email="e@example.com", password="pw")
        make_subject(state=CentralSubject.State.DRAFT, created_by=editor)
        make_subject(state=CentralSubject.State.IN_REVIEW, created_by=editor)
        make_subject(state=CentralSubject.State.APPROVED, created_by=editor)
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Draft")
        self.assertContains(resp, "In Review")
        self.assertContains(resp, "Approved")
```

```python
# central_content/tests/test_audit_log.py
from django.test import TestCase, override_settings

from central_content.models import AuditLogEntry
from central_content.state_machine import submit_for_review
from central_content.tests.factories import make_editor, make_subject


@override_settings(ROOT_URLCONF="central_content.urls")
class SubjectHistoryViewTests(TestCase):
    def test_history_lists_entries(self):
        editor = make_editor(email="e@example.com", password="pw")
        subj = make_subject(created_by=editor)
        submit_for_review(subj, actor=editor)
        self.client.post("/login", {"email": "e@example.com", "password": "pw"})
        resp = self.client.get(f"/subjects/{subj.id}/history")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "draft")
        self.assertContains(resp, "in_review")

    def test_audit_entries_written_on_each_transition(self):
        editor = make_editor()
        subj = make_subject(created_by=editor)
        submit_for_review(subj, actor=editor)
        self.assertEqual(AuditLogEntry.objects.count(), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test central_content.tests.test_views_dashboard central_content.tests.test_audit_log -v 2`
Expected: 404s.

- [ ] **Step 3: Create `central_content/views/dashboard.py`**

```python
# central_content/views/dashboard.py
from django.shortcuts import render

from central_content.models import (
    AuditLogEntry,
    CentralActivity,
    CentralModule,
    CentralStaff,
    CentralSubject,
)
from central_content.permissions import central_role_required


_ALL = (CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)


@central_role_required(*_ALL)
def dashboard(request):
    def _counts(model):
        return {
            "draft": model.objects.filter(state=model.State.DRAFT).count(),
            "in_review": model.objects.filter(state=model.State.IN_REVIEW).count(),
            "approved": model.objects.filter(state=model.State.APPROVED).count(),
        }

    context = {
        "subject_counts": _counts(CentralSubject),
        "module_counts": _counts(CentralModule),
        "activity_counts": _counts(CentralActivity),
        "recent_audit": AuditLogEntry.objects.select_related("actor")[:20],
        "review_queue": CentralSubject.objects.filter(
            state=CentralSubject.State.IN_REVIEW
        )[:10],
    }
    return render(request, "central_content/dashboard.html", context)
```

- [ ] **Step 4: Add `subject_history` to `central_content/views/subjects.py`**

Append:

```python
from django.contrib.contenttypes.models import ContentType
from central_content.models import AuditLogEntry, CentralModule, CentralActivity


@central_role_required(*_ALL_ROLES)
def subject_history(request, subject_id: int):
    subj = get_object_or_404(CentralSubject, pk=subject_id)
    subj_ct = ContentType.objects.get_for_model(CentralSubject)
    mod_ct = ContentType.objects.get_for_model(CentralModule)
    act_ct = ContentType.objects.get_for_model(CentralActivity)

    module_ids = list(subj.modules.values_list("id", flat=True))
    activity_ids = list(subj.activities.values_list("id", flat=True))

    from django.db.models import Q
    entries = AuditLogEntry.objects.filter(
        Q(content_type=subj_ct, object_id=subj.id)
        | Q(content_type=mod_ct, object_id__in=module_ids)
        | Q(content_type=act_ct, object_id__in=activity_ids)
    ).select_related("actor")

    return render(
        request, "central_content/subjects/history.html",
        {"subject": subj, "entries": entries},
    )
```

- [ ] **Step 5: Wire the new URLs**

Add to `central_content/urls.py`:

```python
from central_content.views import dashboard as dashboard_views

# Prepend the root dashboard:
    path("", dashboard_views.dashboard, name="dashboard"),
    path("subjects/<int:subject_id>/history", subject_views.subject_history, name="subject_history"),
```

- [ ] **Step 6: Create `central_content/templates/central_content/dashboard.html`**

```html
{% extends "central_content/base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">Dashboard</h1>

<div class="grid grid-cols-3 gap-4 mb-6">
    {% for label, counts in counts_sections %}
    <div class="bg-white p-4 rounded shadow">
        <h2 class="font-semibold">{{ label }}</h2>
        <p class="text-sm">Draft: {{ counts.draft }}</p>
        <p class="text-sm">In Review: {{ counts.in_review }}</p>
        <p class="text-sm">Approved: {{ counts.approved }}</p>
    </div>
    {% endfor %}
</div>

<div class="bg-white p-4 rounded shadow mb-6">
    <h2 class="font-semibold mb-2">Draft</h2>
    <p>Subjects: {{ subject_counts.draft }} · Modules: {{ module_counts.draft }} · Activities: {{ activity_counts.draft }}</p>
    <h2 class="font-semibold mt-3 mb-2">In Review</h2>
    <p>Subjects: {{ subject_counts.in_review }} · Modules: {{ module_counts.in_review }} · Activities: {{ activity_counts.in_review }}</p>
    <h2 class="font-semibold mt-3 mb-2">Approved</h2>
    <p>Subjects: {{ subject_counts.approved }} · Modules: {{ module_counts.approved }} · Activities: {{ activity_counts.approved }}</p>
</div>

<div class="bg-white p-4 rounded shadow mb-6">
    <h2 class="font-semibold mb-2">Needs Review</h2>
    <ul>
    {% for s in review_queue %}
        <li class="py-1"><a href="/subjects/{{ s.id }}/" class="text-blue-700">{{ s.subject_name }}</a></li>
    {% empty %}
        <li class="text-gray-500">Nothing waiting.</li>
    {% endfor %}
    </ul>
</div>

<div class="bg-white p-4 rounded shadow">
    <h2 class="font-semibold mb-2">Recent activity</h2>
    <ul>
    {% for e in recent_audit %}
        <li class="py-1 text-sm">{{ e.created_at|date:"Y-m-d H:i" }} — {{ e.actor.email }} — {{ e.from_state }} → {{ e.to_state }}</li>
    {% empty %}
        <li class="text-gray-500">No activity yet.</li>
    {% endfor %}
    </ul>
</div>
{% endblock %}
```

- [ ] **Step 7: Create `central_content/templates/central_content/subjects/history.html`**

```html
{% extends "central_content/base.html" %}
{% block title %}History — {{ subject.subject_name }}{% endblock %}
{% block content %}
<nav class="text-sm text-gray-500 mb-2">
    <a href="/subjects/{{ subject.id }}/" class="text-blue-700">{{ subject.subject_name }}</a> &raquo; History
</nav>
<h1 class="text-2xl font-semibold mb-4">History</h1>
<ul class="bg-white p-4 rounded shadow">
{% for e in entries %}
    <li class="border-b py-2 text-sm">{{ e.created_at|date:"Y-m-d H:i" }} — {{ e.actor.email }} — {{ e.content_type.model }}#{{ e.object_id }}: {{ e.from_state }} → {{ e.to_state }}{% if e.notes %} ({{ e.notes }}){% endif %}</li>
{% empty %}
    <li class="text-gray-500">No entries.</li>
{% endfor %}
</ul>
{% endblock %}
```

- [ ] **Step 8: Run the tests**

Run: `python manage.py test central_content.tests.test_views_dashboard central_content.tests.test_audit_log -v 2`
Expected: `OK` (4 tests).

- [ ] **Step 9: Commit**

```bash
git add central_content/views/dashboard.py central_content/views/subjects.py central_content/urls.py central_content/templates/central_content/dashboard.html central_content/templates/central_content/subjects/history.html central_content/tests/test_views_dashboard.py central_content/tests/test_audit_log.py
git commit -m "central_content: dashboard view and subject history/audit log view"
```

---

## Task 19: Full-suite verification and cleanup

**Files:**
- No new files
- Optional: minor fixes surfaced by running the whole suite

- [ ] **Step 1: Run the complete central_content test suite**

Run: `python manage.py test central_content -v 2`
Expected: all tests pass. Target count roughly: `OK` (50+ tests).

- [ ] **Step 2: Run `python manage.py check`**

Run: `python manage.py check`
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 3: Manually boot the central portal locally**

Run: `DJANGO_SETTINGS_MODULE=lms.settings_central python manage.py runserver 8001`
In a separate shell: `curl -i http://localhost:8001/login`
Expected: HTTP 200, login HTML served.

- [ ] **Step 4: Bootstrap first Publisher and smoke-test a full flow**

```bash
python manage.py create_central_staff \
  --email admin@example.com --full-name "Admin" \
  --role publisher --password adminpw123
```

In the browser at `http://localhost:8001/login`:
1. Log in as `admin@example.com`
2. Create a subject via `/subjects/new`
3. Add a module and an activity under it
4. Submit each for review
5. Approve each
6. Approve the subject
7. Reopen the subject — verify version bumps to 2 and children revert to draft

Document anything that failed in a follow-up issue.

- [ ] **Step 5: Commit any cleanup**

If Step 1–4 surfaced no issues, no commit is needed. Otherwise commit fixes with descriptive messages.

---

## Self-Review Checklist

Verify before handing off to implementation:

- **Spec coverage:**
  - Architecture & deployment → Task 1, 2
  - Auth model → Task 3, 11
  - Data model → Tasks 3, 4, 5, 6, 7
  - State machine & permissions → Tasks 9, 10
  - Portal UI & URLs → Tasks 11–18
  - Testing approach → woven through every task + Task 19

- **Placeholder scan:** no "TODO", "TBD", "implement later", "add validation", "handle edge cases", or "similar to". Every step has runnable code or an exact command.

- **Type consistency:**
  - `CentralStaff.Role` values: `"editor"`, `"reviewer"`, `"publisher"` — used identically everywhere.
  - State values: `"draft"`, `"in_review"`, `"approved"` — consistent across models, state machine, and tests.
  - `state_machine.submit_for_review`, `approve`, `request_changes`, `reopen` — the same four names appear in state machine code, tests, and view code.
  - Transition exceptions: `IllegalTransition`, `UnresolvedChildren` — imported consistently.
  - Factory function names: `make_editor`, `make_reviewer`, `make_publisher`, `make_subject`, `make_module`, `make_activity` — used identically across all test files.

- **Known simplifications for the first cut (acceptable per YAGNI):**
  - No email password-reset flow UI; admins reset via management command if needed.
  - No rich text editor; stock textareas.
  - Dashboard has no bulk queue actions.
  - No per-object edit audit log — only state transitions are logged.
  - Staff edit form does not change password; password changes are out of scope for Sub-project 1.

## Notes for Sub-project 2 (not part of this plan)

- `central_subject_id` will be referenced by whatever tenant-copy record Sub-project 2 introduces on the school side.
- `version` integer is already bumped on `reopen`; Sub-project 2's re-push workflow can compare versions.
- `state_machine` is currently the only place that knows when to write `AuditLogEntry`; push actions should follow the same pattern.
