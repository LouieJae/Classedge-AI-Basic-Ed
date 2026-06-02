# Old LMS Migration Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, end-to-end data migration foundation from `simulation-lms/classedge` (old LMS) into `Classedge-Ai` (new LMS), proven by migrating the `roles.Role` model, with a Django dashboard that tracks per-row errors down to source file and line number.

**Architecture:** Two cooperating Django apps. On the old side, a new additive `migration_api` app exposes token-authenticated, throttled, cursor-paginated read-only DRF endpoints. On the new side, a new `migration` app pulls pages via Celery, runs per-model mapper functions, writes through an idempotent writer that records `IDMap` rows, captures every failure into `MigrationErrorRecord` with project-frame source location, and surfaces everything in a HTMX-driven dashboard extending `base_operation.html`.

**Tech Stack:** Django 5, DRF, django-environ, Celery + Redis, HTMX, pytest-django, `responses` library for HTTP mocking, requests.

**Spec:** `docs/superpowers/specs/2026-05-20-old-lms-migration-foundation-design.md`

---

## Paths & Conventions

- **NEW codebase root:** `/home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/`
- **OLD codebase root:** `/home/classify/Desktop/Projects/simulation-lms/classedge/`
- All paths in tasks are absolute unless prefixed `NEW/` or `OLD/`.
- Commit messages: conventional commits (`feat:`, `test:`, `fix:`, `chore:`, `docs:`).
- After every task ends with a commit step. Do not batch commits across tasks.

---

## File Structure (locked decisions)

### OLD side — new files only
```
OLD/migration_api/__init__.py
OLD/migration_api/apps.py
OLD/migration_api/models.py
OLD/migration_api/migrations/__init__.py
OLD/migration_api/migrations/0001_initial.py        # auto-generated
OLD/migration_api/authentication.py
OLD/migration_api/throttling.py
OLD/migration_api/pagination.py
OLD/migration_api/serializers/__init__.py
OLD/migration_api/serializers/role.py
OLD/migration_api/views/__init__.py
OLD/migration_api/views/base.py
OLD/migration_api/views/health.py
OLD/migration_api/views/role.py
OLD/migration_api/urls.py
OLD/migration_api/admin.py
OLD/migration_api/tests/__init__.py
OLD/migration_api/tests/conftest.py
OLD/migration_api/tests/test_authentication.py
OLD/migration_api/tests/test_throttling.py
OLD/migration_api/tests/test_pagination.py
OLD/migration_api/tests/test_role_endpoint.py
OLD/migration_api/tests/test_health.py
```

### OLD side — touched
- `OLD/lms/settings.py` — append to `INSTALLED_APPS`, add `MIGRATION_API_THROTTLES` block.
- `OLD/lms/urls.py` — one `include()` line.

### NEW side — new files
```
NEW/migration/__init__.py
NEW/migration/apps.py
NEW/migration/models/__init__.py
NEW/migration/models/job.py
NEW/migration/models/idmap.py
NEW/migration/models/run_log.py
NEW/migration/models/error_record.py
NEW/migration/migrations/__init__.py
NEW/migration/migrations/0001_initial.py            # auto-generated
NEW/migration/client/__init__.py
NEW/migration/client/exceptions.py
NEW/migration/client/http.py
NEW/migration/mappers/__init__.py
NEW/migration/mappers/base.py
NEW/migration/mappers/roles_role.py
NEW/migration/writers/__init__.py
NEW/migration/writers/base.py
NEW/migration/tasks/__init__.py
NEW/migration/tasks/batch.py
NEW/migration/tasks/pipeline.py
NEW/migration/tasks/verify.py
NEW/migration/tasks/retry.py
NEW/migration/services/__init__.py
NEW/migration/services/error_capture.py
NEW/migration/services/progress.py
NEW/migration/views/__init__.py
NEW/migration/views/overview.py
NEW/migration/views/job_detail.py
NEW/migration/views/errors.py
NEW/migration/views/actions.py
NEW/migration/templates/migration/base.html
NEW/migration/templates/migration/overview.html
NEW/migration/templates/migration/job_detail.html
NEW/migration/templates/migration/errors.html
NEW/migration/templates/migration/_job_row.html
NEW/migration/templates/migration/_run_log_tail.html
NEW/migration/templates/migration/_error_drawer.html
NEW/migration/static/migration/migration.css
NEW/migration/urls.py
NEW/migration/admin.py
NEW/migration/settings_defaults.py
NEW/migration/tests/__init__.py
NEW/migration/tests/conftest.py
NEW/migration/tests/test_models.py
NEW/migration/tests/test_http_client.py
NEW/migration/tests/test_error_capture.py
NEW/migration/tests/test_mappers_base.py
NEW/migration/tests/test_mappers_roles_role.py
NEW/migration/tests/test_writers_base.py
NEW/migration/tests/test_tasks_batch.py
NEW/migration/tests/test_tasks_pipeline.py
NEW/migration/tests/test_tasks_verify.py
NEW/migration/tests/test_tasks_retry.py
NEW/migration/tests/test_views_overview.py
NEW/migration/tests/test_views_errors.py
NEW/migration/tests/test_views_actions.py
NEW/migration/tests/test_e2e_roles_role.py
NEW/docs/migration/runbook-foundation.md
```

### NEW side — touched
- `NEW/lms/settings.py` — append `INSTALLED_APPS`, import `migration.settings_defaults`, install `django-environ` block if not present.
- `NEW/lms/urls.py` — one `include()` line.
- `NEW/lms/celery.py` — confirm `app.autodiscover_tasks()` covers `migration.tasks`.
- `NEW/.env.example` — append new env vars.
- `NEW/requirements.txt` — add `responses` (dev), confirm `requests` present.

---

## Phase 0 — Pre-flight

### Task 1: Verify simulation classedge boots and the Role model is reachable

**Files:**
- Read only

- [ ] **Step 1: Inspect the Role model already present in simulation**

Run: `cat /home/classify/Desktop/Projects/simulation-lms/classedge/roles/models.py`
Expected output should include:
```python
class Role(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
```

- [ ] **Step 2: Confirm simulation Django project boots**

Run:
```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py check
```
Expected: `System check identified no issues (0 silenced).` If it fails, stop the plan and resolve dependencies before proceeding.

- [ ] **Step 3: Count Role rows in simulation DB and capture a sample**

Run:
```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py shell -c "from roles.models import Role; print('count=', Role.objects.count()); print('sample=', list(Role.objects.values('id','name','created_at','updated_at')[:3]))"
```
Record both numbers in your scratch notes — Phase E uses them for acceptance.

- [ ] **Step 4: Commit (no code change yet, but capture findings)**

Append the count + sample to `NEW/docs/superpowers/notes/` if such a folder exists, else create `NEW/docs/migration/preflight-2026-05-20.md` with:
```markdown
# Pre-flight findings — 2026-05-20

- Simulation Role count: <N>
- Sample row: <paste>
- `manage.py check` passes: yes
```

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
git add docs/migration/preflight-2026-05-20.md
git commit -m "docs(migration): preflight findings for simulation classedge"
```

---

## Phase A — Old side: `migration_api` skeleton

### Task 2: Scaffold the `migration_api` Django app

**Files:**
- Create: `OLD/migration_api/__init__.py`
- Create: `OLD/migration_api/apps.py`
- Create: `OLD/migration_api/urls.py`
- Create: `OLD/migration_api/admin.py` (empty)
- Create: `OLD/migration_api/views/__init__.py` (empty)
- Create: `OLD/migration_api/tests/__init__.py` (empty)
- Modify: `OLD/lms/settings.py` — append to `INSTALLED_APPS`
- Modify: `OLD/lms/urls.py` — add include

- [ ] **Step 1: Create the app directory and stub files**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
mkdir -p migration_api/views migration_api/tests migration_api/serializers migration_api/migrations
touch migration_api/__init__.py migration_api/views/__init__.py migration_api/tests/__init__.py migration_api/serializers/__init__.py migration_api/migrations/__init__.py
```

- [ ] **Step 2: Write `migration_api/apps.py`**

```python
from django.apps import AppConfig


class MigrationApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "migration_api"
    verbose_name = "Migration API (read-only export to new LMS)"
```

- [ ] **Step 3: Write empty `migration_api/urls.py`**

```python
from django.urls import path

app_name = "migration_api"
urlpatterns: list = []
```

- [ ] **Step 4: Write empty `migration_api/admin.py`**

```python
# Admin registrations added when models exist (Task 3).
```

- [ ] **Step 5: Add to `INSTALLED_APPS` in `OLD/lms/settings.py`**

Open `/home/classify/Desktop/Projects/simulation-lms/classedge/lms/settings.py`, locate `INSTALLED_APPS = [`, and append `"migration_api",` as the last entry before the closing `]`.

- [ ] **Step 6: Include URLs in `OLD/lms/urls.py`**

Locate the `urlpatterns = [` block and add (preserving existing entries):

```python
    path("api/migration/", include("migration_api.urls")),
```

If `include` is not already imported, ensure `from django.urls import path, include` at the top.

- [ ] **Step 7: Verify Django still boots**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 8: Commit**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
git add migration_api/ lms/settings.py lms/urls.py
git commit -m "feat(migration_api): scaffold app skeleton and URL include"
```

---

### Task 3: Add `MigrationToken` model with hashed storage

**Files:**
- Create: `OLD/migration_api/models.py`
- Modify: `OLD/migration_api/admin.py`
- Create: `OLD/migration_api/migrations/0001_initial.py` (auto-generated)
- Create: `OLD/migration_api/tests/conftest.py`
- Create: `OLD/migration_api/tests/test_token_model.py`

- [ ] **Step 1: Write the failing test for token hashing**

`OLD/migration_api/tests/test_token_model.py`:
```python
import hashlib
import pytest
from migration_api.models import MigrationToken


@pytest.mark.django_db
def test_create_token_stores_sha256_hash_not_plaintext():
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    assert plaintext  # returned to caller exactly once
    assert token.token_hash == hashlib.sha256(plaintext.encode()).hexdigest()
    assert token.token_hash != plaintext
    assert token.is_active is True


@pytest.mark.django_db
def test_resolve_by_plaintext_returns_active_token():
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    found = MigrationToken.objects.resolve(plaintext)
    assert found.pk == token.pk


@pytest.mark.django_db
def test_resolve_returns_none_for_unknown_plaintext():
    assert MigrationToken.objects.resolve("nope") is None


@pytest.mark.django_db
def test_resolve_returns_none_for_inactive_token():
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    token.is_active = False
    token.save()
    assert MigrationToken.objects.resolve(plaintext) is None
```

- [ ] **Step 2: Write `conftest.py` to allow pytest-django**

`OLD/migration_api/tests/conftest.py`:
```python
import pytest


@pytest.fixture(autouse=True)
def _enable_db_access(db):
    """All migration_api tests get DB access by default."""
    yield
```

- [ ] **Step 3: Run the test, expect failure**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
pytest migration_api/tests/test_token_model.py -v
```
Expected: ImportError / ModuleNotFoundError on `MigrationToken`.

- [ ] **Step 4: Implement the model**

`OLD/migration_api/models.py`:
```python
import hashlib
import secrets

from django.db import models


def _hash(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


class MigrationTokenManager(models.Manager):
    def create_token(self, *, label: str) -> tuple[str, "MigrationToken"]:
        plaintext = secrets.token_urlsafe(32)
        token = self.create(label=label, token_hash=_hash(plaintext))
        return plaintext, token

    def resolve(self, plaintext: str) -> "MigrationToken | None":
        if not plaintext:
            return None
        return self.filter(token_hash=_hash(plaintext), is_active=True).first()


class MigrationToken(models.Model):
    label = models.CharField(max_length=120)
    token_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    objects = MigrationTokenManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.label} ({'active' if self.is_active else 'inactive'})"
```

- [ ] **Step 5: Register in admin**

`OLD/migration_api/admin.py`:
```python
from django.contrib import admin, messages

from .models import MigrationToken


@admin.register(MigrationToken)
class MigrationTokenAdmin(admin.ModelAdmin):
    list_display = ("label", "is_active", "created_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("label",)
    readonly_fields = ("token_hash", "created_at", "last_used_at")
    actions = ["create_new_token"]

    @admin.action(description="Create new token (shown once)")
    def create_new_token(self, request, queryset):
        plaintext, token = MigrationToken.objects.create_token(label="adhoc")
        messages.warning(
            request,
            f"Token created (label={token.label}). Copy now — it will not be shown again: {plaintext}",
        )
```

- [ ] **Step 6: Generate and apply the migration**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py makemigrations migration_api
python manage.py migrate migration_api
```
Expected: `Migrations for 'migration_api': 0001_initial.py - Create model MigrationToken`.

- [ ] **Step 7: Re-run the tests, expect pass**

```bash
pytest migration_api/tests/test_token_model.py -v
```
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add migration_api/models.py migration_api/admin.py migration_api/migrations/0001_initial.py migration_api/tests/
git commit -m "feat(migration_api): MigrationToken model with hashed storage + admin"
```

---

### Task 4: Implement `MigrationTokenAuthentication`

**Files:**
- Create: `OLD/migration_api/authentication.py`
- Create: `OLD/migration_api/tests/test_authentication.py`

- [ ] **Step 1: Write the failing tests**

`OLD/migration_api/tests/test_authentication.py`:
```python
import pytest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from migration_api.authentication import MigrationTokenAuthentication
from migration_api.models import MigrationToken


@pytest.fixture
def auth():
    return MigrationTokenAuthentication()


@pytest.fixture
def factory():
    return APIRequestFactory()


def _request(factory, header_value=None):
    headers = {"HTTP_AUTHORIZATION": header_value} if header_value else {}
    return factory.get("/", **headers)


def test_missing_header_returns_none(auth, factory):
    assert auth.authenticate(_request(factory)) is None


def test_wrong_prefix_returns_none(auth, factory):
    assert auth.authenticate(_request(factory, "Bearer abc")) is None


def test_valid_token_returns_anonymous_user_and_token(auth, factory):
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    user, returned_token = auth.authenticate(_request(factory, f"Token {plaintext}"))
    assert returned_token.pk == token.pk
    assert user.is_authenticated is False  # we return AnonymousUser


def test_invalid_token_raises(auth, factory):
    with pytest.raises(AuthenticationFailed):
        auth.authenticate(_request(factory, "Token deadbeef"))


def test_inactive_token_raises(auth, factory):
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    token.is_active = False
    token.save()
    with pytest.raises(AuthenticationFailed):
        auth.authenticate(_request(factory, f"Token {plaintext}"))


def test_valid_token_updates_last_used_at(auth, factory):
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    assert token.last_used_at is None
    auth.authenticate(_request(factory, f"Token {plaintext}"))
    token.refresh_from_db()
    assert token.last_used_at is not None
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration_api/tests/test_authentication.py -v
```

- [ ] **Step 3: Implement the authentication class**

`OLD/migration_api/authentication.py`:
```python
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import MigrationToken


class MigrationTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None
        plaintext = header[len(self.keyword) + 1 :].strip()
        token = MigrationToken.objects.resolve(plaintext)
        if token is None:
            raise exceptions.AuthenticationFailed("Invalid or inactive migration token.")
        MigrationToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        return (AnonymousUser(), token)

    def authenticate_header(self, request):
        return self.keyword
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest migration_api/tests/test_authentication.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add migration_api/authentication.py migration_api/tests/test_authentication.py
git commit -m "feat(migration_api): token authentication with last_used_at tracking"
```

---

### Task 5: Implement scoped throttles

**Files:**
- Create: `OLD/migration_api/throttling.py`
- Create: `OLD/migration_api/tests/test_throttling.py`
- Modify: `OLD/lms/settings.py` — add `REST_FRAMEWORK` throttle rates

