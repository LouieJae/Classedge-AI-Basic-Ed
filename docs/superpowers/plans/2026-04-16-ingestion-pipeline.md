# PDF Ingestion Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Central portal staff upload a textbook PDF, a microservice extracts the table of contents, and the result is stored as ParsedTextbook + ParsedChapter rows ready for the curriculum planner (Sub-project 4b).

**Architecture:** A Docker microservice (FastAPI + PyMuPDF) handles PDF parsing via HTTP. The Django central portal uploads PDFs, dispatches Celery tasks that call the microservice, and stores results in two new models. The subject detail page shows uploaded textbooks with status badges that auto-refresh via HTMX polling.

**Tech Stack:** FastAPI, PyMuPDF (fitz), Docker, Celery, Django, HTMX

---

## File Structure

**Create:**
- `services/mineru/Dockerfile`
- `services/mineru/requirements.txt`
- `services/mineru/app.py` — FastAPI application with `/parse/toc` and `/parse/chapter` endpoints
- `services/mineru/cache.py` — file-based SHA-256 cache
- `central_content/models/parsed_textbook.py` — ParsedTextbook model
- `central_content/models/parsed_chapter.py` — ParsedChapter model
- `central_content/tasks.py` — Celery tasks for TOC and chapter parsing
- `central_content/views/textbooks.py` — upload + detail views
- `central_content/templates/central_content/textbooks/upload.html`
- `central_content/templates/central_content/textbooks/detail.html`
- `central_content/templates/central_content/textbooks/status_badge.html` — HTMX partial for polling
- `central_content/tests/test_textbook_models.py`
- `central_content/tests/test_textbook_tasks.py`
- `central_content/tests/test_textbook_views.py`

**Modify:**
- `central_content/models/__init__.py` — export new models
- `central_content/forms.py` — add TextbookUploadForm
- `central_content/views/subjects.py:44-57` — add textbooks to subject_detail context
- `central_content/templates/central_content/subjects/detail.html` — add Textbooks section
- `central_content/urls.py` — add textbook routes
- `lms/settings.py` — add MINERU_SERVICE_URL, MINERU_TIMEOUT

---

## Context for the implementer

### Existing patterns

**Celery tasks** use `@shared_task(bind=True, max_retries=3)`, import models inside the function, use `transaction.atomic()`, return dicts with status. See `course/tasks.py` for examples. Tasks are autodiscovered from `tasks.py` in each Django app.

**Central content views** use `@central_role_required(*roles)` decorator, `get_object_or_404`, and render templates. Subject detail at `central_content/views/subjects.py:44-57`.

**Central content models** live in `central_content/models/` with one file per model. Each is exported in `__init__.py`. Follow existing State choices pattern.

**Templates** use Tailwind CSS via CDN, extend `central_content/base.html`. Subject detail shows modules/activities sections in white cards with shadow.

**Test patterns** use Django TestCase with `@override_settings(...)` for central settings. Use factories from `central_content/tests/factories.py`.

**URL pattern**: `subjects/<int:subject_id>/resource/action`

### Dev environment

- Virtualenv: `env/bin/python`
- Test DB: `test_neondb` on Neon cloud, use `--keepdb`
- Run tests: `env/bin/python manage.py test <app_label> --keepdb -v2`

---

### Task 1: MinerU Docker microservice — cache module

**Files:**
- Create: `services/mineru/cache.py`

- [ ] **Step 1: Create the services directory**

```bash
mkdir -p services/mineru
```

- [ ] **Step 2: Write the cache module**

Create `services/mineru/cache.py`:

```python
import hashlib
import json
import os
from pathlib import Path

CACHE_DIR = Path(os.environ.get("MINERU_CACHE_DIR", "/tmp/mineru_cache"))


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _cache_path(sha: str, suffix: str) -> Path:
    return CACHE_DIR / f"{sha}_{suffix}.json"


def get_cached(sha: str, suffix: str) -> dict | None:
    path = _cache_path(sha, suffix)
    if path.exists():
        return json.loads(path.read_text())
    return None


def put_cache(sha: str, suffix: str, data: dict) -> None:
    _ensure_cache_dir()
    path = _cache_path(sha, suffix)
    path.write_text(json.dumps(data, ensure_ascii=False))
```

- [ ] **Step 3: Commit**

```bash
git add services/mineru/cache.py
git commit -m "feat(mineru): add file-based cache module for PDF parsing results"
```

---

### Task 2: MinerU Docker microservice — FastAPI application

**Files:**
- Create: `services/mineru/app.py`
- Create: `services/mineru/requirements.txt`
- Create: `services/mineru/Dockerfile`

- [ ] **Step 1: Write requirements.txt**

Create `services/mineru/requirements.txt`:

```
fastapi==0.115.0
uvicorn==0.34.0
python-multipart==0.0.9
PyMuPDF==1.24.9
```

- [ ] **Step 2: Write the FastAPI application**

Create `services/mineru/app.py`:

```python
import io
import re
import tempfile

import fitz
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from cache import file_hash, get_cached, put_cache

app = FastAPI(title="MinerU PDF Parser")


@app.get("/health")
def health():
    return {"status": "ok"}


def _extract_toc(doc: fitz.Document) -> list[dict]:
    toc = doc.get_toc(simple=True)
    if not toc:
        return _fallback_chapters(doc)

    chapters = []
    for i, (level, title, page) in enumerate(toc):
        if level > 1:
            continue
        start_page = page
        end_page = toc[i + 1][2] - 1 if i + 1 < len(toc) else doc.page_count
        chapters.append({
            "number": len(chapters) + 1,
            "title": title.strip(),
            "start_page": start_page,
            "end_page": end_page,
        })
    return chapters


def _fallback_chapters(doc: fitz.Document) -> list[dict]:
    chapter_pattern = re.compile(
        r"^(chapter|unit|module|lesson)\s+\d+", re.IGNORECASE
    )
    chapters = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                max_size = max((span["size"] for span in line["spans"]), default=0)
                if max_size >= 16 and chapter_pattern.match(text):
                    if chapters:
                        chapters[-1]["end_page"] = page_num
                    chapters.append({
                        "number": len(chapters) + 1,
                        "title": text,
                        "start_page": page_num + 1,
                        "end_page": doc.page_count,
                    })
    if not chapters:
        chapters.append({
            "number": 1,
            "title": "Full Document",
            "start_page": 1,
            "end_page": doc.page_count,
        })
    return chapters


@app.post("/parse/toc")
async def parse_toc(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty_file")

    sha = file_hash(contents)
    cached = get_cached(sha, "toc")
    if cached:
        return JSONResponse(content=cached)

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_pdf")

    chapters = _extract_toc(doc)
    title = doc.metadata.get("title", "") or file.filename or "Untitled"

    result = {
        "title": title.replace(".pdf", ""),
        "total_pages": doc.page_count,
        "chapters": chapters,
    }
    doc.close()

    put_cache(sha, "toc", result)
    return JSONResponse(content=result)


def _parse_page_text(page: fitz.Page) -> list[dict]:
    blocks = page.get_text("dict")["blocks"]
    sections = []
    current_heading = ""
    current_text_parts = []

    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            max_size = max((span["size"] for span in line["spans"]), default=0)
            is_bold = any(
                "bold" in (span.get("font", "").lower()) for span in line["spans"]
            )
            if max_size >= 13 and is_bold and len(text) < 200:
                if current_heading or current_text_parts:
                    sections.append({
                        "heading": current_heading,
                        "text": " ".join(current_text_parts),
                    })
                current_heading = text
                current_text_parts = []
            else:
                current_text_parts.append(text)

    if current_heading or current_text_parts:
        sections.append({
            "heading": current_heading,
            "text": " ".join(current_text_parts),
        })
    return sections


@app.post("/parse/chapter")
async def parse_chapter(
    file: UploadFile = File(...),
    start_page: int = Form(...),
    end_page: int = Form(...),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty_file")

    sha = file_hash(contents)
    cache_suffix = f"ch{start_page}_{end_page}"
    cached = get_cached(sha, cache_suffix)
    if cached:
        return JSONResponse(content=cached)

    try:
        doc = fitz.open(stream=contents, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_pdf")

    if start_page < 1 or end_page > doc.page_count or start_page > end_page:
        doc.close()
        raise HTTPException(status_code=400, detail="invalid_page_range")

    all_sections = []
    images = []
    for page_num in range(start_page - 1, end_page):
        page = doc.load_page(page_num)
        all_sections.extend(_parse_page_text(page))
        for img_index, img in enumerate(page.get_images(full=True)):
            images.append(f"page{page_num + 1}_img{img_index + 1}")

    result = {
        "start_page": start_page,
        "end_page": end_page,
        "sections": all_sections,
        "images": images,
    }
    doc.close()

    put_cache(sha, cache_suffix, result)
    return JSONResponse(content=result)
```

- [ ] **Step 3: Write the Dockerfile**

Create `services/mineru/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MINERU_CACHE_DIR=/data/cache

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/health')"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8765"]
```

- [ ] **Step 4: Build and test the Docker image**

```bash
cd services/mineru && docker build -t mineru-parser . && cd ../..
docker run -d --name mineru-test -p 8765:8765 -v mineru_cache:/data/cache mineru-parser
curl http://localhost:8765/health
```

Expected: `{"status":"ok"}`

```bash
docker stop mineru-test && docker rm mineru-test
```

- [ ] **Step 5: Commit**

```bash
git add services/mineru/
git commit -m "feat(mineru): add Docker microservice for PDF parsing (FastAPI + PyMuPDF)"
```

---

### Task 3: ParsedTextbook and ParsedChapter models + migration

**Files:**
- Create: `central_content/models/parsed_textbook.py`
- Create: `central_content/models/parsed_chapter.py`
- Modify: `central_content/models/__init__.py`

- [ ] **Step 1: Write ParsedTextbook model**

Create `central_content/models/parsed_textbook.py`:

```python
import os
import uuid

from django.db import models


def _textbook_file_path(instance, filename):
    new_name = f"{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    return os.path.join("central", "textbooks", new_name)


class ParsedTextbook(models.Model):
    class Status(models.TextChoices):
        UPLOADING = "uploading", "Uploading"
        PARSING_TOC = "parsing_toc", "Parsing TOC"
        TOC_READY = "toc_ready", "TOC Ready"
        FAILED = "failed", "Failed"

    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="textbooks",
    )
    title = models.CharField(max_length=200)
    original_file = models.FileField(upload_to=_textbook_file_path)
    file_hash = models.CharField(max_length=64, blank=True)
    toc_data = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.UPLOADING,
    )
    error_message = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="textbooks_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_parsed_textbook"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
```

- [ ] **Step 2: Write ParsedChapter model**

Create `central_content/models/parsed_chapter.py`:

```python
from django.db import models


class ParsedChapter(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARSING = "parsing", "Parsing"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    textbook = models.ForeignKey(
        "central_content.ParsedTextbook",
        on_delete=models.CASCADE,
        related_name="chapters",
    )
    chapter_number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    start_page = models.PositiveIntegerField()
    end_page = models.PositiveIntegerField()
    parsed_data = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    error_message = models.TextField(blank=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_parsed_chapter"
        ordering = ["chapter_number"]

    def __str__(self):
        return f"Ch.{self.chapter_number}: {self.title}"
```

- [ ] **Step 3: Export models in __init__.py**

Read `central_content/models/__init__.py` and add the new imports. Add these lines:

```python
from central_content.models.parsed_textbook import ParsedTextbook
from central_content.models.parsed_chapter import ParsedChapter
```

- [ ] **Step 4: Generate and apply migration**

```bash
env/bin/python manage.py makemigrations central_content --name add_parsed_textbook_and_chapter
env/bin/python manage.py migrate central_content
```

- [ ] **Step 5: Commit**

```bash
git add central_content/models/parsed_textbook.py central_content/models/parsed_chapter.py central_content/models/__init__.py central_content/migrations/*_add_parsed_textbook_and_chapter.py
git commit -m "feat(central_content): add ParsedTextbook and ParsedChapter models"
```

---

### Task 4: Settings additions

**Files:**
- Modify: `lms/settings.py`

- [ ] **Step 1: Add MinerU settings**

In `lms/settings.py`, after the `CENTRAL_INGEST_TOKEN` line (around line 294), add:

```python
MINERU_SERVICE_URL = os.getenv('MINERU_SERVICE_URL', 'http://localhost:8765')
MINERU_TOC_TIMEOUT = int(os.getenv('MINERU_TOC_TIMEOUT', '120'))
MINERU_CHAPTER_TIMEOUT = int(os.getenv('MINERU_CHAPTER_TIMEOUT', '300'))
```

- [ ] **Step 2: Run Django check**

```bash
env/bin/python manage.py check
```

Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add lms/settings.py
git commit -m "feat(settings): add MINERU_SERVICE_URL and timeout settings"
```

---

### Task 5: Celery tasks for TOC and chapter parsing

**Files:**
- Create: `central_content/tasks.py`

- [ ] **Step 1: Write the tasks**

Create `central_content/tasks.py`:

```python
import hashlib

import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction


@shared_task(bind=True, max_retries=3)
def parse_textbook_toc(self, textbook_id):
    from central_content.models import ParsedTextbook, ParsedChapter

    try:
        textbook = ParsedTextbook.objects.get(pk=textbook_id)
    except ParsedTextbook.DoesNotExist:
        return {"status": "error", "detail": "textbook_not_found"}

    file_bytes = textbook.original_file.read()
    textbook.file_hash = hashlib.sha256(file_bytes).hexdigest()
    textbook.status = ParsedTextbook.Status.PARSING_TOC
    textbook.save(update_fields=["file_hash", "status"])

    try:
        textbook.original_file.seek(0)
        resp = requests.post(
            f"{settings.MINERU_SERVICE_URL}/parse/toc",
            files={"file": (textbook.original_file.name, file_bytes, "application/pdf")},
            timeout=settings.MINERU_TOC_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ValueError(f"MinerU returned {resp.status_code}: {resp.text[:500]}")

        toc = resp.json()

        with transaction.atomic():
            textbook.toc_data = toc
            textbook.title = textbook.title or toc.get("title", "Untitled")
            textbook.status = ParsedTextbook.Status.TOC_READY
            textbook.error_message = ""
            textbook.save(update_fields=[
                "toc_data", "title", "status", "error_message",
            ])

            ParsedChapter.objects.filter(textbook=textbook).delete()
            for ch in toc.get("chapters", []):
                ParsedChapter.objects.create(
                    textbook=textbook,
                    chapter_number=ch["number"],
                    title=ch["title"],
                    start_page=ch["start_page"],
                    end_page=ch["end_page"],
                )

        return {"status": "success", "chapters": len(toc.get("chapters", []))}

    except requests.RequestException as exc:
        textbook.status = ParsedTextbook.Status.FAILED
        textbook.error_message = f"Connection error: {exc}"
        textbook.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    except Exception as exc:
        textbook.status = ParsedTextbook.Status.FAILED
        textbook.error_message = str(exc)[:2000]
        textbook.save(update_fields=["status", "error_message"])
        return {"status": "error", "detail": str(exc)[:500]}


@shared_task(bind=True, max_retries=3)
def parse_single_chapter(self, chapter_id):
    from central_content.models import ParsedChapter

    try:
        chapter = ParsedChapter.objects.select_related("textbook").get(pk=chapter_id)
    except ParsedChapter.DoesNotExist:
        return {"status": "error", "detail": "chapter_not_found"}

    chapter.status = ParsedChapter.Status.PARSING
    chapter.save(update_fields=["status"])

    try:
        file_bytes = chapter.textbook.original_file.read()
        chapter.textbook.original_file.seek(0)

        resp = requests.post(
            f"{settings.MINERU_SERVICE_URL}/parse/chapter",
            files={"file": ("textbook.pdf", file_bytes, "application/pdf")},
            data={
                "start_page": chapter.start_page,
                "end_page": chapter.end_page,
            },
            timeout=settings.MINERU_CHAPTER_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ValueError(f"MinerU returned {resp.status_code}: {resp.text[:500]}")

        chapter.parsed_data = resp.json()
        chapter.status = ParsedChapter.Status.COMPLETE
        chapter.error_message = ""
        chapter.save(update_fields=["parsed_data", "status", "error_message"])

        return {"status": "success", "chapter": chapter.chapter_number}

    except requests.RequestException as exc:
        chapter.status = ParsedChapter.Status.FAILED
        chapter.error_message = f"Connection error: {exc}"
        chapter.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    except Exception as exc:
        chapter.status = ParsedChapter.Status.FAILED
        chapter.error_message = str(exc)[:2000]
        chapter.save(update_fields=["status", "error_message"])
        return {"status": "error", "detail": str(exc)[:500]}
```

- [ ] **Step 2: Verify Celery discovers the tasks**

```bash
env/bin/python -c "
import django; import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lms.settings')
django.setup()
from central_content.tasks import parse_textbook_toc, parse_single_chapter
print('parse_textbook_toc:', parse_textbook_toc.name)
print('parse_single_chapter:', parse_single_chapter.name)
"
```

Expected: Both task names print without error.

- [ ] **Step 3: Commit**

```bash
git add central_content/tasks.py
git commit -m "feat(central_content): add Celery tasks for TOC and chapter parsing"
```

---

### Task 6: Textbook upload form

**Files:**
- Modify: `central_content/forms.py`

- [ ] **Step 1: Add TextbookUploadForm**

Add to the end of `central_content/forms.py`:

```python
class TextbookUploadForm(forms.Form):
    title = forms.CharField(max_length=200, required=False)
    file = forms.FileField()

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are accepted.")
        if f.size > 200 * 1024 * 1024:
            raise forms.ValidationError("File must be under 200 MB.")
        return f
```

- [ ] **Step 2: Commit**

```bash
git add central_content/forms.py
git commit -m "feat(central_content): add TextbookUploadForm with PDF validation"
```

---

### Task 7: Views — textbook upload and detail

**Files:**
- Create: `central_content/views/textbooks.py`
- Modify: `central_content/views/subjects.py`

- [ ] **Step 1: Write textbook views**

Create `central_content/views/textbooks.py`:

```python
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from central_content.forms import TextbookUploadForm
from central_content.models import CentralSubject, ParsedTextbook
from central_content.permissions import central_role_required
from central_content.tasks import parse_textbook_toc


@central_role_required("publisher", "editor")
def textbook_upload(request, subject_id: int):
    subject = get_object_or_404(CentralSubject, pk=subject_id)

    if request.method == "POST":
        form = TextbookUploadForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data["title"] or request.FILES["file"].name.replace(".pdf", "")
            textbook = ParsedTextbook.objects.create(
                central_subject=subject,
                title=title,
                original_file=form.cleaned_data["file"],
                uploaded_by=request.user,
                status=ParsedTextbook.Status.UPLOADING,
            )
            parse_textbook_toc.delay(textbook.pk)
            return redirect(f"/subjects/{subject_id}/textbooks/{textbook.pk}/")
    else:
        form = TextbookUploadForm()

    return render(
        request,
        "central_content/textbooks/upload.html",
        {"subject": subject, "form": form},
    )


@central_role_required("publisher", "editor", "reviewer")
def textbook_detail(request, subject_id: int, textbook_id: int):
    textbook = get_object_or_404(
        ParsedTextbook.objects.select_related("central_subject", "uploaded_by"),
        pk=textbook_id,
        central_subject_id=subject_id,
    )
    chapters = textbook.chapters.all()

    return render(
        request,
        "central_content/textbooks/detail.html",
        {"textbook": textbook, "subject": textbook.central_subject, "chapters": chapters},
    )


@central_role_required("publisher", "editor", "reviewer")
def textbook_status_badge(request, subject_id: int, textbook_id: int):
    textbook = get_object_or_404(
        ParsedTextbook, pk=textbook_id, central_subject_id=subject_id,
    )
    return render(
        request,
        "central_content/textbooks/status_badge.html",
        {"textbook": textbook},
    )
```

- [ ] **Step 2: Update subject_detail to include textbooks**

In `central_content/views/subjects.py`, replace the `subject_detail` function:

```python
@central_role_required(*_ALL_ROLES)
def subject_detail(request, subject_id: int):
    subj = get_object_or_404(
        CentralSubject.objects.prefetch_related("modules", "activities", "textbooks"),
        pk=subject_id,
    )
    return render(
        request,
        "central_content/subjects/detail.html",
        {
            "subject": subj,
            "modules": subj.modules.all(),
            "activities": subj.activities.all(),
            "textbooks": subj.textbooks.all(),
        },
    )
```

- [ ] **Step 3: Commit**

```bash
git add central_content/views/textbooks.py central_content/views/subjects.py
git commit -m "feat(central_content): add textbook upload and detail views"
```

---

### Task 8: Templates

**Files:**
- Create: `central_content/templates/central_content/textbooks/upload.html`
- Create: `central_content/templates/central_content/textbooks/detail.html`
- Create: `central_content/templates/central_content/textbooks/status_badge.html`
- Modify: `central_content/templates/central_content/subjects/detail.html`

- [ ] **Step 1: Create templates directory**

```bash
mkdir -p central_content/templates/central_content/textbooks
```

- [ ] **Step 2: Write upload.html**

Create `central_content/templates/central_content/textbooks/upload.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}Upload Textbook — {{ subject.subject_name }}{% endblock %}
{% block content %}
<h1 class="text-2xl font-semibold mb-4">Upload Textbook</h1>
<p class="text-gray-600 mb-6">Subject: {{ subject.subject_name }}</p>

<form method="post" enctype="multipart/form-data" class="bg-white p-6 rounded shadow max-w-lg">
    {% csrf_token %}
    <div class="mb-4">
        <label class="block text-sm font-medium mb-1" for="id_title">Title (optional, defaults to filename)</label>
        <input type="text" name="title" id="id_title" class="w-full border rounded px-3 py-2" value="{{ form.title.value|default:'' }}">
        {% if form.title.errors %}<p class="text-red-600 text-sm mt-1">{{ form.title.errors.0 }}</p>{% endif %}
    </div>
    <div class="mb-4">
        <label class="block text-sm font-medium mb-1" for="id_file">PDF File</label>
        <input type="file" name="file" id="id_file" accept=".pdf" class="w-full border rounded px-3 py-2" required>
        {% if form.file.errors %}<p class="text-red-600 text-sm mt-1">{{ form.file.errors.0 }}</p>{% endif %}
    </div>
    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Upload &amp; Parse</button>
    <a href="/subjects/{{ subject.id }}/" class="ml-3 text-gray-600">Cancel</a>
</form>
{% endblock %}
```

- [ ] **Step 3: Write status_badge.html (HTMX partial)**

Create `central_content/templates/central_content/textbooks/status_badge.html`:

```html
{% if textbook.status == "uploading" or textbook.status == "parsing_toc" %}
<span class="px-2 py-1 rounded bg-amber-100 text-amber-800 text-xs"
      hx-get="/subjects/{{ textbook.central_subject_id }}/textbooks/{{ textbook.id }}/status"
      hx-trigger="every 3s"
      hx-swap="outerHTML">
    Processing...
</span>
{% elif textbook.status == "toc_ready" %}
<span class="px-2 py-1 rounded bg-green-100 text-green-800 text-xs">Ready</span>
{% elif textbook.status == "failed" %}
<span class="px-2 py-1 rounded bg-red-100 text-red-800 text-xs" title="{{ textbook.error_message }}">Failed</span>
{% else %}
<span class="px-2 py-1 rounded bg-gray-100 text-gray-600 text-xs">{{ textbook.status }}</span>
{% endif %}
```

- [ ] **Step 4: Write detail.html**

Create `central_content/templates/central_content/textbooks/detail.html`:

```html
{% extends "central_content/base.html" %}
{% block title %}{{ textbook.title }}{% endblock %}
{% block content %}
<div class="flex justify-between items-start mb-4">
    <div>
        <h1 class="text-2xl font-semibold">{{ textbook.title }}</h1>
        <p class="text-gray-600">{{ subject.subject_name }}</p>
    </div>
    {% include "central_content/textbooks/status_badge.html" %}
</div>

<div class="mb-6 bg-white p-4 rounded shadow">
    <h2 class="font-semibold mb-2">Details</h2>
    <p class="text-sm text-gray-500">Uploaded by {{ textbook.uploaded_by.full_name }} · {{ textbook.created_at|date:"M d, Y H:i" }}</p>
    {% if textbook.toc_data %}
    <p class="text-sm text-gray-500 mt-1">{{ textbook.toc_data.total_pages }} pages · {{ textbook.chapters.count }} chapters</p>
    {% endif %}
</div>

{% if textbook.status == "toc_ready" %}
<div class="bg-white p-4 rounded shadow">
    <h2 class="font-semibold mb-2">Chapters</h2>
    <table class="w-full text-sm">
        <thead>
            <tr class="text-left text-gray-500 border-b">
                <th class="py-2 w-12">#</th>
                <th class="py-2">Title</th>
                <th class="py-2 w-24">Pages</th>
                <th class="py-2 w-24">Status</th>
            </tr>
        </thead>
        <tbody>
        {% for ch in chapters %}
            <tr class="border-t">
                <td class="py-2">{{ ch.chapter_number }}</td>
                <td class="py-2">{{ ch.title }}</td>
                <td class="py-2 text-gray-500">{{ ch.start_page }}–{{ ch.end_page }}</td>
                <td class="py-2">
                    {% if ch.status == "complete" %}
                    <span class="text-green-700">Complete</span>
                    {% elif ch.status == "parsing" %}
                    <span class="text-amber-700">Parsing...</span>
                    {% elif ch.status == "failed" %}
                    <span class="text-red-700" title="{{ ch.error_message }}">Failed</span>
                    {% else %}
                    <span class="text-gray-500">Pending</span>
                    {% endif %}
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</div>
{% elif textbook.status == "failed" %}
<div class="bg-red-50 border border-red-200 p-4 rounded">
    <p class="text-red-800 font-medium">Parsing failed</p>
    <p class="text-red-700 text-sm mt-1">{{ textbook.error_message }}</p>
</div>
{% endif %}

<div class="mt-4">
    <a href="/subjects/{{ subject.id }}/" class="text-blue-700">&larr; Back to subject</a>
</div>
{% endblock %}
```

- [ ] **Step 5: Add Textbooks section to subject detail template**

In `central_content/templates/central_content/subjects/detail.html`, add after the Activities section (before `{% endblock %}`):

```html

<div class="bg-white p-4 rounded shadow mt-6">
    <div class="flex justify-between items-center mb-2">
        <h2 class="font-semibold">Textbooks</h2>
        <a href="/subjects/{{ subject.id }}/textbooks/upload" class="text-blue-700">+ Upload textbook</a>
    </div>
    <ul>
    {% for t in textbooks %}
        <li class="border-t py-2 flex justify-between items-center">
            <a href="/subjects/{{ subject.id }}/textbooks/{{ t.id }}/" class="text-blue-700">{{ t.title }}</a>
            {% include "central_content/textbooks/status_badge.html" with textbook=t %}
        </li>
    {% empty %}
        <li class="text-gray-500 py-2">No textbooks yet.</li>
    {% endfor %}
    </ul>
</div>
```

- [ ] **Step 6: Commit**

```bash
git add central_content/templates/
git commit -m "feat(central_content): add textbook templates (upload, detail, status badge)"
```

---

### Task 9: URL routing

**Files:**
- Modify: `central_content/urls.py`

- [ ] **Step 1: Add textbook URL patterns**

In `central_content/urls.py`, add the import at the top:

```python
from central_content.views import textbooks as textbook_views
```

Then add these URL patterns to the `urlpatterns` list:

```python
    # Textbook URLs
    path("subjects/<int:subject_id>/textbooks/upload", textbook_views.textbook_upload, name="textbook_upload"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/", textbook_views.textbook_detail, name="textbook_detail"),
    path("subjects/<int:subject_id>/textbooks/<int:textbook_id>/status", textbook_views.textbook_status_badge, name="textbook_status_badge"),
```

- [ ] **Step 2: Run Django check**

```bash
env/bin/python manage.py check
```

Expected: `System check identified no issues.`

- [ ] **Step 3: Commit**

```bash
git add central_content/urls.py
git commit -m "feat(central_content): add textbook URL routes"
```

---

### Task 10: Model tests

**Files:**
- Create: `central_content/tests/test_textbook_models.py`

- [ ] **Step 1: Write model tests**

Create `central_content/tests/test_textbook_models.py`:

```python
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from central_content.models import (
    CentralSubject, ParsedTextbook, ParsedChapter,
)
from central_content.tests.factories import make_subject, make_editor


class ParsedTextbookModelTests(TestCase):
    def test_create_textbook(self):
        subject = make_subject()
        editor = make_editor()
        pdf = SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf")
        tb = ParsedTextbook.objects.create(
            central_subject=subject,
            title="Algebra Textbook",
            original_file=pdf,
            uploaded_by=editor,
        )
        self.assertEqual(tb.status, "uploading")
        self.assertEqual(tb.central_subject, subject)
        self.assertEqual(str(tb), "Algebra Textbook")

    def test_multiple_textbooks_per_subject(self):
        subject = make_subject()
        editor = make_editor()
        for i in range(3):
            ParsedTextbook.objects.create(
                central_subject=subject,
                title=f"Book {i}",
                original_file=SimpleUploadedFile(f"b{i}.pdf", b"%PDF-fake"),
                uploaded_by=editor,
            )
        self.assertEqual(subject.textbooks.count(), 3)

    def test_cascade_delete(self):
        subject = make_subject()
        editor = make_editor()
        tb = ParsedTextbook.objects.create(
            central_subject=subject,
            title="Book",
            original_file=SimpleUploadedFile("b.pdf", b"%PDF-fake"),
            uploaded_by=editor,
        )
        ParsedChapter.objects.create(
            textbook=tb, chapter_number=1, title="Ch 1",
            start_page=1, end_page=10,
        )
        tb.delete()
        self.assertEqual(ParsedChapter.objects.count(), 0)


class ParsedChapterModelTests(TestCase):
    def _make_textbook(self):
        subject = make_subject()
        editor = make_editor()
        return ParsedTextbook.objects.create(
            central_subject=subject,
            title="Book",
            original_file=SimpleUploadedFile("b.pdf", b"%PDF-fake"),
            uploaded_by=editor,
        )

    def test_create_chapter(self):
        tb = self._make_textbook()
        ch = ParsedChapter.objects.create(
            textbook=tb, chapter_number=1, title="Real Numbers",
            start_page=1, end_page=24,
        )
        self.assertEqual(ch.status, "pending")
        self.assertIsNone(ch.parsed_data)
        self.assertEqual(str(ch), "Ch.1: Real Numbers")

    def test_chapters_ordered_by_number(self):
        tb = self._make_textbook()
        ParsedChapter.objects.create(textbook=tb, chapter_number=3, title="C3", start_page=50, end_page=75)
        ParsedChapter.objects.create(textbook=tb, chapter_number=1, title="C1", start_page=1, end_page=24)
        ParsedChapter.objects.create(textbook=tb, chapter_number=2, title="C2", start_page=25, end_page=49)
        nums = list(tb.chapters.values_list("chapter_number", flat=True))
        self.assertEqual(nums, [1, 2, 3])

    def test_status_transitions(self):
        tb = self._make_textbook()
        ch = ParsedChapter.objects.create(
            textbook=tb, chapter_number=1, title="Ch 1",
            start_page=1, end_page=10,
        )
        ch.status = ParsedChapter.Status.PARSING
        ch.save(update_fields=["status"])
        ch.refresh_from_db()
        self.assertEqual(ch.status, "parsing")

        ch.parsed_data = {"sections": []}
        ch.status = ParsedChapter.Status.COMPLETE
        ch.save(update_fields=["parsed_data", "status"])
        ch.refresh_from_db()
        self.assertEqual(ch.status, "complete")
        self.assertEqual(ch.parsed_data, {"sections": []})
```

- [ ] **Step 2: Run tests**

```bash
env/bin/python manage.py test central_content.tests.test_textbook_models --keepdb -v2
```

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add central_content/tests/test_textbook_models.py
git commit -m "test: add ParsedTextbook and ParsedChapter model tests"
```

---

### Task 11: Celery task tests

**Files:**
- Create: `central_content/tests/test_textbook_tasks.py`

- [ ] **Step 1: Write task tests**

Create `central_content/tests/test_textbook_tasks.py`:

```python
from unittest.mock import patch, MagicMock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import ParsedTextbook, ParsedChapter
from central_content.tasks import parse_textbook_toc, parse_single_chapter
from central_content.tests.factories import make_subject, make_editor


def _make_textbook():
    subject = make_subject()
    editor = make_editor()
    return ParsedTextbook.objects.create(
        central_subject=subject,
        title="Test Book",
        original_file=SimpleUploadedFile("test.pdf", b"%PDF-fake-content"),
        uploaded_by=editor,
        status=ParsedTextbook.Status.UPLOADING,
    )


def _mock_toc_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "title": "Algebra Textbook",
        "total_pages": 100,
        "chapters": [
            {"number": 1, "title": "Real Numbers", "start_page": 1, "end_page": 30},
            {"number": 2, "title": "Expressions", "start_page": 31, "end_page": 60},
            {"number": 3, "title": "Equations", "start_page": 61, "end_page": 100},
        ],
    }
    return resp


@override_settings(MINERU_SERVICE_URL="http://fake-mineru:8765", MINERU_TOC_TIMEOUT=10)
class ParseTextbookTocTests(TestCase):
    @patch("central_content.tasks.requests.post")
    def test_success_creates_chapters(self, mock_post):
        mock_post.return_value = _mock_toc_response()
        tb = _make_textbook()

        result = parse_textbook_toc(tb.pk)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["chapters"], 3)
        tb.refresh_from_db()
        self.assertEqual(tb.status, "toc_ready")
        self.assertEqual(tb.toc_data["total_pages"], 100)
        self.assertEqual(tb.chapters.count(), 3)
        ch1 = tb.chapters.get(chapter_number=1)
        self.assertEqual(ch1.title, "Real Numbers")
        self.assertEqual(ch1.start_page, 1)
        self.assertEqual(ch1.end_page, 30)
        self.assertEqual(ch1.status, "pending")

    @patch("central_content.tasks.requests.post")
    def test_failure_sets_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")
        tb = _make_textbook()

        result = parse_textbook_toc(tb.pk)

        self.assertEqual(result["status"], "error")
        tb.refresh_from_db()
        self.assertEqual(tb.status, "failed")
        self.assertIn("500", tb.error_message)

    @patch("central_content.tasks.requests.post")
    def test_connection_error_retries(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError("refused")
        tb = _make_textbook()

        with self.assertRaises(Exception):
            parse_textbook_toc(tb.pk)

        tb.refresh_from_db()
        self.assertEqual(tb.status, "failed")

    def test_nonexistent_textbook(self):
        result = parse_textbook_toc(99999)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["detail"], "textbook_not_found")

    @patch("central_content.tasks.requests.post")
    def test_reparsing_replaces_chapters(self, mock_post):
        mock_post.return_value = _mock_toc_response()
        tb = _make_textbook()
        ParsedChapter.objects.create(
            textbook=tb, chapter_number=99, title="Old", start_page=1, end_page=5,
        )

        parse_textbook_toc(tb.pk)

        self.assertEqual(tb.chapters.count(), 3)
        self.assertFalse(tb.chapters.filter(chapter_number=99).exists())


@override_settings(MINERU_SERVICE_URL="http://fake-mineru:8765", MINERU_CHAPTER_TIMEOUT=10)
class ParseSingleChapterTests(TestCase):
    @patch("central_content.tasks.requests.post")
    def test_success_stores_parsed_data(self, mock_post):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "start_page": 1,
            "end_page": 30,
            "sections": [{"heading": "1.1 Intro", "text": "Some text"}],
            "images": ["page1_img1"],
        }
        mock_post.return_value = resp

        tb = _make_textbook()
        tb.status = ParsedTextbook.Status.TOC_READY
        tb.save(update_fields=["status"])
        ch = ParsedChapter.objects.create(
            textbook=tb, chapter_number=1, title="Real Numbers",
            start_page=1, end_page=30,
        )

        result = parse_single_chapter(ch.pk)

        self.assertEqual(result["status"], "success")
        ch.refresh_from_db()
        self.assertEqual(ch.status, "complete")
        self.assertEqual(len(ch.parsed_data["sections"]), 1)

    @patch("central_content.tasks.requests.post")
    def test_failure_sets_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=500, text="Error")
        tb = _make_textbook()
        ch = ParsedChapter.objects.create(
            textbook=tb, chapter_number=1, title="Ch 1",
            start_page=1, end_page=10,
        )

        result = parse_single_chapter(ch.pk)

        self.assertEqual(result["status"], "error")
        ch.refresh_from_db()
        self.assertEqual(ch.status, "failed")

    def test_nonexistent_chapter(self):
        result = parse_single_chapter(99999)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["detail"], "chapter_not_found")
```

- [ ] **Step 2: Run tests**

```bash
env/bin/python manage.py test central_content.tests.test_textbook_tasks --keepdb -v2
```

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add central_content/tests/test_textbook_tasks.py
git commit -m "test: add Celery task tests for TOC and chapter parsing"
```

---

### Task 12: View tests

**Files:**
- Create: `central_content/tests/test_textbook_views.py`

- [ ] **Step 1: Write view tests**

Create `central_content/tests/test_textbook_views.py`:

```python
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, Client

from central_content.models import CentralSubject, ParsedTextbook
from central_content.tests.factories import (
    make_subject, make_publisher, make_editor, make_reviewer,
)


@override_settings(ROOT_URLCONF="central_content.urls")
class TextbookUploadViewTests(TestCase):
    def setUp(self):
        self.subject = make_subject()
        self.publisher = make_publisher(password="testpass")
        self.editor = make_editor(password="testpass")
        self.reviewer = make_reviewer(password="testpass")
        self.client = Client()

    def _login(self, user):
        self.client.post("/login", {"email": user.email, "password": "testpass"})

    def test_upload_form_renders_for_publisher(self):
        self._login(self.publisher)
        resp = self.client.get(f"/subjects/{self.subject.pk}/textbooks/upload")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Upload Textbook")

    def test_upload_form_renders_for_editor(self):
        self._login(self.editor)
        resp = self.client.get(f"/subjects/{self.subject.pk}/textbooks/upload")
        self.assertEqual(resp.status_code, 200)

    def test_upload_forbidden_for_reviewer(self):
        self._login(self.reviewer)
        resp = self.client.get(f"/subjects/{self.subject.pk}/textbooks/upload")
        self.assertIn(resp.status_code, [302, 403])

    @patch("central_content.views.textbooks.parse_textbook_toc.delay")
    def test_upload_creates_textbook_and_triggers_task(self, mock_delay):
        self._login(self.publisher)
        pdf = SimpleUploadedFile("algebra.pdf", b"%PDF-fake", content_type="application/pdf")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/upload",
            {"file": pdf},
        )
        self.assertEqual(resp.status_code, 302)
        tb = ParsedTextbook.objects.get()
        self.assertEqual(tb.title, "algebra")
        self.assertEqual(tb.central_subject, self.subject)
        self.assertEqual(tb.uploaded_by, self.publisher)
        mock_delay.assert_called_once_with(tb.pk)

    def test_upload_rejects_non_pdf(self):
        self._login(self.publisher)
        txt = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        resp = self.client.post(
            f"/subjects/{self.subject.pk}/textbooks/upload",
            {"file": txt},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ParsedTextbook.objects.count(), 0)


@override_settings(ROOT_URLCONF="central_content.urls")
class TextbookDetailViewTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(password="testpass")
        self.subject = make_subject()
        self.textbook = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Algebra",
            original_file=SimpleUploadedFile("a.pdf", b"%PDF-fake"),
            uploaded_by=self.publisher,
            status=ParsedTextbook.Status.TOC_READY,
            toc_data={"total_pages": 100, "chapters": []},
        )
        self.client = Client()
        self.client.post("/login", {"email": self.publisher.email, "password": "testpass"})

    def test_detail_renders(self):
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Algebra")
        self.assertContains(resp, "100 pages")

    def test_status_badge_endpoint(self):
        resp = self.client.get(
            f"/subjects/{self.subject.pk}/textbooks/{self.textbook.pk}/status"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Ready")


@override_settings(ROOT_URLCONF="central_content.urls")
class SubjectDetailTextbooksSectionTests(TestCase):
    def setUp(self):
        self.publisher = make_publisher(password="testpass")
        self.subject = make_subject()
        self.client = Client()
        self.client.post("/login", {"email": self.publisher.email, "password": "testpass"})

    def test_subject_detail_shows_textbooks_section(self):
        resp = self.client.get(f"/subjects/{self.subject.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Textbooks")
        self.assertContains(resp, "Upload textbook")

    def test_subject_detail_lists_textbook(self):
        ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="My Book",
            original_file=SimpleUploadedFile("b.pdf", b"%PDF-fake"),
            uploaded_by=self.publisher,
            status=ParsedTextbook.Status.TOC_READY,
        )
        resp = self.client.get(f"/subjects/{self.subject.pk}/")
        self.assertContains(resp, "My Book")
```

- [ ] **Step 2: Run tests**

```bash
env/bin/python manage.py test central_content.tests.test_textbook_views --keepdb -v2
```

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add central_content/tests/test_textbook_views.py
git commit -m "test: add textbook view tests (upload, detail, subject section)"
```

---

### Task 13: Full regression run

- [ ] **Step 1: Run all central_content tests**

```bash
env/bin/python manage.py test central_content --keepdb -v2
```

Expected: All tests pass (existing 65 Sub-1 + Sub-2 tests + new textbook tests).

- [ ] **Step 2: Run all received_central_content tests**

```bash
env/bin/python manage.py test received_central_content --keepdb -v2
```

Expected: All pass.

- [ ] **Step 3: Run Django system check**

```bash
env/bin/python manage.py check
```

Expected: `System check identified no issues.`

- [ ] **Step 4: Count total tests**

```bash
env/bin/python manage.py test central_content received_central_content --keepdb -v2 2>&1 | tail -5
```

Expected: Test count > 153 (prior total). All pass.

- [ ] **Step 5: Final commit if fixups needed**

```bash
git add -A
git commit -m "chore: Sub-4a regression fixes"
```

Only create this commit if fixups were needed.