- [ ] **Step 1: Write the failing tests**

`OLD/migration_api/tests/test_throttling.py`:
```python
import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from migration_api.authentication import MigrationTokenAuthentication
from migration_api.models import MigrationToken
from migration_api.throttling import MigrationDefaultThrottle, MigrationHeavyThrottle


@pytest.fixture
def factory():
    return APIRequestFactory()


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"migration_default": "3/min", "migration_heavy": "1/min"}})
def test_default_throttle_scope_key_uses_token_id(factory):
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    request = factory.get("/", HTTP_AUTHORIZATION=f"Token {plaintext}")
    user_token = MigrationTokenAuthentication().authenticate(request)
    request.user, request.auth = user_token
    t = MigrationDefaultThrottle()
    assert t.get_cache_key(request, view=None) == f"throttle_migration_default_{token.pk}"


@override_settings(REST_FRAMEWORK={"DEFAULT_THROTTLE_RATES": {"migration_heavy": "1/min"}})
def test_heavy_throttle_has_distinct_scope(factory):
    plaintext, token = MigrationToken.objects.create_token(label="dev")
    request = factory.get("/", HTTP_AUTHORIZATION=f"Token {plaintext}")
    user_token = MigrationTokenAuthentication().authenticate(request)
    request.user, request.auth = user_token
    t = MigrationHeavyThrottle()
    assert t.get_cache_key(request, view=None).startswith("throttle_migration_heavy_")


@pytest.mark.django_db
def test_unauthenticated_request_throttled_by_ip(factory):
    request = factory.get("/")
    request.user = None
    request.auth = None
    t = MigrationDefaultThrottle()
    key = t.get_cache_key(request, view=None)
    # falls back to base behavior (None or ip-based) — must not crash
    assert key is None or key.startswith("throttle_migration_default_ip:")
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration_api/tests/test_throttling.py -v
```

- [ ] **Step 3: Implement the throttles**

`OLD/migration_api/throttling.py`:
```python
from rest_framework.throttling import SimpleRateThrottle


class _MigrationThrottle(SimpleRateThrottle):
    scope = "migration"  # overridden in subclasses

    def get_cache_key(self, request, view):
        token = getattr(request, "auth", None)
        if token is not None and hasattr(token, "pk"):
            ident = str(token.pk)
        else:
            ip = self.get_ident(request)
            if ip is None:
                return None
            ident = f"ip:{ip}"
        return f"throttle_{self.scope}_{ident}"


class MigrationDefaultThrottle(_MigrationThrottle):
    scope = "migration_default"


class MigrationHeavyThrottle(_MigrationThrottle):
    scope = "migration_heavy"
```

- [ ] **Step 4: Add throttle rates to settings**

In `/home/classify/Desktop/Projects/simulation-lms/classedge/lms/settings.py`, locate the `REST_FRAMEWORK = {` block. Add or merge:

```python
REST_FRAMEWORK = {
    # ... existing keys preserved ...
    "DEFAULT_THROTTLE_RATES": {
        # preserve any existing keys, then add:
        "migration_default": "30/min",
        "migration_heavy": "10/min",
    },
}
```

If `DEFAULT_THROTTLE_RATES` already exists, merge — do not replace.

- [ ] **Step 5: Run tests, expect pass**

```bash
pytest migration_api/tests/test_throttling.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add migration_api/throttling.py migration_api/tests/test_throttling.py lms/settings.py
git commit -m "feat(migration_api): scoped throttles keyed by migration token id"
```

---

### Task 6: Implement `CursorByPkPagination`

**Files:**
- Create: `OLD/migration_api/pagination.py`
- Create: `OLD/migration_api/tests/test_pagination.py`

- [ ] **Step 1: Write the failing tests**

`OLD/migration_api/tests/test_pagination.py`:
```python
import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIRequestFactory

from migration_api.pagination import CursorByPkPagination
from roles.models import Role


@pytest.fixture
def roles_5():
    return [Role.objects.create(name=f"R{i}") for i in range(5)]


def _paginate(request, queryset):
    paginator = CursorByPkPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator, page


def test_first_page_no_cursor_returns_first_n(roles_5):
    factory = APIRequestFactory()
    request = factory.get("/?limit=2")
    paginator, page = _paginate(request, Role.objects.all())
    assert [r.pk for r in page] == sorted([r.pk for r in roles_5])[:2]
    response = paginator.get_paginated_response(["a", "b"])
    assert response.data["has_more"] is True
    assert response.data["next_cursor"] == str(page[-1].pk)
    assert response.data["total_estimated"] == 5


def test_cursor_skips_already_seen(roles_5):
    factory = APIRequestFactory()
    sorted_pks = sorted([r.pk for r in roles_5])
    request = factory.get(f"/?limit=10&cursor={sorted_pks[1]}")
    paginator, page = _paginate(request, Role.objects.all())
    assert [r.pk for r in page] == sorted_pks[2:]
    response = paginator.get_paginated_response(["..."])
    assert response.data["has_more"] is False
    assert response.data["next_cursor"] is None


def test_limit_clamped_to_max(roles_5):
    factory = APIRequestFactory()
    request = factory.get("/?limit=99999")
    paginator, page = _paginate(request, Role.objects.all())
    assert len(page) <= 500


def test_invalid_cursor_returns_empty_page(roles_5):
    factory = APIRequestFactory()
    request = factory.get("/?cursor=notanumber")
    paginator, page = _paginate(request, Role.objects.all())
    assert len(page) == 0
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration_api/tests/test_pagination.py -v
```

- [ ] **Step 3: Implement the paginator**

`OLD/migration_api/pagination.py`:
```python
from django.core.cache import cache
from rest_framework.pagination import BasePagination
from rest_framework.response import Response


class CursorByPkPagination(BasePagination):
    """Cursor pagination ordered by pk, stable across long migrations."""

    default_limit = 500
    max_limit = 500

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        self.queryset_model = queryset.model
        cursor = request.query_params.get("cursor")
        try:
            limit = min(int(request.query_params.get("limit", self.default_limit)), self.max_limit)
        except (TypeError, ValueError):
            limit = self.default_limit
        limit = max(1, limit)

        qs = queryset.order_by("pk")
        if cursor:
            try:
                qs = qs.filter(pk__gt=int(cursor))
            except (TypeError, ValueError):
                return []
        page = list(qs[: limit + 1])
        self._has_more = len(page) > limit
        self._page = page[:limit]
        return self._page

    def get_paginated_response(self, data):
        next_cursor = str(self._page[-1].pk) if (self._has_more and self._page) else None
        return Response(
            {
                "results": data,
                "next_cursor": next_cursor,
                "has_more": self._has_more,
                "total_estimated": self._cached_total(),
            }
        )

    def _cached_total(self) -> int:
        key = f"migration_total:{self.queryset_model._meta.label_lower}"
        total = cache.get(key)
        if total is None:
            total = self.queryset_model.objects.count()
            cache.set(key, total, timeout=300)
        return total
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest migration_api/tests/test_pagination.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add migration_api/pagination.py migration_api/tests/test_pagination.py
git commit -m "feat(migration_api): pk-cursor pagination with cached total estimate"
```

---

### Task 7: Implement the base read-only viewset and the health endpoint

**Files:**
- Create: `OLD/migration_api/views/base.py`
- Create: `OLD/migration_api/views/health.py`
- Modify: `OLD/migration_api/urls.py`
- Create: `OLD/migration_api/tests/test_health.py`

- [ ] **Step 1: Write the failing test for `/health/`**

`OLD/migration_api/tests/test_health.py`:
```python
import pytest
from rest_framework.test import APIClient

from migration_api.models import MigrationToken


@pytest.fixture
def client():
    return APIClient()


def test_health_requires_token(client):
    response = client.get("/api/migration/health/")
    assert response.status_code in (401, 403)


def test_health_returns_ok_for_valid_token(client):
    plaintext, _ = MigrationToken.objects.create_token(label="dev")
    client.credentials(HTTP_AUTHORIZATION=f"Token {plaintext}")
    response = client.get("/api/migration/health/")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert "server_time" in response.json()
```

- [ ] **Step 2: Run, expect 404 (no URL registered)**

```bash
pytest migration_api/tests/test_health.py -v
```

- [ ] **Step 3: Implement the base viewset**

`OLD/migration_api/views/base.py`:
```python
from rest_framework.generics import ListAPIView, RetrieveAPIView

from ..authentication import MigrationTokenAuthentication
from ..pagination import CursorByPkPagination
from ..throttling import MigrationDefaultThrottle


class MigrationReadOnlyListView(ListAPIView):
    authentication_classes = [MigrationTokenAuthentication]
    permission_classes = []  # Authentication-only; no permission gate
    throttle_classes = [MigrationDefaultThrottle]
    pagination_class = CursorByPkPagination


class MigrationReadOnlyDetailView(RetrieveAPIView):
    authentication_classes = [MigrationTokenAuthentication]
    permission_classes = []
    throttle_classes = [MigrationDefaultThrottle]
    lookup_field = "pk"
```

- [ ] **Step 4: Implement the health endpoint**

`OLD/migration_api/views/health.py`:
```python
from django.db import connection
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from ..authentication import MigrationTokenAuthentication
from ..throttling import MigrationDefaultThrottle


class HealthView(APIView):
    authentication_classes = [MigrationTokenAuthentication]
    permission_classes = []
    throttle_classes = [MigrationDefaultThrottle]

    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            db_ok = False
        return Response(
            {
                "ok": db_ok,
                "db_ok": db_ok,
                "server_time": timezone.now().isoformat(),
                "version": "1",
            }
        )
```

- [ ] **Step 5: Register the URL**

`OLD/migration_api/urls.py`:
```python
from django.urls import path

from .views.health import HealthView

app_name = "migration_api"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
```

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest migration_api/tests/test_health.py -v
```
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add migration_api/views/ migration_api/urls.py migration_api/tests/test_health.py
git commit -m "feat(migration_api): health endpoint + read-only viewset bases"
```

---

### Task 8: Implement the Role serializer and endpoint

**Files:**
- Create: `OLD/migration_api/serializers/role.py`
- Create: `OLD/migration_api/views/role.py`
- Modify: `OLD/migration_api/urls.py`
- Create: `OLD/migration_api/tests/test_role_endpoint.py`

- [ ] **Step 1: Write the failing test**

`OLD/migration_api/tests/test_role_endpoint.py`:
```python
import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from migration_api.models import MigrationToken
from roles.models import Role


@pytest.fixture
def client_with_token():
    plaintext, _ = MigrationToken.objects.create_token(label="dev")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {plaintext}")
    return client


def test_role_list_requires_token():
    response = APIClient().get("/api/migration/roles/role/")
    assert response.status_code in (401, 403)


def test_role_list_returns_paginated_payload(client_with_token):
    Role.objects.create(name="Teacher")
    Role.objects.create(name="Student")
    response = client_with_token.get("/api/migration/roles/role/?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert "next_cursor" in body
    assert "has_more" in body
    assert "total_estimated" in body
    assert {r["name"] for r in body["results"]} >= {"Teacher", "Student"}


def test_role_payload_exposes_permission_codenames(client_with_token):
    perm = Permission.objects.first()
    assert perm is not None
    role = Role.objects.create(name="Admin")
    role.permissions.add(perm)
    response = client_with_token.get("/api/migration/roles/role/?limit=10")
    body = response.json()
    admin_row = next(r for r in body["results"] if r["name"] == "Admin")
    assert admin_row["permissions"] == [
        {"app_label": perm.content_type.app_label, "codename": perm.codename}
    ]


def test_role_detail_returns_single_row(client_with_token):
    role = Role.objects.create(name="Teacher")
    response = client_with_token.get(f"/api/migration/roles/role/{role.pk}/")
    assert response.status_code == 200
    assert response.json()["name"] == "Teacher"


def test_role_detail_404_for_unknown(client_with_token):
    response = client_with_token.get("/api/migration/roles/role/9999999/")
    assert response.status_code == 404
```

- [ ] **Step 2: Run, expect 404 on URL**

```bash
pytest migration_api/tests/test_role_endpoint.py -v
```

- [ ] **Step 3: Implement the serializer**

`OLD/migration_api/serializers/role.py`:
```python
from rest_framework import serializers

from roles.models import Role


class _PermissionCodenameField(serializers.RelatedField):
    def to_representation(self, value):
        return {"app_label": value.content_type.app_label, "codename": value.codename}


class RoleMigrationSerializer(serializers.ModelSerializer):
    permissions = _PermissionCodenameField(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "permissions", "created_at", "updated_at"]
        read_only_fields = fields
```

- [ ] **Step 4: Implement the view**

`OLD/migration_api/views/role.py`:
```python
from roles.models import Role

from ..serializers.role import RoleMigrationSerializer
from .base import MigrationReadOnlyDetailView, MigrationReadOnlyListView


class RoleMigrationListView(MigrationReadOnlyListView):
    queryset = Role.objects.all().prefetch_related("permissions__content_type").order_by("pk")
    serializer_class = RoleMigrationSerializer


class RoleMigrationDetailView(MigrationReadOnlyDetailView):
    queryset = Role.objects.all().prefetch_related("permissions__content_type")
    serializer_class = RoleMigrationSerializer
```

- [ ] **Step 5: Register URLs**

Replace `OLD/migration_api/urls.py` with:
```python
from django.urls import path

from .views.health import HealthView
from .views.role import RoleMigrationDetailView, RoleMigrationListView

app_name = "migration_api"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("roles/role/", RoleMigrationListView.as_view(), name="roles-role-list"),
    path("roles/role/<int:pk>/", RoleMigrationDetailView.as_view(), name="roles-role-detail"),
]
```

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest migration_api/tests/test_role_endpoint.py -v
```
Expected: 5 passed.

- [ ] **Step 7: Run the full old-side test suite**

```bash
pytest migration_api/ -v
```
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add migration_api/serializers/ migration_api/views/role.py migration_api/urls.py migration_api/tests/test_role_endpoint.py
git commit -m "feat(migration_api): roles.Role read-only list + detail endpoints"
```

---

### Task 9: Manual smoke test — boot the simulation server and curl the endpoints

**Files:**
- None modified.

- [ ] **Step 1: Create a token via manage.py shell**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py shell -c "from migration_api.models import MigrationToken; p, t = MigrationToken.objects.create_token(label='local-dev'); print('TOKEN=', p)"
```
Save the printed token. **Do not commit it.**

- [ ] **Step 2: Boot the simulation server**

```bash
python manage.py runserver 0.0.0.0:8001
```
(Background or separate terminal; the new side will hit `http://localhost:8001`.)

- [ ] **Step 3: Curl health**

```bash
curl -s -H "Authorization: Token <paste>" http://localhost:8001/api/migration/health/ | python -m json.tool
```
Expected: `{"ok": true, ...}`.

- [ ] **Step 4: Curl roles**

```bash
curl -s -H "Authorization: Token <paste>" "http://localhost:8001/api/migration/roles/role/?limit=2" | python -m json.tool
```
Expected: paginated payload.

- [ ] **Step 5: Curl without token**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/api/migration/health/
```
Expected: `401`.

- [ ] **Step 6: Record the working token label in the runbook (to be created in Task 36) — for now, note it in the preflight doc**

Append to `NEW/docs/migration/preflight-2026-05-20.md`:
```markdown
- Health endpoint smoke: PASS
- Roles endpoint smoke: PASS, <N> rows returned
- Unauthenticated request returns 401: confirmed
```

- [ ] **Step 7: Commit (preflight doc)**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
git add docs/migration/preflight-2026-05-20.md
git commit -m "docs(migration): record old-side smoke test results"
```

---

## Phase B — New side foundation (models, client, mappers, writer, error capture)

All remaining tasks operate in `NEW = /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/`.

### Task 10: Scaffold the `migration` Django app

**Files:**
- Create: `NEW/migration/__init__.py`
- Create: `NEW/migration/apps.py`
- Create: `NEW/migration/urls.py`
- Create: `NEW/migration/admin.py` (stub)
- Create: `NEW/migration/settings_defaults.py`
- Create: `NEW/migration/models/__init__.py`
- Create: `NEW/migration/migrations/__init__.py`
- Modify: `NEW/lms/settings.py`
- Modify: `NEW/lms/urls.py`

- [ ] **Step 1: Create directories**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
mkdir -p migration/models migration/migrations migration/client migration/mappers migration/writers migration/tasks migration/services migration/views migration/templates/migration migration/static/migration migration/tests
touch migration/__init__.py migration/models/__init__.py migration/migrations/__init__.py migration/client/__init__.py migration/mappers/__init__.py migration/writers/__init__.py migration/tasks/__init__.py migration/services/__init__.py migration/views/__init__.py migration/tests/__init__.py
```

- [ ] **Step 2: Write `migration/apps.py`**

```python
from django.apps import AppConfig


class MigrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "migration"
    verbose_name = "Old LMS data migration"
```

- [ ] **Step 3: Write `migration/settings_defaults.py`**

```python
"""Defaults loaded into Django settings for the migration app.

Import and merge in lms/settings.py:

    from migration.settings_defaults import apply as apply_migration_defaults
    apply_migration_defaults(globals())
"""
import os


def apply(settings_globals: dict) -> None:
    settings_globals.setdefault("MIGRATION_OLD_LMS_BASE_URL", os.environ.get("MIGRATION_OLD_LMS_BASE_URL", "http://localhost:8001"))
    settings_globals.setdefault("MIGRATION_OLD_LMS_TOKEN", os.environ.get("MIGRATION_OLD_LMS_TOKEN", ""))
    settings_globals.setdefault("MIGRATION_BATCH_SIZE", int(os.environ.get("MIGRATION_BATCH_SIZE", "500")))
    settings_globals.setdefault("MIGRATION_BATCH_INTERVAL_SECONDS", int(os.environ.get("MIGRATION_BATCH_INTERVAL_SECONDS", "30")))
    settings_globals.setdefault("MIGRATION_DRY_RUN", os.environ.get("MIGRATION_DRY_RUN", "False").lower() == "true")
    settings_globals.setdefault("MIGRATION_HTTP_TIMEOUT", int(os.environ.get("MIGRATION_HTTP_TIMEOUT", "30")))
    settings_globals.setdefault("MIGRATION_MAX_RETRIES", int(os.environ.get("MIGRATION_MAX_RETRIES", "5")))
    settings_globals.setdefault("MIGRATION_ENABLED", os.environ.get("MIGRATION_ENABLED", "False").lower() == "true")
    settings_globals.setdefault("MIGRATION_DASHBOARD_POLL_SECONDS", int(os.environ.get("MIGRATION_DASHBOARD_POLL_SECONDS", "3")))
```

- [ ] **Step 4: Write stub `migration/urls.py` and `migration/admin.py`**

`migration/urls.py`:
```python
from django.urls import path

app_name = "migration"
urlpatterns: list = []
```

`migration/admin.py`:
```python
# Registrations added in Task 11.
```

- [ ] **Step 5: Wire into `NEW/lms/settings.py`**

Append `"migration",` to `INSTALLED_APPS`. At the bottom of `settings.py`, add:

```python
from migration.settings_defaults import apply as _apply_migration_defaults
_apply_migration_defaults(globals())
```

- [ ] **Step 6: Wire into `NEW/lms/urls.py`**

Add to `urlpatterns`:
```python
    path("operations/migration/", include("migration.urls")),
```
Ensure `include` is imported.

- [ ] **Step 7: Verify Django boots**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
python manage.py check
```
Expected: passes.

- [ ] **Step 8: Append env vars to `.env.example` if file exists**

If `NEW/.env.example` exists, append:
```
MIGRATION_OLD_LMS_BASE_URL=http://localhost:8001
MIGRATION_OLD_LMS_TOKEN=
MIGRATION_BATCH_SIZE=500
MIGRATION_BATCH_INTERVAL_SECONDS=30
MIGRATION_DRY_RUN=False
MIGRATION_HTTP_TIMEOUT=30
MIGRATION_MAX_RETRIES=5
MIGRATION_ENABLED=False
MIGRATION_DASHBOARD_POLL_SECONDS=3
```

- [ ] **Step 9: Commit**

```bash
git add migration/ lms/settings.py lms/urls.py
git add .env.example 2>/dev/null || true
git commit -m "feat(migration): scaffold app, URL include, settings defaults"
```

---

### Task 11: Implement the four core models

**Files:**
- Create: `NEW/migration/models/job.py`
- Create: `NEW/migration/models/idmap.py`
- Create: `NEW/migration/models/run_log.py`
- Create: `NEW/migration/models/error_record.py`
- Modify: `NEW/migration/models/__init__.py`
- Modify: `NEW/migration/admin.py`
- Create: `NEW/migration/migrations/0001_initial.py` (auto-generated)
- Create: `NEW/migration/tests/conftest.py`
- Create: `NEW/migration/tests/test_models.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/conftest.py`:
```python
import pytest


@pytest.fixture(autouse=True)
def _enable_db_access(db):
    yield
```

`NEW/migration/tests/test_models.py`:
```python
import pytest
from django.core.exceptions import ValidationError

from migration.models import IDMap, MigrationErrorRecord, MigrationJob, MigrationRunLog


def test_migrationjob_unique_per_app_model():
    MigrationJob.objects.create(app_label="roles", model_name="Role")
    with pytest.raises(Exception):
        MigrationJob.objects.create(app_label="roles", model_name="Role")


def test_migrationjob_default_status_pending():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    assert job.status == "pending"


def test_idmap_unique_per_app_model_old_pk():
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk="11")
    with pytest.raises(Exception):
        IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk="22")


def test_idmap_lookup_returns_new_pk():
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="7", new_pk="77")
    assert IDMap.resolve("roles", "Role", "7") == "77"
    assert IDMap.resolve("roles", "Role", "missing") is None


def test_runlog_links_to_job():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    log = MigrationRunLog.objects.create(job=job, rows_in_page=10, rows_written=10)
    assert log.job_id == job.id
    assert log.is_retry is False
    assert log.is_dry_run is False


def test_error_record_required_fields():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    err = MigrationErrorRecord.objects.create(
        job=job,
        category="mapper_error",
        message="boom",
        old_app="roles",
        old_model="Role",
    )
    assert err.resolved is False
    assert err.payload_excerpt == {}
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_models.py -v
```

- [ ] **Step 3: Implement `models/job.py`**

```python
from django.db import models


class MigrationJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    app_label = models.CharField(max_length=64)
    model_name = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    last_cursor = models.CharField(max_length=128, blank=True, default="")
    total_estimated = models.IntegerField(default=0)
    rows_fetched = models.IntegerField(default=0)
    rows_written = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    rows_errored = models.IntegerField(default=0)
    dry_run = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_verification = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("app_label", "model_name")]
        indexes = [models.Index(fields=["status"])]
        ordering = ["app_label", "model_name"]

    def __str__(self) -> str:
        return f"{self.app_label}.{self.model_name} [{self.status}]"
```

- [ ] **Step 4: Implement `models/idmap.py`**

```python
from django.db import models


class IDMap(models.Model):
    app_label = models.CharField(max_length=64)
    model_name = models.CharField(max_length=64)
    old_pk = models.CharField(max_length=64)
    new_pk = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("app_label", "model_name", "old_pk")]
        indexes = [models.Index(fields=["app_label", "model_name", "old_pk"])]

    def __str__(self) -> str:
        return f"{self.app_label}.{self.model_name} {self.old_pk}->{self.new_pk}"

    @classmethod
    def resolve(cls, app_label: str, model_name: str, old_pk) -> str | None:
        row = cls.objects.filter(app_label=app_label, model_name=model_name, old_pk=str(old_pk)).only("new_pk").first()
        return row.new_pk if row else None

    @classmethod
    def upsert(cls, app_label: str, model_name: str, old_pk, new_pk) -> "IDMap":
        obj, _ = cls.objects.update_or_create(
            app_label=app_label, model_name=model_name, old_pk=str(old_pk),
            defaults={"new_pk": str(new_pk)},
        )
        return obj
```

- [ ] **Step 5: Implement `models/run_log.py`**

```python
from django.db import models


class MigrationRunLog(models.Model):
    job = models.ForeignKey("migration.MigrationJob", on_delete=models.CASCADE, related_name="run_logs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cursor_in = models.CharField(max_length=128, blank=True, default="")
    cursor_out = models.CharField(max_length=128, blank=True, default="")
    rows_in_page = models.IntegerField(default=0)
    rows_written = models.IntegerField(default=0)
    rows_skipped = models.IntegerField(default=0)
    rows_errored = models.IntegerField(default=0)
    http_status = models.IntegerField(null=True, blank=True)
    retry_attempt = models.IntegerField(default=0)
    is_retry = models.BooleanField(default=False)
    is_dry_run = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [models.Index(fields=["job", "-started_at"])]
        ordering = ["-started_at"]
```

- [ ] **Step 6: Implement `models/error_record.py`**

```python
from django.db import models


class MigrationErrorRecord(models.Model):
    CATEGORY_CHOICES = [
        ("transport_error", "Transport error"),
        ("auth_error", "Auth error"),
        ("throttled", "Throttled"),
        ("mapper_error", "Mapper error"),
        ("missing_fk", "Missing FK"),
        ("validation", "Validation"),
        ("db_error", "DB error"),
        ("unknown", "Unknown"),
    ]

    job = models.ForeignKey("migration.MigrationJob", on_delete=models.CASCADE, related_name="errors")
    run_log = models.ForeignKey("migration.MigrationRunLog", on_delete=models.SET_NULL, null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    old_app = models.CharField(max_length=64)
    old_model = models.CharField(max_length=64)
    old_pk = models.CharField(max_length=64, blank=True, default="")
    batch_cursor = models.CharField(max_length=128, blank=True, default="")
    batch_index = models.IntegerField(null=True, blank=True)

    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    message = models.CharField(max_length=500)
    field = models.CharField(max_length=120, blank=True, default="")
    expected = models.CharField(max_length=500, blank=True, default="")
    actual = models.CharField(max_length=500, blank=True, default="")

    source_file = models.CharField(max_length=255, blank=True, default="")
    source_line = models.IntegerField(null=True, blank=True)
    source_function = models.CharField(max_length=120, blank=True, default="")
    traceback = models.TextField(blank=True, default="")

    payload_excerpt = models.JSONField(default=dict, blank=True)

    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["job", "category"]),
            models.Index(fields=["resolved", "category"]),
            models.Index(fields=["-occurred_at"]),
        ]
        ordering = ["-occurred_at"]
```

- [ ] **Step 7: Update `models/__init__.py`**

```python
from .error_record import MigrationErrorRecord
from .idmap import IDMap
from .job import MigrationJob
from .run_log import MigrationRunLog

__all__ = ["MigrationJob", "IDMap", "MigrationRunLog", "MigrationErrorRecord"]
```

- [ ] **Step 8: Register admin**

`NEW/migration/admin.py`:
```python
from django.contrib import admin

from .models import IDMap, MigrationErrorRecord, MigrationJob, MigrationRunLog


@admin.register(MigrationJob)
class MigrationJobAdmin(admin.ModelAdmin):
    list_display = ("app_label", "model_name", "status", "rows_written", "rows_errored", "updated_at")
    list_filter = ("status",)


@admin.register(IDMap)
class IDMapAdmin(admin.ModelAdmin):
    list_display = ("app_label", "model_name", "old_pk", "new_pk", "created_at")
    search_fields = ("old_pk", "new_pk")


@admin.register(MigrationRunLog)
class MigrationRunLogAdmin(admin.ModelAdmin):
    list_display = ("job", "started_at", "rows_in_page", "rows_written", "rows_errored", "http_status")


@admin.register(MigrationErrorRecord)
class MigrationErrorRecordAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "job", "category", "old_pk", "resolved")
    list_filter = ("category", "resolved")
    search_fields = ("old_pk", "message")
```

- [ ] **Step 9: Generate and apply migration**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
python manage.py makemigrations migration
python manage.py migrate migration
```

- [ ] **Step 10: Run tests, expect pass**

```bash
pytest migration/tests/test_models.py -v
```
Expected: 6 passed.

- [ ] **Step 11: Commit**

```bash
git add migration/models/ migration/admin.py migration/migrations/0001_initial.py migration/tests/conftest.py migration/tests/test_models.py
git commit -m "feat(migration): core models — Job, IDMap, RunLog, ErrorRecord"
```

---

### Task 12: HTTP client exceptions

**Files:**
- Create: `NEW/migration/client/exceptions.py`

- [ ] **Step 1: Write the file**

```python
class MigrationClientError(Exception):
    """Base for all OldLmsClient errors."""


class AuthError(MigrationClientError):
    """401/403 from old side. Do not retry."""


class ThrottledError(MigrationClientError):
    """429 from old side. Caller should sleep `retry_after` seconds."""

    def __init__(self, message: str, retry_after: float = 1.0):
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(MigrationClientError):
    """5xx or connection error after retries exhausted."""


class PermanentError(MigrationClientError):
    """4xx other than 401/403/429. Do not retry."""
```

- [ ] **Step 2: Commit**

```bash
git add migration/client/exceptions.py
git commit -m "feat(migration): client exception hierarchy"
```

---

### Task 13: Implement `OldLmsClient`

**Files:**
- Create: `NEW/migration/client/http.py`
- Create: `NEW/migration/tests/test_http_client.py`

- [ ] **Step 1: Confirm `responses` is installed**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
python -c "import responses" 2>&1 | head
```
If ModuleNotFoundError:
```bash
pip install responses
echo "responses" >> requirements.txt
```

- [ ] **Step 2: Write failing tests**

`NEW/migration/tests/test_http_client.py`:
```python
import pytest
import responses
from django.test import override_settings

from migration.client.exceptions import AuthError, PermanentError, ThrottledError, TransientError
from migration.client.http import OldLmsClient


@pytest.fixture
def client():
    return OldLmsClient(base_url="http://old/", token="abc", timeout=1, max_retries=2)


@responses.activate
def test_fetch_page_returns_decoded_body(client):
    responses.add(
        responses.GET,
        "http://old/api/migration/roles/role/",
        json={"results": [{"id": 1}], "next_cursor": None, "has_more": False, "total_estimated": 1},
        status=200,
    )
    body = client.fetch_page("roles", "role")
    assert body["results"] == [{"id": 1}]


@responses.activate
def test_fetch_page_sends_token_header(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": []}, status=200)
    client.fetch_page("roles", "role")
    sent = responses.calls[0].request
    assert sent.headers.get("Authorization") == "Token abc"


@responses.activate
def test_fetch_page_appends_cursor_and_limit(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": []}, status=200)
    client.fetch_page("roles", "role", cursor="42", limit=10)
    url = responses.calls[0].request.url
    assert "cursor=42" in url
    assert "limit=10" in url


@responses.activate
def test_401_raises_authentication_error(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=401)
    with pytest.raises(AuthError):
        client.fetch_page("roles", "role")


@responses.activate
def test_403_raises_authentication_error(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=403)
    with pytest.raises(AuthError):
        client.fetch_page("roles", "role")


@responses.activate
def test_429_raises_throttled_with_retry_after(client):
    responses.add(
        responses.GET, "http://old/api/migration/roles/role/",
        status=429, headers={"Retry-After": "7"},
    )
    with pytest.raises(ThrottledError) as exc:
        client.fetch_page("roles", "role")
    assert exc.value.retry_after == 7.0


@responses.activate
def test_500_retries_then_raises_transient(client):
    for _ in range(3):
        responses.add(responses.GET, "http://old/api/migration/roles/role/", status=500)
    with pytest.raises(TransientError):
        client.fetch_page("roles", "role")


@responses.activate
def test_404_raises_permanent(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=404)
    with pytest.raises(PermanentError):
        client.fetch_page("roles", "role")


@responses.activate
def test_health_calls_health_endpoint(client):
    responses.add(responses.GET, "http://old/api/migration/health/", json={"ok": True}, status=200)
    assert client.health()["ok"] is True


@responses.activate
def test_fetch_by_pk_uses_detail_url(client):
    responses.add(responses.GET, "http://old/api/migration/roles/role/7/", json={"id": 7}, status=200)
    assert client.fetch_by_pk("roles", "role", 7)["id"] == 7
```

- [ ] **Step 3: Run, expect ImportError**

```bash
pytest migration/tests/test_http_client.py -v
```

- [ ] **Step 4: Implement the client**

`NEW/migration/client/http.py`:
```python
import time

import requests
from django.conf import settings

from .exceptions import AuthError, PermanentError, ThrottledError, TransientError


class OldLmsClient:
    def __init__(self, base_url: str | None = None, token: str | None = None,
                 timeout: int | None = None, max_retries: int | None = None,
                 backoff_base: float = 1.0):
        self.base_url = (base_url or settings.MIGRATION_OLD_LMS_BASE_URL).rstrip("/")
        self.token = token or settings.MIGRATION_OLD_LMS_TOKEN
        self.timeout = timeout if timeout is not None else settings.MIGRATION_HTTP_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.MIGRATION_MAX_RETRIES
        self.backoff_base = backoff_base
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Token {self.token}"

    def health(self) -> dict:
        return self._get("/api/migration/health/")

    def fetch_page(self, app: str, model: str, cursor: str | None = None, limit: int = 500) -> dict:
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get(f"/api/migration/{app}/{model}/", params=params)

    def fetch_by_pk(self, app: str, model: str, old_pk) -> dict:
        return self._get(f"/api/migration/{app}/{model}/{old_pk}/")

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_exc = exc
                self._sleep(attempt)
                continue
            status = resp.status_code
            if 200 <= status < 300:
                return resp.json()
            if status in (401, 403):
                raise AuthError(f"{status} from old LMS")
            if status == 429:
                retry_after = float(resp.headers.get("Retry-After", "1") or 1)
                raise ThrottledError("429 from old LMS", retry_after=retry_after)
            if 400 <= status < 500:
                raise PermanentError(f"{status} {resp.text[:200]}")
            # 5xx — retry
            last_exc = TransientError(f"{status} {resp.text[:200]}")
            self._sleep(attempt)
        raise TransientError(f"Exhausted retries: {last_exc}") from last_exc

    def _sleep(self, attempt: int) -> None:
        time.sleep(self.backoff_base * (2 ** attempt))
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_http_client.py -v
```
Expected: 10 passed. If `_sleep` makes tests slow, the test client uses `backoff_base=1.0` and `max_retries=2`, which is acceptable (<6s total).

- [ ] **Step 6: Commit**

```bash
git add migration/client/http.py migration/tests/test_http_client.py requirements.txt
git commit -m "feat(migration): OldLmsClient with retries, 401/403/429 handling"
```

---

### Task 14: Implement `error_capture.capture` and the project-frame filter

**Files:**
- Create: `NEW/migration/services/error_capture.py`
- Create: `NEW/migration/tests/test_error_capture.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_error_capture.py`:
```python
import re
from pathlib import Path

import pytest

from migration.models import MigrationErrorRecord, MigrationJob
from migration.services.error_capture import capture


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role")


def _raise_from_inside_project(payload):
    # This file lives under BASE_DIR/migration/tests/, so it qualifies as a project frame.
    raise ValueError("forced failure")


def test_capture_records_minimal_fields(job):
    try:
        _raise_from_inside_project({"id": 1})
    except ValueError as exc:
        capture(job=job, category="mapper_error", exc=exc, payload={"id": 1}, old_pk="1")
    err = MigrationErrorRecord.objects.get()
    assert err.category == "mapper_error"
    assert err.message == "forced failure"
    assert err.old_pk == "1"
    assert err.payload_excerpt == {"id": 1}
    assert err.traceback


def test_capture_source_line_points_at_project_frame(job):
    raising_line: int | None = None
    try:
        raising_line = _raise_from_inside_project.__code__.co_firstlineno + 2  # the `raise` line
        _raise_from_inside_project({})
    except Exception as exc:
        capture(job=job, category="mapper_error", exc=exc)
    err = MigrationErrorRecord.objects.get()
    assert err.source_file.endswith("test_error_capture.py")
    assert err.source_function == "_raise_from_inside_project"
    assert err.source_line == raising_line


def test_capture_redacts_secret_keys(job):
    try:
        _raise_from_inside_project({})
    except Exception as exc:
        capture(job=job, category="mapper_error", exc=exc,
                payload={"id": 1, "password": "hunter2", "api_key": "k", "name": "ok"})
    err = MigrationErrorRecord.objects.get()
    assert err.payload_excerpt["password"] == "***"
    assert err.payload_excerpt["api_key"] == "***"
    assert err.payload_excerpt["name"] == "ok"


def test_capture_caps_long_traceback_and_message(job):
    long_msg = "x" * 1000
    try:
        raise ValueError(long_msg)
    except ValueError as exc:
        capture(job=job, category="mapper_error", exc=exc)
    err = MigrationErrorRecord.objects.get()
    assert len(err.message) <= 500
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_error_capture.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/services/error_capture.py`:
```python
import re
import traceback as tb_module
from pathlib import Path
from typing import Any

from django.conf import settings

from migration.models import MigrationErrorRecord, MigrationJob, MigrationRunLog


_SECRET_KEY_RE = re.compile(r"(password|token|secret|api[_-]?key)", re.IGNORECASE)
_BASE_DIR = Path(settings.BASE_DIR).resolve()


def _is_project_frame(filename: str) -> bool:
    try:
        path = Path(filename).resolve()
    except (OSError, RuntimeError):
        return False
    try:
        path.relative_to(_BASE_DIR)
    except ValueError:
        return False
    # Exclude vendored site-packages even if inside BASE_DIR
    parts = path.parts
    return "site-packages" not in parts and ".venv" not in parts and "env" not in parts


def _innermost_project_frame(tb: tb_module.TracebackException):
    frames = list(tb.stack)
    for frame in reversed(frames):
        if _is_project_frame(frame.filename):
            return frame
    return frames[-1] if frames else None


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if _SECRET_KEY_RE.search(str(k)):
            out[k] = "***"
        else:
            out[k] = v
    return out


def capture(
    *,
    job: MigrationJob,
    category: str,
    exc: BaseException,
    payload: dict | None = None,
    field: str = "",
    expected: str = "",
    actual: str = "",
    old_pk: str = "",
    batch_cursor: str = "",
    batch_index: int | None = None,
    run_log: MigrationRunLog | None = None,
) -> MigrationErrorRecord:
    tb = tb_module.TracebackException.from_exception(exc)
    frame = _innermost_project_frame(tb)
    return MigrationErrorRecord.objects.create(
        job=job,
        run_log=run_log,
        category=category,
        message=str(exc)[:500],
        field=field[:120],
        expected=expected[:500],
        actual=actual[:500],
        old_pk=str(old_pk)[:64],
        batch_cursor=str(batch_cursor)[:128],
        batch_index=batch_index,
        source_file=(frame.filename if frame else "")[:255],
        source_line=(frame.lineno if frame else None),
        source_function=(frame.name if frame else "")[:120],
        traceback=("".join(tb.format()))[:20000],
        old_app=job.app_label,
        old_model=job.model_name,
        payload_excerpt=_redact(payload or {}),
    )
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest migration/tests/test_error_capture.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add migration/services/error_capture.py migration/tests/test_error_capture.py
git commit -m "feat(migration): error_capture with project-frame filter and redaction"
```

---

### Task 15: Mapper base infrastructure

**Files:**
- Create: `NEW/migration/mappers/base.py`
- Modify: `NEW/migration/mappers/__init__.py`
- Create: `NEW/migration/tests/test_mappers_base.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_mappers_base.py`:
```python
import pytest

from migration.mappers import get_mapper, register_mapper
from migration.mappers.base import MapperResult, MissingFKError, require_fk
from migration.models import IDMap


def test_register_and_get_mapper():
    @register_mapper("dummy", "Thing")
    def mapper(payload):
        return MapperResult(fields={"id": payload["id"]})

    assert get_mapper("dummy", "Thing") is mapper


def test_get_mapper_unknown_raises():
    with pytest.raises(KeyError):
        get_mapper("nope", "Nope")


def test_require_fk_returns_new_pk_when_idmap_present():
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="5", new_pk="55")
    assert require_fk("roles", "Role", 5) == "55"


def test_require_fk_raises_when_missing():
    with pytest.raises(MissingFKError) as exc:
        require_fk("roles", "Role", 999)
    assert exc.value.target_app == "roles"
    assert exc.value.target_model == "Role"
    assert exc.value.old_pk == "999"
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_mappers_base.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/mappers/base.py`:
```python
from dataclasses import dataclass, field
from typing import Callable

from migration.models import IDMap


@dataclass
class MapperResult:
    fields: dict
    fk_resolutions: list[tuple] = field(default_factory=list)
    m2m_resolutions: dict[str, list[tuple]] = field(default_factory=dict)
    skip: bool = False
    skip_reason: str = ""


class MissingFKError(Exception):
    def __init__(self, target_app: str, target_model: str, old_pk: str, field_name: str = ""):
        self.target_app = target_app
        self.target_model = target_model
        self.old_pk = str(old_pk)
        self.field_name = field_name
        super().__init__(
            f"IDMap miss: {target_app}.{target_model} old_pk={old_pk}"
            + (f" (field {field_name})" if field_name else "")
        )


def require_fk(target_app: str, target_model: str, old_pk, *, field_name: str = "") -> str:
    new_pk = IDMap.resolve(target_app, target_model, old_pk)
    if new_pk is None:
        raise MissingFKError(target_app, target_model, old_pk, field_name=field_name)
    return new_pk


_REGISTRY: dict[tuple[str, str], Callable] = {}


def register_mapper(app_label: str, model_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[(app_label, model_name)] = fn
        return fn
    return decorator


def get_mapper(app_label: str, model_name: str) -> Callable:
    try:
        return _REGISTRY[(app_label, model_name)]
    except KeyError as e:
        raise KeyError(f"No mapper registered for {app_label}.{model_name}") from e


def all_mappers() -> dict[tuple[str, str], Callable]:
    return dict(_REGISTRY)
```

- [ ] **Step 4: Update `mappers/__init__.py`**

```python
from .base import MapperResult, MissingFKError, all_mappers, get_mapper, register_mapper, require_fk
from . import roles_role  # noqa: F401 — registers mapper on import

__all__ = ["MapperResult", "MissingFKError", "register_mapper", "get_mapper", "all_mappers", "require_fk"]
```

The `roles_role` import will fail until Task 16 — that's expected. Temporarily comment it out and write:
```python
from .base import MapperResult, MissingFKError, all_mappers, get_mapper, register_mapper, require_fk

__all__ = ["MapperResult", "MissingFKError", "register_mapper", "get_mapper", "all_mappers", "require_fk"]
```

We'll add the `roles_role` import in Task 16.

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_mappers_base.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add migration/mappers/base.py migration/mappers/__init__.py migration/tests/test_mappers_base.py
git commit -m "feat(migration): mapper registry, MapperResult, require_fk helper"
```

---

### Task 16: Role mapper

**Files:**
- Create: `NEW/migration/mappers/roles_role.py`
- Modify: `NEW/migration/mappers/__init__.py`
- Create: `NEW/migration/tests/test_mappers_roles_role.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_mappers_roles_role.py`:
```python
import pytest

from migration.mappers.base import MapperResult
from migration.mappers.roles_role import map_role


def test_map_role_basic_fields():
    payload = {
        "id": 1, "name": "Teacher", "permissions": [],
        "created_at": "2024-01-01T00:00:00Z", "updated_at": None,
    }
    result = map_role(payload)
    assert isinstance(result, MapperResult)
    assert result.fields["name"] == "Teacher"
    assert result.fields["created_at"] == "2024-01-01T00:00:00Z"


def test_map_role_records_m2m_permission_codenames():
    payload = {
        "id": 1, "name": "Admin",
        "permissions": [
            {"app_label": "auth", "codename": "add_user"},
            {"app_label": "auth", "codename": "change_user"},
        ],
        "created_at": "2024-01-01T00:00:00Z", "updated_at": None,
    }
    result = map_role(payload)
    assert "permissions" in result.m2m_resolutions
    assert result.m2m_resolutions["permissions"] == [
        ("auth", "add_user"), ("auth", "change_user"),
    ]


def test_map_role_missing_name_raises_keyerror():
    with pytest.raises(KeyError):
        map_role({"id": 1, "permissions": []})
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_mappers_roles_role.py -v
```

- [ ] **Step 3: Implement the mapper**

`NEW/migration/mappers/roles_role.py`:
```python
from .base import MapperResult, register_mapper


@register_mapper("roles", "Role")
def map_role(payload: dict) -> MapperResult:
    perms = [(p["app_label"], p["codename"]) for p in payload.get("permissions", [])]
    return MapperResult(
        fields={
            "name": payload["name"],
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
        },
        m2m_resolutions={"permissions": perms},
    )
```

- [ ] **Step 4: Re-enable the import in `mappers/__init__.py`**

```python
from .base import MapperResult, MissingFKError, all_mappers, get_mapper, register_mapper, require_fk
from . import roles_role  # noqa: F401

__all__ = ["MapperResult", "MissingFKError", "register_mapper", "get_mapper", "all_mappers", "require_fk"]
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_mappers_roles_role.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add migration/mappers/roles_role.py migration/mappers/__init__.py migration/tests/test_mappers_roles_role.py
git commit -m "feat(migration): roles.Role mapper with permission codename M2M"
```

---

### Task 17: Writer base

**Files:**
- Create: `NEW/migration/writers/base.py`
- Modify: `NEW/migration/writers/__init__.py`
- Create: `NEW/migration/tests/test_writers_base.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_writers_base.py`:
```python
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from migration.mappers.base import MapperResult
from migration.models import IDMap
from migration.writers.base import RowWriter
from roles.models import Role


@pytest.fixture
def writer():
    return RowWriter(app_label="roles", model_name="Role", target_model=Role)


def _role_payload(id_, name="R", perms=None):
    return {"id": id_, "name": name, "permissions": perms or [], "created_at": None, "updated_at": None}


def test_writer_creates_new_row_and_idmap(writer):
    result = MapperResult(fields={"name": "Teacher"}, m2m_resolutions={})
    obj = writer.write(old_pk="1", mapper_result=result)
    assert obj.pk is not None
    assert Role.objects.get(pk=obj.pk).name == "Teacher"
    assert IDMap.resolve("roles", "Role", "1") == str(obj.pk)


def test_writer_is_idempotent_on_rerun(writer):
    r1 = writer.write(old_pk="1", mapper_result=MapperResult(fields={"name": "Teacher"}))
    r2 = writer.write(old_pk="1", mapper_result=MapperResult(fields={"name": "Teacher"}))
    assert r1.pk == r2.pk
    assert Role.objects.filter(name="Teacher").count() == 1


def test_writer_resolves_m2m_permission_codenames(writer):
    ct = ContentType.objects.first()
    perm = Permission.objects.create(content_type=ct, codename="dummy_xyz", name="Dummy")
    result = MapperResult(
        fields={"name": "Admin"},
        m2m_resolutions={"permissions": [(perm.content_type.app_label, "dummy_xyz")]},
    )
    role = writer.write(old_pk="2", mapper_result=result)
    assert list(role.permissions.values_list("codename", flat=True)) == ["dummy_xyz"]


def test_writer_dry_run_skips_save(writer):
    obj = writer.write(old_pk="3", mapper_result=MapperResult(fields={"name": "T"}), dry_run=True)
    assert obj is None
    assert not Role.objects.filter(name="T").exists()
    assert IDMap.resolve("roles", "Role", "3") is None
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_writers_base.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/writers/base.py`:
```python
from django.apps import apps
from django.contrib.auth.models import Permission
from django.db import transaction

from migration.mappers.base import MapperResult, MissingFKError, require_fk
from migration.models import IDMap


class RowWriter:
    def __init__(self, *, app_label: str, model_name: str, target_model=None):
        self.app_label = app_label
        self.model_name = model_name
        self.target_model = target_model or apps.get_model(app_label, model_name)

    def write(self, *, old_pk, mapper_result: MapperResult, dry_run: bool = False):
        if mapper_result.skip:
            return None
        if dry_run:
            return None
        with transaction.atomic():
            existing_new_pk = IDMap.resolve(self.app_label, self.model_name, old_pk)
            if existing_new_pk:
                instance = self.target_model.objects.get(pk=existing_new_pk)
            else:
                instance = self.target_model()

            for fk_info in mapper_result.fk_resolutions:
                target_app, target_model, fk_old_pk, field_name = fk_info
                new_fk = require_fk(target_app, target_model, fk_old_pk, field_name=field_name)
                setattr(instance, f"{field_name}_id", new_fk)

            for fname, fvalue in mapper_result.fields.items():
                setattr(instance, fname, fvalue)
            instance.full_clean(exclude=self._exclude_for_clean(mapper_result))
            instance.save()

            for m2m_field, items in mapper_result.m2m_resolutions.items():
                self._apply_m2m(instance, m2m_field, items)

            IDMap.upsert(self.app_label, self.model_name, old_pk, instance.pk)
        return instance

    def _exclude_for_clean(self, result: MapperResult) -> list[str]:
        return list(result.m2m_resolutions.keys())

    def _apply_m2m(self, instance, field_name: str, items: list[tuple]) -> None:
        """For the foundation plan, the only M2M is roles.Role.permissions, which
        is keyed by (app_label, codename). Subclasses may override for other M2M.
        """
        if field_name == "permissions" and isinstance(instance, self.target_model):
            from roles.models import Role as RoleModel
            if isinstance(instance, RoleModel):
                qs = Permission.objects.none()
                for app_label, codename in items:
                    qs = qs | Permission.objects.filter(content_type__app_label=app_label, codename=codename)
                instance.permissions.set(qs.distinct())
                return
        raise NotImplementedError(f"No M2M handler for {field_name} on {self.target_model.__name__}")
```

- [ ] **Step 4: Update `writers/__init__.py`**

```python
from .base import RowWriter

__all__ = ["RowWriter"]
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_writers_base.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add migration/writers/ migration/tests/test_writers_base.py
git commit -m "feat(migration): idempotent RowWriter with IDMap upsert + codename M2M"
```

---

## Phase C — Celery tasks and end-to-end run

### Task 18: `migrate_model_batch` Celery task

**Files:**
- Create: `NEW/migration/tasks/batch.py`
- Modify: `NEW/migration/tasks/__init__.py`
- Create: `NEW/migration/tests/test_tasks_batch.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_tasks_batch.py`:
```python
import pytest
import responses
from django.test import override_settings

from migration.mappers.base import MissingFKError
from migration.models import IDMap, MigrationErrorRecord, MigrationJob, MigrationRunLog
from migration.tasks.batch import migrate_model_batch
from roles.models import Role


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")


def _page(results, next_cursor=None, has_more=False, total=None):
    return {
        "results": results,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total_estimated": total if total is not None else len(results),
    }


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_writes_rows_and_advances_cursor(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([{"id": 1, "name": "Teacher", "permissions": [],
                               "created_at": None, "updated_at": None}],
                             next_cursor="1", has_more=True, total=2),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    job.refresh_from_db()
    assert job.rows_written == 1
    assert job.last_cursor == "1"
    assert Role.objects.filter(name="Teacher").exists()
    assert IDMap.resolve("roles", "Role", "1") is not None


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_completes_job_when_no_next_cursor(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([], next_cursor=None, has_more=False, total=0),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    job.refresh_from_db()
    assert job.status == "completed"


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_paused_job_returns_early(job):
    job.status = "paused"
    job.save()
    migrate_model_batch.run(job_id=job.id)
    assert len(responses.calls) == 0


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_mapper_error_recorded_with_source_info(job, monkeypatch):
    from migration.mappers import roles_role as mod

    def boom(payload):
        raise ValueError("mapper exploded")
    monkeypatch.setattr(mod, "map_role", boom)
    # Re-register
    from migration.mappers.base import _REGISTRY
    _REGISTRY[("roles", "Role")] = boom

    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([{"id": 1, "name": "Teacher", "permissions": []}],
                             next_cursor=None, has_more=False, total=1),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    err = MigrationErrorRecord.objects.get()
    assert err.category == "mapper_error"
    assert err.old_pk == "1"
    assert err.source_file  # populated by error_capture
    job.refresh_from_db()
    assert job.rows_errored == 1


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_auth_error_pauses_job(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=401)
    migrate_model_batch.run(job_id=job.id)
    job.refresh_from_db()
    assert job.status == "paused"
    assert MigrationErrorRecord.objects.filter(category="auth_error").exists()


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_writes_run_log_entry(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([{"id": 1, "name": "T", "permissions": [],
                               "created_at": None, "updated_at": None}],
                             next_cursor=None, has_more=False, total=1),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    log = MigrationRunLog.objects.get()
    assert log.job_id == job.id
    assert log.rows_in_page == 1
    assert log.rows_written == 1
    assert log.http_status == 200
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_tasks_batch.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/tasks/batch.py`:
```python
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from celery import shared_task

from migration.client.exceptions import AuthError, MigrationClientError, PermanentError, ThrottledError, TransientError
from migration.client.http import OldLmsClient
from migration.mappers.base import MissingFKError, get_mapper
from migration.models import MigrationJob, MigrationRunLog
from migration.services.error_capture import capture
from migration.writers.base import RowWriter

logger = logging.getLogger(__name__)


@shared_task(name="migration.tasks.migrate_model_batch")
def migrate_model_batch(job_id: int) -> dict:
    job = MigrationJob.objects.get(pk=job_id)
    if job.status not in ("pending", "running"):
        logger.info("Job %s status=%s, skipping batch", job_id, job.status)
        return {"skipped": True, "status": job.status}

    if job.started_at is None:
        job.started_at = timezone.now()
    job.status = "running"
    job.save(update_fields=["status", "started_at", "updated_at"])

    client = OldLmsClient()
    run_log = MigrationRunLog.objects.create(
        job=job,
        cursor_in=job.last_cursor,
        is_dry_run=bool(getattr(settings, "MIGRATION_DRY_RUN", False) or job.dry_run),
    )

    try:
        page = client.fetch_page(
            job.app_label, _model_url(job.model_name),
            cursor=job.last_cursor or None,
            limit=settings.MIGRATION_BATCH_SIZE,
        )
        run_log.http_status = 200
    except AuthError as exc:
        capture(job=job, category="auth_error", exc=exc, run_log=run_log)
        job.status = "paused"
        job.save(update_fields=["status", "updated_at"])
        run_log.http_status = 401
        _finalize_log(run_log)
        return {"paused": True}
    except ThrottledError as exc:
        capture(job=job, category="throttled", exc=exc, run_log=run_log)
        run_log.http_status = 429
        run_log.notes = f"retry_after={exc.retry_after}"
        _finalize_log(run_log)
        return {"throttled": True, "retry_after": exc.retry_after}
    except (TransientError, PermanentError, MigrationClientError) as exc:
        capture(job=job, category="transport_error", exc=exc, run_log=run_log)
        run_log.http_status = 0
        _finalize_log(run_log)
        return {"error": "transport"}

    results = page.get("results", [])
    job.total_estimated = page.get("total_estimated", job.total_estimated)
    job.rows_fetched += len(results)
    run_log.rows_in_page = len(results)

    mapper = get_mapper(job.app_label, job.model_name)
    writer = RowWriter(app_label=job.app_label, model_name=job.model_name)
    dry_run = run_log.is_dry_run

    for idx, payload in enumerate(results):
        old_pk = str(payload.get("id", ""))
        try:
            result = mapper(payload)
            writer.write(old_pk=old_pk, mapper_result=result, dry_run=dry_run)
            run_log.rows_written += 1
            job.rows_written += 1
        except MissingFKError as exc:
            capture(job=job, category="missing_fk", exc=exc,
                    payload=payload, old_pk=old_pk,
                    batch_cursor=job.last_cursor, batch_index=idx,
                    field=exc.field_name,
                    expected=f"IDMap {exc.target_app}.{exc.target_model} old_pk={exc.old_pk}",
                    actual="not found", run_log=run_log)
            run_log.rows_errored += 1
            job.rows_errored += 1
        except Exception as exc:
            category = _categorize(exc)
            capture(job=job, category=category, exc=exc,
                    payload=payload, old_pk=old_pk,
                    batch_cursor=job.last_cursor, batch_index=idx,
                    run_log=run_log)
            run_log.rows_errored += 1
            job.rows_errored += 1

    next_cursor = page.get("next_cursor")
    if next_cursor:
        job.last_cursor = str(next_cursor)
    else:
        job.status = "completed"
        job.completed_at = timezone.now()

    run_log.cursor_out = job.last_cursor or ""
    _finalize_log(run_log)
    job.save()
    return {
        "ok": True,
        "rows_written": run_log.rows_written,
        "rows_errored": run_log.rows_errored,
        "next_cursor": next_cursor,
    }


def _finalize_log(run_log: MigrationRunLog) -> None:
    run_log.finished_at = timezone.now()
    run_log.save()


def _model_url(model_name: str) -> str:
    """Convert PascalCase model name to kebab-case path segment.

    Role -> role; StudentActivity -> student-activity.
    """
    out = []
    for i, ch in enumerate(model_name):
        if ch.isupper() and i > 0:
            out.append("-")
        out.append(ch.lower())
    return "".join(out)


def _categorize(exc: Exception) -> str:
    from django.core.exceptions import ValidationError
    from django.db import DataError, IntegrityError

    if isinstance(exc, ValidationError):
        return "validation"
    if isinstance(exc, (IntegrityError, DataError)):
        return "db_error"
    return "mapper_error"
```

- [ ] **Step 4: Update `tasks/__init__.py`**

```python
from .batch import migrate_model_batch

__all__ = ["migrate_model_batch"]
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_tasks_batch.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add migration/tasks/batch.py migration/tasks/__init__.py migration/tests/test_tasks_batch.py
git commit -m "feat(migration): migrate_model_batch task with per-row error capture"
```

---

### Task 19: Orchestrator and beat schedule

**Files:**
- Create: `NEW/migration/tasks/pipeline.py`
- Modify: `NEW/migration/tasks/__init__.py`
- Modify: `NEW/lms/celery.py` (only if beat schedule is added there)
- Create: `NEW/migration/tests/test_tasks_pipeline.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_tasks_pipeline.py`:
```python
from unittest.mock import patch

import pytest
from django.test import override_settings

from migration.models import MigrationJob
from migration.tasks.pipeline import DEPENDENCY_ORDER, run_migration_pipeline


def test_dependency_order_starts_with_roles_role():
    assert DEPENDENCY_ORDER[0] == ("roles", "Role")


@override_settings(MIGRATION_ENABLED=True)
def test_run_pipeline_creates_missing_jobs():
    assert MigrationJob.objects.count() == 0
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    assert MigrationJob.objects.filter(app_label="roles", model_name="Role").exists()
    m.assert_called()


@override_settings(MIGRATION_ENABLED=False)
def test_run_pipeline_noop_when_disabled():
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    m.assert_not_called()


@override_settings(MIGRATION_ENABLED=True)
def test_run_pipeline_skips_completed_jobs():
    MigrationJob.objects.create(app_label="roles", model_name="Role", status="completed")
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    m.assert_not_called()


@override_settings(MIGRATION_ENABLED=True)
def test_run_pipeline_skips_paused_jobs():
    MigrationJob.objects.create(app_label="roles", model_name="Role", status="paused")
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    m.assert_not_called()
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_tasks_pipeline.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/tasks/pipeline.py`:
```python
import logging

from celery import shared_task
from django.conf import settings

from migration.models import MigrationJob
from .batch import migrate_model_batch

logger = logging.getLogger(__name__)

DEPENDENCY_ORDER: list[tuple[str, str]] = [
    ("roles", "Role"),
    # Future plans append accounts.CustomUser, classroom.*, etc. here.
]


@shared_task(name="migration.tasks.run_migration_pipeline")
def run_migration_pipeline() -> dict:
    if not getattr(settings, "MIGRATION_ENABLED", False):
        return {"enabled": False}

    enqueued = []
    for app_label, model_name in DEPENDENCY_ORDER:
        job, _ = MigrationJob.objects.get_or_create(app_label=app_label, model_name=model_name)
        if job.status in ("pending", "running"):
            migrate_model_batch.delay(job_id=job.id)
            enqueued.append(job.id)
    return {"enabled": True, "enqueued_job_ids": enqueued}
```

- [ ] **Step 4: Update `tasks/__init__.py`**

```python
from .batch import migrate_model_batch
from .pipeline import DEPENDENCY_ORDER, run_migration_pipeline

__all__ = ["migrate_model_batch", "run_migration_pipeline", "DEPENDENCY_ORDER"]
```

- [ ] **Step 5: Register beat schedule**

In `NEW/lms/celery.py`, append (preserving existing config):

```python
from celery.schedules import schedule
from django.conf import settings

app.conf.beat_schedule = {
    **getattr(app.conf, "beat_schedule", {}),
    "migration-pipeline-tick": {
        "task": "migration.tasks.run_migration_pipeline",
        "schedule": schedule(run_every=int(getattr(settings, "MIGRATION_BATCH_INTERVAL_SECONDS", 30))),
    },
}
```

If `beat_schedule` is already configured elsewhere (e.g., via `django-celery-beat` DB schedules), instead document that operators add the entry through admin. For this plan we assume in-code schedule.

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest migration/tests/test_tasks_pipeline.py -v
```
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add migration/tasks/pipeline.py migration/tasks/__init__.py lms/celery.py migration/tests/test_tasks_pipeline.py
git commit -m "feat(migration): pipeline orchestrator + Celery beat schedule"
```

---

### Task 20: Verification task

**Files:**
- Create: `NEW/migration/tasks/verify.py`
- Modify: `NEW/migration/tasks/__init__.py`
- Create: `NEW/migration/tests/test_tasks_verify.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_tasks_verify.py`:
```python
import pytest
import responses
from django.test import override_settings

from migration.models import IDMap, MigrationJob
from migration.tasks.verify import verify_migration
from roles.models import Role


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="completed")


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_verify_matches_counts_when_equal(job):
    Role.objects.create(name="A")
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk=str(Role.objects.first().pk))
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": [], "next_cursor": None, "has_more": False, "total_estimated": 1},
                  status=200)
    report = verify_migration.run(job_id=job.id)
    assert report["count_parity"] is True
    assert report["old_count"] == 1
    assert report["new_count"] == 1


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_verify_flags_count_mismatch(job):
    Role.objects.create(name="A")
    Role.objects.create(name="B")
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk="1")
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="2", new_pk="2")
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": [], "next_cursor": None, "has_more": False, "total_estimated": 5},
                  status=200)
    report = verify_migration.run(job_id=job.id)
    assert report["count_parity"] is False
    assert report["old_count"] == 5
    assert report["new_count"] == 2


def test_verify_persists_report_on_job(job):
    Role.objects.create(name="A")
    with responses.RequestsMock() as rsps:
        rsps.add(rsps.GET, "http://old/api/migration/roles/role/",
                 json={"results": [], "next_cursor": None, "has_more": False, "total_estimated": 1},
                 status=200)
        with override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t"):
            verify_migration.run(job_id=job.id)
    job.refresh_from_db()
    assert "old_count" in job.last_verification
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_tasks_verify.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/tasks/verify.py`:
```python
from celery import shared_task
from django.apps import apps

from migration.client.http import OldLmsClient
from migration.models import IDMap, MigrationJob
from migration.tasks.batch import _model_url


@shared_task(name="migration.tasks.verify_migration")
def verify_migration(job_id: int) -> dict:
    job = MigrationJob.objects.get(pk=job_id)
    target_model = apps.get_model(job.app_label, job.model_name)

    client = OldLmsClient()
    head = client.fetch_page(job.app_label, _model_url(job.model_name), limit=1)
    old_count = int(head.get("total_estimated", 0))

    new_count = target_model.objects.count()
    idmap_count = IDMap.objects.filter(app_label=job.app_label, model_name=job.model_name).count()

    report = {
        "old_count": old_count,
        "new_count": new_count,
        "idmap_count": idmap_count,
        "count_parity": old_count == new_count,
        "idmap_complete": idmap_count == new_count,
    }
    job.last_verification = report
    job.save(update_fields=["last_verification", "updated_at"])
    return report
```

- [ ] **Step 4: Update `tasks/__init__.py`**

```python
from .batch import migrate_model_batch
from .pipeline import DEPENDENCY_ORDER, run_migration_pipeline
from .verify import verify_migration

__all__ = ["migrate_model_batch", "run_migration_pipeline", "verify_migration", "DEPENDENCY_ORDER"]
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_tasks_verify.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add migration/tasks/verify.py migration/tasks/__init__.py migration/tests/test_tasks_verify.py
git commit -m "feat(migration): verify_migration task with count + IDMap parity"
```

---

### Task 21: Retry task

**Files:**
- Create: `NEW/migration/tasks/retry.py`
- Modify: `NEW/migration/tasks/__init__.py`
- Create: `NEW/migration/tests/test_tasks_retry.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_tasks_retry.py`:
```python
import pytest
import responses
from django.test import override_settings

from migration.models import IDMap, MigrationErrorRecord, MigrationJob
from migration.tasks.retry import retry_single_row
from roles.models import Role


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_retry_fetches_single_row_and_writes(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/9/",
                  json={"id": 9, "name": "Solo", "permissions": [],
                        "created_at": None, "updated_at": None}, status=200)
    retry_single_row.run(job_id=job.id, old_pk="9")
    assert Role.objects.filter(name="Solo").exists()
    assert IDMap.resolve("roles", "Role", "9") is not None


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_retry_marks_matching_errors_resolved(job):
    err = MigrationErrorRecord.objects.create(
        job=job, category="mapper_error", message="x",
        old_app="roles", old_model="Role", old_pk="9",
    )
    responses.add(responses.GET, "http://old/api/migration/roles/role/9/",
                  json={"id": 9, "name": "Solo", "permissions": [],
                        "created_at": None, "updated_at": None}, status=200)
    retry_single_row.run(job_id=job.id, old_pk="9")
    err.refresh_from_db()
    assert err.resolved is True


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_retry_records_new_error_on_failure(job, monkeypatch):
    from migration.mappers.base import _REGISTRY
    _REGISTRY[("roles", "Role")] = lambda p: (_ for _ in ()).throw(ValueError("boom"))
    responses.add(responses.GET, "http://old/api/migration/roles/role/9/",
                  json={"id": 9, "name": "X", "permissions": []}, status=200)
    retry_single_row.run(job_id=job.id, old_pk="9")
    # Restore registered mapper for downstream tests
    from migration.mappers.roles_role import map_role
    _REGISTRY[("roles", "Role")] = map_role
    assert MigrationErrorRecord.objects.filter(category="mapper_error").exists()
```

- [ ] **Step 2: Run, expect ImportError**

```bash
pytest migration/tests/test_tasks_retry.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/tasks/retry.py`:
```python
from celery import shared_task
from django.utils import timezone

from migration.client.http import OldLmsClient
from migration.mappers.base import MissingFKError, get_mapper
from migration.models import MigrationErrorRecord, MigrationJob
from migration.services.error_capture import capture
from migration.tasks.batch import _categorize, _model_url
from migration.writers.base import RowWriter


@shared_task(name="migration.tasks.retry_single_row")
def retry_single_row(job_id: int, old_pk: str) -> dict:
    job = MigrationJob.objects.get(pk=job_id)
    client = OldLmsClient()
    mapper = get_mapper(job.app_label, job.model_name)
    writer = RowWriter(app_label=job.app_label, model_name=job.model_name)

    try:
        payload = client.fetch_by_pk(job.app_label, _model_url(job.model_name), old_pk)
    except Exception as exc:
        capture(job=job, category="transport_error", exc=exc, old_pk=old_pk)
        return {"ok": False, "stage": "fetch"}

    try:
        result = mapper(payload)
        writer.write(old_pk=str(old_pk), mapper_result=result, dry_run=False)
    except MissingFKError as exc:
        capture(job=job, category="missing_fk", exc=exc, payload=payload, old_pk=str(old_pk),
                field=exc.field_name,
                expected=f"IDMap {exc.target_app}.{exc.target_model} old_pk={exc.old_pk}",
                actual="not found")
        return {"ok": False, "stage": "fk"}
    except Exception as exc:
        capture(job=job, category=_categorize(exc), exc=exc, payload=payload, old_pk=str(old_pk))
        return {"ok": False, "stage": "write"}

    MigrationErrorRecord.objects.filter(
        job=job, old_pk=str(old_pk), resolved=False,
    ).update(resolved=True, resolved_at=timezone.now(), resolution_note="resolved via retry_single_row")
    return {"ok": True}
```

- [ ] **Step 4: Update `tasks/__init__.py`**

```python
from .batch import migrate_model_batch
from .pipeline import DEPENDENCY_ORDER, run_migration_pipeline
from .retry import retry_single_row
from .verify import verify_migration

__all__ = ["migrate_model_batch", "run_migration_pipeline", "verify_migration",
           "retry_single_row", "DEPENDENCY_ORDER"]
```

- [ ] **Step 5: Run, expect pass**

```bash
pytest migration/tests/test_tasks_retry.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add migration/tasks/retry.py migration/tasks/__init__.py migration/tests/test_tasks_retry.py
git commit -m "feat(migration): retry_single_row task with auto-resolve of matching errors"
```

---

### Task 22: End-to-end test against a live old-side process

**Files:**
- Create: `NEW/migration/tests/test_e2e_roles_role.py`

This test uses the **real** simulation server. It is opt-in via env var to keep CI deterministic.

- [ ] **Step 1: Write the test**

`NEW/migration/tests/test_e2e_roles_role.py`:
```python
import os

import pytest

from migration.models import IDMap, MigrationJob
from migration.tasks.batch import migrate_model_batch
from migration.tasks.verify import verify_migration
from roles.models import Role

pytestmark = pytest.mark.skipif(
    os.environ.get("MIGRATION_E2E") != "1",
    reason="E2E test requires running simulation server and MIGRATION_E2E=1",
)


def test_full_role_migration_end_to_end(settings):
    settings.MIGRATION_OLD_LMS_BASE_URL = os.environ["MIGRATION_OLD_LMS_BASE_URL"]
    settings.MIGRATION_OLD_LMS_TOKEN = os.environ["MIGRATION_OLD_LMS_TOKEN"]
    settings.MIGRATION_BATCH_SIZE = 500

    job = MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")
    # Drain pages until completion or 50 batches (safety).
    for _ in range(50):
        migrate_model_batch.run(job_id=job.id)
        job.refresh_from_db()
        if job.status == "completed":
            break

    assert job.status == "completed"
    new_count = Role.objects.count()
    assert new_count > 0
    assert IDMap.objects.filter(app_label="roles", model_name="Role").count() == new_count

    report = verify_migration.run(job_id=job.id)
    assert report["count_parity"] is True
```

- [ ] **Step 2: Run the E2E test manually (developer machine)**

In one terminal, start the simulation server (`Task 9` style):
```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py runserver 0.0.0.0:8001
```

In a second terminal, with a fresh token (`Task 9` step 1):
```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
MIGRATION_E2E=1 \
MIGRATION_OLD_LMS_BASE_URL=http://localhost:8001 \
MIGRATION_OLD_LMS_TOKEN=<paste> \
pytest migration/tests/test_e2e_roles_role.py -v
```
Expected: PASS. If it fails, capture the `MigrationErrorRecord` rows: `python manage.py shell -c "from migration.models import MigrationErrorRecord; [print(e.category, e.source_file, e.source_line, e.message) for e in MigrationErrorRecord.objects.all()]"`.

- [ ] **Step 3: Idempotency check**

Re-run the same command. Expected: PASS. New role count unchanged. `MigrationErrorRecord.objects.count()` unchanged.

- [ ] **Step 4: Resume check**

Reset:
```bash
python manage.py shell -c "from migration.models import *; MigrationJob.objects.all().delete(); IDMap.objects.all().delete(); MigrationErrorRecord.objects.all().delete(); from roles.models import Role; Role.objects.all().delete()"
```
Run the test with `MIGRATION_BATCH_SIZE=1` so each batch covers exactly one row. Kill the process after the second batch (Ctrl-C). Resume by re-running the test. Confirm via shell that `MigrationJob.last_cursor` advanced past the killed batch and final count is correct.

- [ ] **Step 5: Commit**

```bash
git add migration/tests/test_e2e_roles_role.py
git commit -m "test(migration): opt-in E2E for roles.Role end-to-end migration"
```

---

## Phase D — Dashboard

### Task 23: URL routing and base template

**Files:**
- Modify: `NEW/migration/urls.py`
- Create: `NEW/migration/templates/migration/base.html`
- Create: `NEW/migration/static/migration/migration.css`

- [ ] **Step 1: Write `migration/templates/migration/base.html`**

```html
{% extends "base_operation.html" %}
{% load static %}

{% block operations_title %}Data Migration{% endblock %}

{% block operations_extra_head %}
  <link rel="stylesheet" href="{% static 'migration/migration.css' %}">
  <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
{% endblock %}

{% block operations_content %}
  <div class="migration-shell"
       data-poll-seconds="{{ poll_seconds|default:3 }}"
       data-dry-run="{{ dry_run|yesno:'true,false' }}">
    <header class="migration-header">
      <div>
        <strong>Source:</strong> {{ old_lms_base_url }}
        &middot;
        <strong>Token:</strong> {{ token_label|default:"(unset)" }}
        &middot;
        <strong>Last health:</strong> <span id="last-health">{{ last_health|default:"never" }}</span>
      </div>
      <nav>
        <a href="{% url 'migration:overview' %}">Overview</a>
        <a href="{% url 'migration:errors' %}">Errors</a>
      </nav>
    </header>
    <main>{% block migration_content %}{% endblock %}</main>
  </div>
{% endblock %}
```

If `base_operation.html` does not define blocks named `operations_title`, `operations_extra_head`, or `operations_content`, inspect it and adjust block names accordingly. (Tooling note: run `grep "block" templates/base_operation.html` before this task.)

- [ ] **Step 2: Write `migration/static/migration/migration.css`**

```css
.migration-shell { font-family: system-ui, sans-serif; padding: 1rem; }
.migration-header { display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0; border-bottom:1px solid #eee; margin-bottom:1rem; }
.migration-header nav a { margin-left: 1rem; }
.migration-table { width: 100%; border-collapse: collapse; }
.migration-table th, .migration-table td { padding: 0.5rem; border-bottom: 1px solid #eee; text-align:left; }
.status-pill { padding: 2px 8px; border-radius: 12px; font-size: 0.85em; }
.status-pending { background:#eee; }
.status-running { background:#cfe; }
.status-paused { background:#ffe; }
.status-completed { background:#dfd; }
.status-failed { background:#fdd; }
.progress { background:#eee; height:8px; border-radius:4px; overflow:hidden; }
.progress > div { background:#39c; height:100%; }
.error-badge { background:#c33; color:#fff; padding:1px 6px; border-radius:8px; font-size:0.75em; }
.drawer { border:1px solid #ddd; padding:1rem; margin-top:1rem; background:#fafafa; }
.drawer pre { white-space: pre-wrap; word-break: break-all; }
```

- [ ] **Step 3: Update `migration/urls.py`**

```python
from django.urls import path

from .views import actions, errors, job_detail, overview

app_name = "migration"

urlpatterns = [
    path("", overview.OverviewView.as_view(), name="overview"),
    path("rows/", overview.JobRowsFragment.as_view(), name="overview-rows"),
    path("job/<int:pk>/", job_detail.JobDetailView.as_view(), name="job-detail"),
    path("job/<int:pk>/fragment/", job_detail.JobDetailFragment.as_view(), name="job-detail-fragment"),
    path("errors/", errors.ErrorsView.as_view(), name="errors"),
    path("errors/<int:pk>/", errors.ErrorDetailView.as_view(), name="error-detail"),
    # Actions
    path("actions/start/", actions.StartPipelineView.as_view(), name="action-start"),
    path("actions/pause-all/", actions.PauseAllView.as_view(), name="action-pause-all"),
    path("actions/resume-all/", actions.ResumeAllView.as_view(), name="action-resume-all"),
    path("actions/toggle-dry-run/", actions.ToggleDryRunView.as_view(), name="action-toggle-dry-run"),
    path("actions/job/<int:pk>/pause/", actions.PauseJobView.as_view(), name="action-job-pause"),
    path("actions/job/<int:pk>/resume/", actions.ResumeJobView.as_view(), name="action-job-resume"),
    path("actions/job/<int:pk>/restart/", actions.RestartJobView.as_view(), name="action-job-restart"),
    path("actions/job/<int:pk>/verify/", actions.VerifyJobView.as_view(), name="action-job-verify"),
    path("actions/errors/<int:pk>/retry/", actions.RetryErrorView.as_view(), name="action-error-retry"),
    path("actions/errors/<int:pk>/resolve/", actions.ResolveErrorView.as_view(), name="action-error-resolve"),
]
```

- [ ] **Step 4: Commit (views will be created in next tasks; URLs reference them)**

Skipping `manage.py check` here because views.py is empty — defer to Task 24 step 1 boot.

```bash
git add migration/urls.py migration/templates/migration/base.html migration/static/migration/migration.css
git commit -m "feat(migration): URL routing, base template, dashboard styles"
```

---

### Task 24: Overview view + job row fragment

**Files:**
- Create: `NEW/migration/views/overview.py`
- Create: `NEW/migration/templates/migration/overview.html`
- Create: `NEW/migration/templates/migration/_job_row.html`
- Create: `NEW/migration/services/progress.py`
- Create: `NEW/migration/tests/test_views_overview.py`

- [ ] **Step 1: Implement `services/progress.py`**

```python
from datetime import timedelta
from django.utils import timezone

from migration.models import MigrationJob, MigrationRunLog


def rows_per_minute(job: MigrationJob, *, window_logs: int = 5) -> float:
    logs = list(MigrationRunLog.objects.filter(job=job, finished_at__isnull=False).order_by("-finished_at")[:window_logs])
    if len(logs) < 2:
        return 0.0
    earliest = logs[-1].started_at
    latest = logs[0].finished_at
    span_seconds = max((latest - earliest).total_seconds(), 1.0)
    rows = sum(l.rows_written for l in logs)
    return (rows / span_seconds) * 60.0


def eta_seconds(job: MigrationJob) -> int | None:
    if job.total_estimated <= 0:
        return None
    remaining = max(job.total_estimated - job.rows_written, 0)
    if remaining == 0:
        return 0
    rpm = rows_per_minute(job)
    if rpm <= 0:
        return None
    return int((remaining / rpm) * 60)
```

- [ ] **Step 2: Implement `views/overview.py`**

```python
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView, ListView

from migration.models import MigrationJob
from migration.services.progress import eta_seconds, rows_per_minute


class _SuperuserOnly(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser


def _augment(jobs):
    return [
        {
            "job": j,
            "rpm": round(rows_per_minute(j), 1),
            "eta": eta_seconds(j),
            "error_count": j.errors.filter(resolved=False).count(),
            "percent": (int((j.rows_written / j.total_estimated) * 100) if j.total_estimated else 0),
        }
        for j in jobs
    ]


class OverviewView(_SuperuserOnly, TemplateView):
    template_name = "migration/overview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["jobs"] = _augment(MigrationJob.objects.all())
        ctx["old_lms_base_url"] = settings.MIGRATION_OLD_LMS_BASE_URL
        ctx["poll_seconds"] = settings.MIGRATION_DASHBOARD_POLL_SECONDS
        ctx["dry_run"] = settings.MIGRATION_DRY_RUN
        return ctx


class JobRowsFragment(_SuperuserOnly, TemplateView):
    template_name = "migration/_job_row.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["jobs"] = _augment(MigrationJob.objects.all())
        return ctx
```

- [ ] **Step 3: Write `templates/migration/overview.html`**

```html
{% extends "migration/base.html" %}

{% block migration_content %}
<form method="post" action="{% url 'migration:action-start' %}" style="display:inline">{% csrf_token %}<button type="submit">Start pipeline</button></form>
<form method="post" action="{% url 'migration:action-pause-all' %}" style="display:inline">{% csrf_token %}<button type="submit">Pause all</button></form>
<form method="post" action="{% url 'migration:action-resume-all' %}" style="display:inline">{% csrf_token %}<button type="submit">Resume all</button></form>
<form method="post" action="{% url 'migration:action-toggle-dry-run' %}" style="display:inline">{% csrf_token %}<button type="submit">Toggle dry-run ({{ dry_run|yesno:"on,off" }})</button></form>

<table class="migration-table"
       hx-get="{% url 'migration:overview-rows' %}"
       hx-trigger="every {{ poll_seconds }}s"
       hx-target="this"
       hx-select="tbody"
       hx-swap="outerHTML">
  <thead>
    <tr>
      <th>App.Model</th><th>Status</th><th>Progress</th>
      <th>Rows</th><th>Rate /min</th><th>ETA s</th><th>Errors</th><th>Actions</th>
    </tr>
  </thead>
  {% include "migration/_job_row.html" %}
</table>
{% endblock %}
```

- [ ] **Step 4: Write `templates/migration/_job_row.html`**

```html
<tbody>
{% for row in jobs %}
  {% with j=row.job %}
  <tr>
    <td>{{ j.app_label }}.{{ j.model_name }}</td>
    <td><span class="status-pill status-{{ j.status }}">{{ j.status }}</span></td>
    <td><div class="progress"><div style="width:{{ row.percent }}%"></div></div> {{ row.percent }}%</td>
    <td>{{ j.rows_written }}/{{ j.total_estimated }}</td>
    <td>{{ row.rpm }}</td>
    <td>{{ row.eta|default:"-" }}</td>
    <td>{% if row.error_count %}<a href="{% url 'migration:errors' %}?job={{ j.id }}"><span class="error-badge">{{ row.error_count }}</span></a>{% else %}0{% endif %}</td>
    <td>
      <a href="{% url 'migration:job-detail' j.id %}">Detail</a>
      <form method="post" action="{% url 'migration:action-job-pause' j.id %}" style="display:inline">{% csrf_token %}<button>Pause</button></form>
      <form method="post" action="{% url 'migration:action-job-resume' j.id %}" style="display:inline">{% csrf_token %}<button>Resume</button></form>
      <form method="post" action="{% url 'migration:action-job-verify' j.id %}" style="display:inline">{% csrf_token %}<button>Verify</button></form>
    </td>
  </tr>
  {% endwith %}
{% empty %}
  <tr><td colspan="8">No migration jobs yet — click <em>Start pipeline</em> to create them.</td></tr>
{% endfor %}
</tbody>
```

- [ ] **Step 5: Write failing tests**

`NEW/migration/tests/test_views_overview.py`:
```python
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from migration.models import MigrationJob

User = get_user_model()


@pytest.fixture
def super_client():
    u = User.objects.create_superuser(username="root", email="r@r", password="pw")
    c = Client()
    c.force_login(u)
    return c


def test_overview_requires_superuser():
    c = Client()
    r = c.get("/operations/migration/")
    assert r.status_code in (302, 403)


def test_overview_renders_job_rows(super_client):
    MigrationJob.objects.create(app_label="roles", model_name="Role", rows_written=3, total_estimated=10)
    r = super_client.get("/operations/migration/")
    assert r.status_code == 200
    assert b"roles" in r.content.lower()
    assert b"Role" in r.content


def test_rows_fragment_returns_tbody(super_client):
    MigrationJob.objects.create(app_label="roles", model_name="Role")
    r = super_client.get("/operations/migration/rows/")
    assert r.status_code == 200
    assert b"<tbody" in r.content
```

- [ ] **Step 6: Run, expect pass**

```bash
pytest migration/tests/test_views_overview.py -v
```
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add migration/views/overview.py migration/templates/migration/overview.html migration/templates/migration/_job_row.html migration/services/progress.py migration/tests/test_views_overview.py
git commit -m "feat(migration): dashboard overview screen with HTMX polling"
```

---

### Task 25: Job detail view + run-log tail

**Files:**
- Create: `NEW/migration/views/job_detail.py`
- Create: `NEW/migration/templates/migration/job_detail.html`
- Create: `NEW/migration/templates/migration/_run_log_tail.html`

- [ ] **Step 1: Implement view**

`NEW/migration/views/job_detail.py`:
```python
from django.views.generic import TemplateView

from migration.models import MigrationJob, MigrationRunLog
from .overview import _SuperuserOnly


class JobDetailView(_SuperuserOnly, TemplateView):
    template_name = "migration/job_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = MigrationJob.objects.get(pk=kwargs["pk"])
        ctx["job"] = job
        ctx["logs"] = MigrationRunLog.objects.filter(job=job)[:50]
        ctx["recent_errors"] = job.errors.all()[:10]
        return ctx


class JobDetailFragment(_SuperuserOnly, TemplateView):
    template_name = "migration/_run_log_tail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = MigrationJob.objects.get(pk=kwargs["pk"])
        ctx["job"] = job
        ctx["logs"] = MigrationRunLog.objects.filter(job=job)[:50]
        return ctx
```

- [ ] **Step 2: Write `templates/migration/job_detail.html`**

```html
{% extends "migration/base.html" %}

{% block migration_content %}
<h2>{{ job.app_label }}.{{ job.model_name }} — {{ job.status }}</h2>
<dl>
  <dt>Cursor</dt><dd>{{ job.last_cursor|default:"-" }}</dd>
  <dt>Rows written</dt><dd>{{ job.rows_written }} / {{ job.total_estimated }}</dd>
  <dt>Errored</dt><dd>{{ job.rows_errored }}</dd>
  <dt>Skipped</dt><dd>{{ job.rows_skipped }}</dd>
  <dt>Started</dt><dd>{{ job.started_at|default:"-" }}</dd>
  <dt>Completed</dt><dd>{{ job.completed_at|default:"-" }}</dd>
</dl>

<h3>Recent run logs</h3>
<div hx-get="{% url 'migration:job-detail-fragment' job.id %}"
     hx-trigger="every 3s"
     hx-swap="innerHTML">
  {% include "migration/_run_log_tail.html" %}
</div>

<h3>Recent errors</h3>
<ul>
{% for e in recent_errors %}
<li><a href="{% url 'migration:error-detail' e.id %}">{{ e.occurred_at }} {{ e.category }} pk={{ e.old_pk }} — {{ e.message }}</a></li>
{% empty %}<li>None</li>{% endfor %}
</ul>
{% endblock %}
```

- [ ] **Step 3: Write `templates/migration/_run_log_tail.html`**

```html
<table class="migration-table">
  <thead><tr><th>Started</th><th>Finished</th><th>cursor in→out</th><th>page</th><th>written</th><th>err</th><th>http</th><th>note</th></tr></thead>
  <tbody>
  {% for l in logs %}
  <tr>
    <td>{{ l.started_at|date:"H:i:s" }}</td>
    <td>{{ l.finished_at|date:"H:i:s"|default:"…" }}</td>
    <td>{{ l.cursor_in|default:"∅" }} → {{ l.cursor_out|default:"∅" }}</td>
    <td>{{ l.rows_in_page }}</td>
    <td>{{ l.rows_written }}</td>
    <td>{{ l.rows_errored }}</td>
    <td>{{ l.http_status|default:"-" }}</td>
    <td>{{ l.notes }}</td>
  </tr>
  {% empty %}<tr><td colspan="8">No batches yet.</td></tr>{% endfor %}
  </tbody>
</table>
```

- [ ] **Step 4: Manual check**

```bash
python manage.py check
```
Expected: passes.

- [ ] **Step 5: Commit**

```bash
git add migration/views/job_detail.py migration/templates/migration/job_detail.html migration/templates/migration/_run_log_tail.html
git commit -m "feat(migration): job detail page with live run-log tail"
```

---

### Task 26: Error inspector + drawer

**Files:**
- Create: `NEW/migration/views/errors.py`
- Create: `NEW/migration/templates/migration/errors.html`
- Create: `NEW/migration/templates/migration/_error_drawer.html`
- Create: `NEW/migration/tests/test_views_errors.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_views_errors.py`:
```python
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from migration.models import MigrationErrorRecord, MigrationJob

User = get_user_model()


@pytest.fixture
def super_client():
    u = User.objects.create_superuser(username="root", email="r@r", password="pw")
    c = Client()
    c.force_login(u)
    return c


@pytest.fixture
def err():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    return MigrationErrorRecord.objects.create(
        job=job, category="mapper_error", message="boom",
        old_app="roles", old_model="Role", old_pk="7",
        source_file="/abs/path/migration/mappers/roles_role.py",
        source_line=243, source_function="map_role",
        payload_excerpt={"id": 7, "name": "X"},
    )


def test_errors_index_lists_records(super_client, err):
    r = super_client.get("/operations/migration/errors/")
    assert r.status_code == 200
    assert b"boom" in r.content


def test_error_detail_shows_source_line_and_vscode_link(super_client, err):
    r = super_client.get(f"/operations/migration/errors/{err.id}/")
    assert r.status_code == 200
    assert b"roles_role.py:243" in r.content
    assert b"vscode://file" in r.content
    assert b"map_role" in r.content


def test_errors_filter_by_category(super_client, err):
    r = super_client.get("/operations/migration/errors/?category=missing_fk")
    assert r.status_code == 200
    assert b"boom" not in r.content
```

- [ ] **Step 2: Run, expect 404 or ImportError**

```bash
pytest migration/tests/test_views_errors.py -v
```

- [ ] **Step 3: Implement views**

`NEW/migration/views/errors.py`:
```python
from django.views.generic import DetailView, ListView

from migration.models import MigrationErrorRecord
from .overview import _SuperuserOnly


class ErrorsView(_SuperuserOnly, ListView):
    template_name = "migration/errors.html"
    paginate_by = 50
    context_object_name = "errors"

    def get_queryset(self):
        qs = MigrationErrorRecord.objects.select_related("job").all()
        params = self.request.GET
        if params.get("job"):
            qs = qs.filter(job_id=params["job"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        if params.get("old_pk"):
            qs = qs.filter(old_pk=params["old_pk"])
        if params.get("resolved") == "true":
            qs = qs.filter(resolved=True)
        elif params.get("resolved") == "false":
            qs = qs.filter(resolved=False)
        return qs


class ErrorDetailView(_SuperuserOnly, DetailView):
    model = MigrationErrorRecord
    template_name = "migration/_error_drawer.html"
    context_object_name = "err"
```

- [ ] **Step 4: Write `templates/migration/errors.html`**

```html
{% extends "migration/base.html" %}

{% block migration_content %}
<form method="get">
  Category:
  <select name="category">
    <option value="">(any)</option>
    <option value="transport_error" {% if request.GET.category == 'transport_error' %}selected{% endif %}>transport_error</option>
    <option value="auth_error" {% if request.GET.category == 'auth_error' %}selected{% endif %}>auth_error</option>
    <option value="throttled" {% if request.GET.category == 'throttled' %}selected{% endif %}>throttled</option>
    <option value="mapper_error" {% if request.GET.category == 'mapper_error' %}selected{% endif %}>mapper_error</option>
    <option value="missing_fk" {% if request.GET.category == 'missing_fk' %}selected{% endif %}>missing_fk</option>
    <option value="validation" {% if request.GET.category == 'validation' %}selected{% endif %}>validation</option>
    <option value="db_error" {% if request.GET.category == 'db_error' %}selected{% endif %}>db_error</option>
    <option value="unknown" {% if request.GET.category == 'unknown' %}selected{% endif %}>unknown</option>
  </select>
  Old PK: <input name="old_pk" value="{{ request.GET.old_pk }}">
  Resolved:
  <select name="resolved">
    <option value="">(any)</option>
    <option value="false" {% if request.GET.resolved == 'false' %}selected{% endif %}>unresolved</option>
    <option value="true" {% if request.GET.resolved == 'true' %}selected{% endif %}>resolved</option>
  </select>
  <button>Filter</button>
</form>

<table class="migration-table">
  <thead><tr><th>When</th><th>Job</th><th>Cat</th><th>old_pk</th><th>Message</th><th>Source</th><th></th></tr></thead>
  <tbody>
  {% for e in errors %}
    <tr>
      <td>{{ e.occurred_at }}</td>
      <td>{{ e.job.app_label }}.{{ e.job.model_name }}</td>
      <td>{{ e.category }}</td>
      <td>{{ e.old_pk }}</td>
      <td>{{ e.message }}</td>
      <td>{% if e.source_file %}{{ e.source_file|cut:"/home/" }}:{{ e.source_line }}{% endif %}</td>
      <td><a href="{% url 'migration:error-detail' e.id %}">open</a></td>
    </tr>
  {% empty %}<tr><td colspan="7">No matching errors.</td></tr>{% endfor %}
  </tbody>
</table>

{% if is_paginated %}
  <p>Page {{ page_obj.number }} of {{ paginator.num_pages }}</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: Write `templates/migration/_error_drawer.html`**

```html
{% extends "migration/base.html" %}

{% block migration_content %}
<h2>Error #{{ err.id }} — {{ err.category }}</h2>
<div class="drawer">
  <p><strong>Job:</strong> {{ err.job.app_label }}.{{ err.job.model_name }} (#{{ err.job_id }})</p>
  <p><strong>Where in source data:</strong> old_pk={{ err.old_pk|default:"(none)" }} · batch_cursor={{ err.batch_cursor|default:"-" }} · index={{ err.batch_index|default:"-" }}</p>
  <p><strong>Summary:</strong> {{ err.message }}</p>
  {% if err.field %}<p><strong>Field:</strong> {{ err.field }}</p>{% endif %}
  {% if err.expected %}<p><strong>Expected:</strong> {{ err.expected }}</p>{% endif %}
  {% if err.actual %}<p><strong>Actual:</strong> {{ err.actual }}</p>{% endif %}

  <p><strong>Code:</strong>
    {% if err.source_file %}
      <code>{{ err.source_file }}:{{ err.source_line }}</code> in <code>{{ err.source_function }}</code>
      &nbsp;<a href="vscode://file{{ err.source_file }}:{{ err.source_line }}">open in VS Code</a>
    {% else %}(no source frame captured){% endif %}
  </p>

  <details><summary>Traceback</summary><pre>{{ err.traceback }}</pre></details>
  <details open><summary>Payload</summary><pre>{{ err.payload_excerpt|pprint }}</pre></details>

  <p><strong>Resolved:</strong> {{ err.resolved|yesno:"yes,no" }}{% if err.resolved_at %} ({{ err.resolved_at }}){% endif %}</p>
  {% if err.resolution_note %}<p><em>{{ err.resolution_note }}</em></p>{% endif %}

  <form method="post" action="{% url 'migration:action-error-retry' err.id %}" style="display:inline">{% csrf_token %}<button>Retry this row</button></form>
  <form method="post" action="{% url 'migration:action-error-resolve' err.id %}" style="display:inline">{% csrf_token %}<button>Mark resolved</button></form>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests, expect pass**

```bash
pytest migration/tests/test_views_errors.py -v
```
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add migration/views/errors.py migration/templates/migration/errors.html migration/templates/migration/_error_drawer.html migration/tests/test_views_errors.py
git commit -m "feat(migration): error inspector + drawer with vscode deep link"
```

---

### Task 27: Action endpoints (start/pause/resume/restart/verify/retry/resolve/dry-run)

**Files:**
- Create: `NEW/migration/views/actions.py`
- Create: `NEW/migration/tests/test_views_actions.py`

- [ ] **Step 1: Write failing tests**

`NEW/migration/tests/test_views_actions.py`:
```python
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from migration.models import MigrationErrorRecord, MigrationJob

User = get_user_model()


@pytest.fixture
def super_client():
    u = User.objects.create_superuser(username="root", email="r@r", password="pw")
    c = Client()
    c.force_login(u)
    return c


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="pending")


def test_pause_job(super_client, job):
    r = super_client.post(f"/operations/migration/actions/job/{job.id}/pause/")
    assert r.status_code in (200, 302)
    job.refresh_from_db()
    assert job.status == "paused"


def test_resume_job(super_client, job):
    job.status = "paused"; job.save()
    super_client.post(f"/operations/migration/actions/job/{job.id}/resume/")
    job.refresh_from_db()
    assert job.status == "running"


def test_restart_job_clears_cursor_and_counters(super_client, job):
    job.last_cursor = "42"; job.rows_written = 10; job.rows_errored = 2; job.status = "completed"; job.save()
    super_client.post(f"/operations/migration/actions/job/{job.id}/restart/", {"confirm": "yes"})
    job.refresh_from_db()
    assert job.last_cursor == ""
    assert job.rows_written == 0
    assert job.rows_errored == 0
    assert job.status == "pending"


def test_pause_all_and_resume_all(super_client):
    MigrationJob.objects.create(app_label="a", model_name="A", status="running")
    MigrationJob.objects.create(app_label="b", model_name="B", status="running")
    super_client.post("/operations/migration/actions/pause-all/")
    assert MigrationJob.objects.filter(status="paused").count() == 2
    super_client.post("/operations/migration/actions/resume-all/")
    assert MigrationJob.objects.filter(status="running").count() == 2


def test_resolve_error(super_client, job):
    err = MigrationErrorRecord.objects.create(job=job, category="mapper_error", message="x",
                                              old_app="roles", old_model="Role")
    super_client.post(f"/operations/migration/actions/errors/{err.id}/resolve/", {"note": "manual"})
    err.refresh_from_db()
    assert err.resolved is True
    assert "manual" in err.resolution_note
```

- [ ] **Step 2: Run, expect 404**

```bash
pytest migration/tests/test_views_actions.py -v
```

- [ ] **Step 3: Implement**

`NEW/migration/views/actions.py`:
```python
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from migration.models import MigrationErrorRecord, MigrationJob
from migration.tasks.pipeline import DEPENDENCY_ORDER, run_migration_pipeline
from migration.tasks.retry import retry_single_row
from migration.tasks.verify import verify_migration


class _SuperuserOnlyMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser


def _back(request, fallback="migration:overview"):
    return HttpResponseRedirect(request.META.get("HTTP_REFERER") or reverse(fallback))


class StartPipelineView(_SuperuserOnlyMixin, View):
    def post(self, request):
        for app, model in DEPENDENCY_ORDER:
            MigrationJob.objects.get_or_create(app_label=app, model_name=model)
        run_migration_pipeline.delay()
        return _back(request)


class PauseAllView(_SuperuserOnlyMixin, View):
    def post(self, request):
        MigrationJob.objects.exclude(status__in=("completed", "failed")).update(status="paused")
        return _back(request)


class ResumeAllView(_SuperuserOnlyMixin, View):
    def post(self, request):
        MigrationJob.objects.filter(status="paused").update(status="running")
        return _back(request)


class ToggleDryRunView(_SuperuserOnlyMixin, View):
    def post(self, request):
        from django.conf import settings
        settings.MIGRATION_DRY_RUN = not getattr(settings, "MIGRATION_DRY_RUN", False)
        return _back(request)


class PauseJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        MigrationJob.objects.filter(pk=pk).update(status="paused")
        return _back(request)


class ResumeJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        MigrationJob.objects.filter(pk=pk).update(status="running")
        return _back(request)


class RestartJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        if request.POST.get("confirm") != "yes":
            return _back(request)
        MigrationJob.objects.filter(pk=pk).update(
            status="pending", last_cursor="", rows_written=0, rows_errored=0,
            rows_skipped=0, rows_fetched=0, completed_at=None, started_at=None,
        )
        return _back(request)


class VerifyJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        verify_migration.delay(job_id=pk)
        return _back(request)


class RetryErrorView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        err = MigrationErrorRecord.objects.get(pk=pk)
        retry_single_row.delay(job_id=err.job_id, old_pk=err.old_pk)
        return _back(request)


class ResolveErrorView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        note = request.POST.get("note", "manual resolution")
        MigrationErrorRecord.objects.filter(pk=pk).update(
            resolved=True, resolved_at=timezone.now(), resolution_note=note,
        )
        return _back(request)
```

- [ ] **Step 4: Run, expect pass**

```bash
pytest migration/tests/test_views_actions.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Update `migration/views/__init__.py`**

```python
# Intentionally empty — views referenced by URLs explicitly.
```

- [ ] **Step 6: Commit**

```bash
git add migration/views/actions.py migration/views/__init__.py migration/tests/test_views_actions.py
git commit -m "feat(migration): dashboard action endpoints (start/pause/resume/retry/etc)"
```

---

### Task 28: Sidebar entry in `base_operation.html`

**Files:**
- Modify: `NEW/templates/base_operation.html` (or the sidebar partial it includes)

- [ ] **Step 1: Inspect the base template**

```bash
cat /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/templates/base_operation.html | head -60
```
Identify the navigation section (likely a `<nav>` or `{% include %}` of a sidebar partial). Find the existing entries to follow the same pattern.

- [ ] **Step 2: Add the entry**

Insert a link visible only to superusers:
```html
{% if request.user.is_superuser %}
  <a href="{% url 'migration:overview' %}" class="...existing classes...">Data Migration</a>
{% endif %}
```
Use the existing class names from a neighboring entry — do not invent new classes.

- [ ] **Step 3: Boot dev server and visit the dashboard**

```bash
python manage.py runserver
```
Browse to `http://localhost:8000/operations/migration/` (after logging in as a superuser). Click around: overview, job detail (after starting the pipeline), errors. Confirm pages render.

- [ ] **Step 4: Commit**

```bash
git add templates/base_operation.html
git commit -m "feat(migration): add Data Migration sidebar entry for superusers"
```

---

## Phase E — Cutover-readiness on simulation

### Task 29: Full end-to-end run on simulation, capture timings

**Files:**
- Modify: `NEW/docs/migration/preflight-2026-05-20.md` (append timings)

- [ ] **Step 1: Reset state**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
python manage.py shell -c "from migration.models import *; from roles.models import Role; MigrationJob.objects.all().delete(); IDMap.objects.all().delete(); MigrationErrorRecord.objects.all().delete(); MigrationRunLog.objects.all().delete(); Role.objects.all().delete()"
```

- [ ] **Step 2: Run the live pipeline**

In one terminal: old-side server (`Task 9 step 2`).
In a second: Celery worker + beat.
```bash
celery -A lms worker -l info &
celery -A lms beat -l info &
```
In a third: visit the dashboard and click **Start pipeline** with `MIGRATION_ENABLED=true` in env.

Wait for `roles.Role` job to reach `completed`.

- [ ] **Step 3: Verify**

In the dashboard, click **Verify** on the Role job. Check `MigrationJob.last_verification` reports `count_parity: True`.

- [ ] **Step 4: Record findings**

Append to `NEW/docs/migration/preflight-2026-05-20.md`:
```markdown
## End-to-end run results (Phase E)

- Total Role rows migrated: <N>
- Wall-clock duration: <H:MM:SS>
- Average rows/min: <R>
- Number of MigrationErrorRecord rows: <E>
- Verification: count_parity=true, idmap_complete=true
```

- [ ] **Step 5: Commit**

```bash
git add docs/migration/preflight-2026-05-20.md
git commit -m "docs(migration): end-to-end timings on simulation classedge"
```

---

### Task 30: Failure-injection acceptance check

**Files:**
- None modified. This is an operator verification step.

- [ ] **Step 1: Force a `missing_fk` (synthetic)**

For the foundation plan, `roles.Role` has no FK other than the M2M `permissions`. To exercise the missing-FK path, temporarily register a synthetic mapper. In a fresh `manage.py shell`:

```python
from migration.mappers.base import _REGISTRY, MapperResult, require_fk
def buggy(payload):
    return MapperResult(
        fields={"name": payload["name"]},
        fk_resolutions=[("nonexistent", "Thing", payload["id"], "fake_field")],
    )
_REGISTRY[("roles", "Role")] = buggy

from migration.models import MigrationJob
from migration.tasks.batch import migrate_model_batch
job = MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")
migrate_model_batch.run(job_id=job.id)
```

- [ ] **Step 2: Open the dashboard error inspector**

Navigate to `/operations/migration/errors/`. Confirm:
- Rows with category `missing_fk` appear.
- Click one. Drawer shows `source_file` ending `migration/writers/base.py` or wherever `require_fk` was called, `source_line` pointing at that exact line, `field="fake_field"`, `expected="IDMap nonexistent.Thing old_pk=..."`.
- Payload excerpt visible.

- [ ] **Step 3: Click "open in VS Code" link**

Confirm the link is well-formed (`vscode://file/...`). Clicking opens VS Code at the line (developer-machine dependent).

- [ ] **Step 4: Restore the real mapper**

```python
from migration.mappers.base import _REGISTRY
from migration.mappers.roles_role import map_role
_REGISTRY[("roles", "Role")] = map_role
```

- [ ] **Step 5: Append a note to runbook (Task 31)**

Skipped here — will be done in Task 31.

- [ ] **Step 6: No commit (operational verification only)**

---

### Task 31: Operator runbook

**Files:**
- Create: `NEW/docs/migration/runbook-foundation.md`

- [ ] **Step 1: Write the runbook**

```markdown
# Migration Foundation — Operator Runbook

This runbook covers the foundation pipeline (Roles only, simulation classedge target).
For per-app expansions, see the matching follow-up plans.

## 1. Prerequisites

- Old LMS source: `/home/classify/Desktop/Projects/simulation-lms/classedge`
- New LMS: `/home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai`
- Redis running (Celery broker).
- Both Python venvs installed.

## 2. Generate a migration token (one-time per environment)

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py shell -c "from migration_api.models import MigrationToken; p, t = MigrationToken.objects.create_token(label='dev'); print('TOKEN:', p)"
```

Copy the printed token — it is not retrievable later.

## 3. Configure the new side

Add to `.env`:

```
MIGRATION_OLD_LMS_BASE_URL=http://localhost:8001
MIGRATION_OLD_LMS_TOKEN=<paste>
MIGRATION_ENABLED=False     # leave False until you are ready to start
```

## 4. Boot

Terminal 1 (old side):
```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
python manage.py runserver 0.0.0.0:8001
```

Terminal 2 (new side worker):
```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
celery -A lms worker -l info
```

Terminal 3 (new side beat):
```bash
celery -A lms beat -l info
```

Terminal 4 (new side web):
```bash
python manage.py runserver
```

## 5. Start the migration

1. Log in as superuser.
2. Visit `/operations/migration/`.
3. Confirm the header shows the correct source URL and a recent health timestamp. If "never" or the URL is wrong, fix `.env` and restart.
4. Click **Start pipeline**.
5. Set `MIGRATION_ENABLED=true` in `.env` and restart Celery beat so the orchestrator ticks.

## 6. Monitor

- Overview table polls every 3s — watch progress bar and rate.
- Click a job to see live batch logs.
- Click error count badges to drill into per-row failures.

## 7. Triage an error

1. Open the error from the inspector.
2. The drawer shows: source file + line, field, expected, actual, payload excerpt, full traceback.
3. Click **open in VS Code** for the exact line of the failing code.
4. Fix the underlying issue. Click **Retry this row** to re-run just that PK. On success, the error auto-resolves.

## 8. Pause / resume / restart

- **Pause all** — flips all `pending`/`running` jobs to `paused`. Workers finish current batch then stop.
- **Resume all** — flips `paused` → `running`.
- **Restart from zero** (per-job, in detail page) — clears cursor and counters. Requires confirmation.

## 9. Dry-run rehearsal

Toggle **dry-run** on the overview before starting the pipeline. Writers will short-circuit before `save()` but run logs still record what would have happened. Use this to time a run without changing the new DB.

## 10. Verify completion

In the overview, click **Verify** on a completed job. The job's `last_verification` JSON shows `count_parity` and `idmap_complete`. Both must be `true` before the foundation is considered done.

## 11. Rollback

Foundation is reversible:
```bash
python manage.py shell -c "from migration.models import *; from roles.models import Role; MigrationJob.objects.all().delete(); IDMap.objects.all().delete(); MigrationErrorRecord.objects.all().delete(); MigrationRunLog.objects.all().delete(); Role.objects.all().delete()"
```

This drops every Role row created by the pipeline plus all tracking state. Use only on test environments.

## 12. Pointing at SNCFI or NewHope

The same code base targets any old LMS. Procedure:
1. Run the analogue of step 2 (create a token) on the target LMS.
2. Set `MIGRATION_OLD_LMS_BASE_URL` and `MIGRATION_OLD_LMS_TOKEN` in `.env`.
3. Reset state (step 11) if you are starting clean, or leave intact to resume.
4. Start the pipeline (step 5).
```

- [ ] **Step 2: Commit**

```bash
git add docs/migration/runbook-foundation.md
git commit -m "docs(migration): operator runbook for foundation pipeline"
```

---

### Task 32: Final full-suite test run + plan close

**Files:**
- None modified.

- [ ] **Step 1: Run full test suite, both sides**

```bash
cd /home/classify/Desktop/Projects/simulation-lms/classedge
pytest migration_api/ -v
```
Expected: all green.

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
pytest migration/ -v
```
Expected: all green except the opt-in E2E (skipped unless `MIGRATION_E2E=1`).

- [ ] **Step 2: Confirm acceptance criteria 1–9 from spec §12**

Run through the spec acceptance list. Tick each one off in your notes. If any fails, file an issue and resolve before declaring the plan complete.

- [ ] **Step 3: Final commit**

```bash
cd /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai
git commit --allow-empty -m "chore(migration): foundation plan complete — all acceptance criteria green"
```

---

## End of plan
