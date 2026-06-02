# Gradebook htmx Adoption + Termbook Table Alignment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add htmx-driven search, modal create/edit, and row-swap delete to the gradebook page (`grade-book/`) and align the standalone termbook page (`term-book/`) with the same table design and behavior.

**Architecture:** Add a parallel set of htmx-only endpoints under `gradebook/htmx/` and `termbook/htmx/`. Existing full-page views remain untouched as fallbacks. New partial templates render rows, table bodies, modal forms, and totals so that htmx swaps are surgical. Both pages share the `_termbook_table.html` partial so the standalone termbook page becomes a thin wrapper around the same markup used inside the gradebook page.

**Tech Stack:** Django 5.0, htmx 1.9.12 (already loaded globally), `django-htmx` (to be added) for clean `request.htmx` detection, existing `GradeBookComponents` / `TermGradeBookComponents` models and their existing forms.

**Spec:** `docs/superpowers/specs/2026-05-06-gradebook-htmx-design.md`

---

## File Map

**New partials**
- `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_table.html` — full table body (used by list endpoint)
- `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_row.html` — single `<tr>`
- `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_totals.html` — tfoot row
- `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_form.html` — modal form
- `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_empty_state.html` — empty state row
- `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_table.html`
- `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_row.html`
- `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_totals.html`
- `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_form.html`

**New view module**
- `gradebookcomponent/views/htmx_views.py` — all htmx endpoints in one focused file (keeps existing view files intact)

**Modified**
- `gradebookcomponent/urls.py` — add htmx routes
- `gradebookcomponent/views/__init__.py` — export htmx views
- `gradebookcomponent/templates/gradebookcomponent/gradebook/grade_book.html` — wire htmx attrs, mount modal
- `gradebookcomponent/templates/gradebookcomponent/termbook/term_book.html` — rewrite with `gb-*` table + htmx
- `Classedge_Ai/settings.py` — add `django_htmx` to `INSTALLED_APPS` and `django_htmx.middleware.HtmxMiddleware`

**New tests**
- `gradebookcomponent/tests/test_htmx_views.py`

---

## Task 1: Install and wire `django-htmx`

**Files:**
- Modify: `requirements.txt` (or equivalent) — add `django-htmx`
- Modify: `Classedge_Ai/settings.py`

- [ ] **Step 1: Install package**

```bash
pip install django-htmx
pip freeze | grep -i htmx >> requirements.txt
```

- [ ] **Step 2: Add to INSTALLED_APPS and middleware**

In `Classedge_Ai/settings.py`, add `'django_htmx'` to `INSTALLED_APPS` and add `'django_htmx.middleware.HtmxMiddleware'` to `MIDDLEWARE` (after `CommonMiddleware`).

- [ ] **Step 3: Verify server starts**

```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt Classedge_Ai/settings.py
git commit -m "chore: add django-htmx for gradebook htmx pilot"
```

---

## Task 2: Skeleton htmx view module + URL wiring

**Files:**
- Create: `gradebookcomponent/views/htmx_views.py`
- Modify: `gradebookcomponent/views/__init__.py`
- Modify: `gradebookcomponent/urls.py`

- [ ] **Step 1: Create the htmx view module skeleton**

Create `gradebookcomponent/views/htmx_views.py`:

```python
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from gradebookcomponent.models import GradeBookComponents, TermGradeBookComponents


def _require_htmx(view):
    """Decorator: returns 400 unless request.htmx is true."""
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "htmx", False):
            return HttpResponseBadRequest("htmx request required")
        return view(request, *args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper


# --- Gradebook htmx endpoints -------------------------------------------------

@login_required
@require_GET
@_require_htmx
def gradebook_htmx_list(request):
    qs = GradeBookComponents.objects.filter(teacher=request.user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(gradebook_components_name__icontains=q)
    qs = qs.select_related("subject", "term").order_by(
        "subject__subject_name", "term__term_name", "gradebook_category"
    )
    return render(
        request,
        "gradebookcomponent/gradebook/partials/_gradebook_table.html",
        {"components": qs, "q": q},
    )


@login_required
@require_GET
@_require_htmx
def gradebook_htmx_totals(request):
    return render(
        request,
        "gradebookcomponent/gradebook/partials/_gradebook_totals.html",
        {"components": GradeBookComponents.objects.filter(teacher=request.user)},
    )


@login_required
@_require_htmx
@require_http_methods(["GET", "POST"])
def gradebook_htmx_form(request, pk=None):
    # Implemented in Task 5
    return HttpResponse(status=501)


@login_required
@require_POST
@_require_htmx
def gradebook_htmx_delete(request, pk):
    obj = get_object_or_404(GradeBookComponents, pk=pk, teacher=request.user)
    obj.delete()
    resp = HttpResponse(status=200)
    resp["HX-Trigger"] = "gb-totals-refresh"
    return resp


# --- Termbook htmx endpoints --------------------------------------------------

@login_required
@require_GET
@_require_htmx
def termbook_htmx_list(request):
    qs = TermGradeBookComponents.objects.filter(teacher=request.user).distinct()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(subjects__subject_name__icontains=q).distinct()
    return render(
        request,
        "gradebookcomponent/termbook/partials/_termbook_table.html",
        {"termbooks": qs, "q": q},
    )


@login_required
@require_GET
@_require_htmx
def termbook_htmx_totals(request):
    return render(
        request,
        "gradebookcomponent/termbook/partials/_termbook_totals.html",
        {"termbooks": TermGradeBookComponents.objects.filter(teacher=request.user)},
    )


@login_required
@_require_htmx
@require_http_methods(["GET", "POST"])
def termbook_htmx_form(request, pk=None):
    # Implemented in Task 5
    return HttpResponse(status=501)


@login_required
@require_POST
@_require_htmx
def termbook_htmx_delete(request, pk):
    obj = get_object_or_404(TermGradeBookComponents, pk=pk, teacher=request.user)
    obj.delete()
    resp = HttpResponse(status=200)
    resp["HX-Trigger"] = "tb-totals-refresh"
    return resp
```

- [ ] **Step 2: Export from views package**

Append to `gradebookcomponent/views/__init__.py`:

```python
from gradebookcomponent.views.htmx_views import (
    gradebook_htmx_list,
    gradebook_htmx_totals,
    gradebook_htmx_form,
    gradebook_htmx_delete,
    termbook_htmx_list,
    termbook_htmx_totals,
    termbook_htmx_form,
    termbook_htmx_delete,
)
```

- [ ] **Step 3: Add URL routes**

In `gradebookcomponent/urls.py`, inside `urlpatterns`, add:

```python
# htmx pilot routes (gradebook + termbook only)
path("gradebook/htmx/list/", gradebook_htmx_list, name="gradebook-htmx-list"),
path("gradebook/htmx/totals/", gradebook_htmx_totals, name="gradebook-htmx-totals"),
path("gradebook/htmx/form/", gradebook_htmx_form, name="gradebook-htmx-form"),
path("gradebook/htmx/form/<int:pk>/", gradebook_htmx_form, name="gradebook-htmx-form-edit"),
path("gradebook/htmx/delete/<int:pk>/", gradebook_htmx_delete, name="gradebook-htmx-delete"),
path("termbook/htmx/list/", termbook_htmx_list, name="termbook-htmx-list"),
path("termbook/htmx/totals/", termbook_htmx_totals, name="termbook-htmx-totals"),
path("termbook/htmx/form/", termbook_htmx_form, name="termbook-htmx-form"),
path("termbook/htmx/form/<int:pk>/", termbook_htmx_form, name="termbook-htmx-form-edit"),
path("termbook/htmx/delete/<int:pk>/", termbook_htmx_delete, name="termbook-htmx-delete"),
```

- [ ] **Step 4: Verify URL config loads**

```bash
python manage.py check
python manage.py show_urls 2>/dev/null | grep "htmx" || python manage.py shell -c "from django.urls import reverse; print(reverse('gradebook-htmx-list'))"
```
Expected: `/gradebook/htmx/list/` printed.

- [ ] **Step 5: Commit**

```bash
git add gradebookcomponent/views/htmx_views.py gradebookcomponent/views/__init__.py gradebookcomponent/urls.py
git commit -m "feat(gradebook): scaffold htmx endpoints and URL routes"
```

---

## Task 3: Gradebook table partials

**Files:**
- Create: `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_row.html`
- Create: `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_table.html`
- Create: `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_totals.html`
- Create: `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_empty_state.html`

- [ ] **Step 1: Create the row partial**

`_gradebook_row.html`:

```django
{% load humanize %}
<tr id="gb-row-{{ component.id }}">
  <td class="gb-cell-strong">{{ component.subject.subject_name }}</td>
  <td>{{ component.gradebook_components_name }}</td>
  <td>{{ component.percentage|floatformat:0 }}%</td>
  <td>{{ component.term.term_name }}</td>
  <td class="gb-action-cell">
    <button type="button"
            class="gb-icon-btn"
            title="Edit"
            hx-get="{% url 'gradebook-htmx-form-edit' component.id %}"
            hx-target="#gb-modal"
            hx-swap="innerHTML">
      <i class="fas fa-pen"></i>
    </button>
    <button type="button"
            class="gb-icon-btn gb-icon-btn--danger"
            title="Delete"
            hx-post="{% url 'gradebook-htmx-delete' component.id %}"
            hx-target="#gb-row-{{ component.id }}"
            hx-swap="outerHTML swap:200ms"
            hx-confirm="Delete this gradebook component?">
      <i class="fas fa-trash"></i>
    </button>
  </td>
</tr>
```

- [ ] **Step 2: Create the table-body partial**

`_gradebook_table.html`:

```django
{% for component in components %}
  {% include "gradebookcomponent/gradebook/partials/_gradebook_row.html" with component=component %}
{% empty %}
  {% include "gradebookcomponent/gradebook/partials/_empty_state.html" with colspan=5 message="No gradebook components found." %}
{% endfor %}
```

- [ ] **Step 3: Create the totals partial**

`_gradebook_totals.html`:

```django
{% load humanize %}
<tr id="gb-totals-row">
  <th></th>
  <th>Total</th>
  <th colspan="3">
    {% with total=components|length %}{{ total }} component{{ total|pluralize }}{% endwith %}
  </th>
</tr>
```

- [ ] **Step 4: Create the empty-state partial**

`_empty_state.html`:

```django
<tr class="gb-empty-row">
  <td colspan="{{ colspan|default:5 }}" class="text-center text-muted py-4">
    {{ message|default:"No records found." }}
  </td>
</tr>
```

- [ ] **Step 5: Smoke test render**

```bash
python manage.py shell -c "from django.template.loader import get_template; get_template('gradebookcomponent/gradebook/partials/_gradebook_table.html'); get_template('gradebookcomponent/gradebook/partials/_gradebook_row.html'); get_template('gradebookcomponent/gradebook/partials/_gradebook_totals.html'); get_template('gradebookcomponent/gradebook/partials/_empty_state.html'); print('OK')"
```
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/gradebook/partials/
git commit -m "feat(gradebook): add htmx table partials"
```

---

## Task 4: Termbook table partials (mirrored)

**Files:**
- Create: `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_row.html`
- Create: `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_table.html`
- Create: `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_totals.html`

- [ ] **Step 1: Create the row partial**

`_termbook_row.html`:

```django
<tr id="tb-row-{{ termbook.id }}">
  <td class="gb-cell-strong">
    {% for subject in termbook.subjects.all %}{{ subject.subject_name }}{% if not forloop.last %}, {% endif %}{% endfor %}
  </td>
  <td>{{ termbook.percentage|floatformat:0 }}%</td>
  <td>{{ termbook.term.term_name }}</td>
  <td>{{ termbook.base_grade }}</td>
  <td class="gb-action-cell">
    <button type="button"
            class="gb-icon-btn"
            title="Edit"
            hx-get="{% url 'termbook-htmx-form-edit' termbook.id %}"
            hx-target="#gb-modal"
            hx-swap="innerHTML">
      <i class="fas fa-pen"></i>
    </button>
    <button type="button"
            class="gb-icon-btn gb-icon-btn--danger"
            title="Delete"
            hx-post="{% url 'termbook-htmx-delete' termbook.id %}"
            hx-target="#tb-row-{{ termbook.id }}"
            hx-swap="outerHTML swap:200ms"
            hx-confirm="Delete this termbook?">
      <i class="fas fa-trash"></i>
    </button>
  </td>
</tr>
```

- [ ] **Step 2: Create the table-body partial**

`_termbook_table.html`:

```django
{% for termbook in termbooks %}
  {% include "gradebookcomponent/termbook/partials/_termbook_row.html" with termbook=termbook %}
{% empty %}
  {% include "gradebookcomponent/gradebook/partials/_empty_state.html" with colspan=5 message="No termbooks found." %}
{% endfor %}
```

- [ ] **Step 3: Create the totals partial**

`_termbook_totals.html`:

```django
<tr id="tb-totals-row">
  <th></th>
  <th>Total</th>
  <th colspan="3">
    {% with total=termbooks|length %}{{ total }} termbook{{ total|pluralize }}{% endwith %}
  </th>
</tr>
```

- [ ] **Step 4: Smoke test render**

```bash
python manage.py shell -c "from django.template.loader import get_template; get_template('gradebookcomponent/termbook/partials/_termbook_table.html'); get_template('gradebookcomponent/termbook/partials/_termbook_row.html'); get_template('gradebookcomponent/termbook/partials/_termbook_totals.html'); print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/termbook/partials/
git commit -m "feat(termbook): add htmx table partials sharing gb-* design"
```

---

## Task 5: Modal forms (create/edit) for gradebook and termbook

**Files:**
- Create: `gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_form.html`
- Create: `gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_form.html`
- Modify: `gradebookcomponent/views/htmx_views.py` (replace stubs from Task 2)

- [ ] **Step 1: Identify the existing forms**

The codebase already has:
- A gradebook form used by `create_grade_book` / `update_grade_book` in `gradebookcomponent/views/gradebook_view.py`
- `TermGradeBookComponentsForm` in `gradebookcomponent/forms/term_gradebook_form.py`

Open `gradebookcomponent/views/gradebook_view.py` and confirm the gradebook form class name (search for `Form(`). Use that exact class in the new view. (If multiple, use the same one `create_grade_book` uses.)

- [ ] **Step 2: Create the gradebook form partial**

`_gradebook_form.html`:

```django
<div class="gb-modal__backdrop" hx-on:click="document.getElementById('gb-modal').innerHTML=''"></div>
<div class="gb-modal__dialog" role="dialog" aria-modal="true">
  <header class="gb-modal__header">
    <h3>{% if instance %}Edit{% else %}Add{% endif %} Gradebook Component</h3>
    <button type="button" class="gb-icon-btn" aria-label="Close"
            hx-on:click="document.getElementById('gb-modal').innerHTML=''">
      <i class="fas fa-times"></i>
    </button>
  </header>
  <form hx-post="{% if instance %}{% url 'gradebook-htmx-form-edit' instance.id %}{% else %}{% url 'gradebook-htmx-form' %}{% endif %}"
        hx-target="#gb-modal"
        hx-swap="innerHTML"
        class="gb-modal__body">
    {% csrf_token %}
    {{ form.as_p }}
    <footer class="gb-modal__footer">
      <button type="button" class="gb-btn gb-btn--ghost"
              hx-on:click="document.getElementById('gb-modal').innerHTML=''">Cancel</button>
      <button type="submit" class="gb-btn gb-btn--primary">
        {% if instance %}Save{% else %}Create{% endif %}
      </button>
    </footer>
  </form>
</div>
```

- [ ] **Step 3: Create the termbook form partial**

`_termbook_form.html`: identical structure to step 2 but with `termbook-htmx-form` / `termbook-htmx-form-edit` URLs and "Termbook" labels.

- [ ] **Step 4: Implement the gradebook form view**

Replace the stub `gradebook_htmx_form` in `htmx_views.py`:

```python
from gradebookcomponent.views.gradebook_view import (
    create_grade_book as _legacy_create,
)  # noqa - only to confirm form class location

from gradebookcomponent.forms.term_gradebook_form import TermGradeBookComponentsForm
# Import the gradebook form class — replace ImportName below with the actual class name
# discovered in Step 1 (e.g. GradeBookComponentsForm). It typically lives in
# gradebookcomponent.forms or gradebookcomponent.forms.gradebook_form.
from gradebookcomponent.forms import GradeBookComponentsForm  # adjust import to match codebase


@login_required
@_require_htmx
@require_http_methods(["GET", "POST"])
def gradebook_htmx_form(request, pk=None):
    instance = (
        get_object_or_404(GradeBookComponents, pk=pk, teacher=request.user) if pk else None
    )
    if request.method == "POST":
        form = GradeBookComponentsForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.teacher = request.user
            obj.save()
            form.save_m2m() if hasattr(form, "save_m2m") else None
            resp = render(
                request,
                "gradebookcomponent/gradebook/partials/_gradebook_row.html",
                {"component": obj},
            )
            resp["HX-Trigger"] = "gb-modal-close, gb-totals-refresh"
            resp["HX-Retarget"] = "#gb-tbody"
            resp["HX-Reswap"] = "afterbegin"
            return resp
        # fall through with errors
    else:
        form = GradeBookComponentsForm(instance=instance)
    return render(
        request,
        "gradebookcomponent/gradebook/partials/_gradebook_form.html",
        {"form": form, "instance": instance},
    )
```

If the actual form class name differs, update the import. If `create_grade_book` uses a non-`ModelForm` workflow, mirror that workflow here instead.

- [ ] **Step 5: Implement the termbook form view**

Replace the stub `termbook_htmx_form`:

```python
@login_required
@_require_htmx
@require_http_methods(["GET", "POST"])
def termbook_htmx_form(request, pk=None):
    instance = (
        get_object_or_404(TermGradeBookComponents, pk=pk, teacher=request.user) if pk else None
    )
    if request.method == "POST":
        form = TermGradeBookComponentsForm(request.POST, instance=instance)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.teacher = request.user
            obj.save()
            form.save_m2m()
            resp = render(
                request,
                "gradebookcomponent/termbook/partials/_termbook_row.html",
                {"termbook": obj},
            )
            resp["HX-Trigger"] = "tb-modal-close, tb-totals-refresh"
            resp["HX-Retarget"] = "#tb-tbody"
            resp["HX-Reswap"] = "afterbegin"
            return resp
    else:
        form = TermGradeBookComponentsForm(instance=instance)
    return render(
        request,
        "gradebookcomponent/termbook/partials/_termbook_form.html",
        {"form": form, "instance": instance},
    )
```

- [ ] **Step 6: Run system check**

```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

If imports fail, fix them based on actual form locations and re-run.

- [ ] **Step 7: Commit**

```bash
git add gradebookcomponent/views/htmx_views.py gradebookcomponent/templates/gradebookcomponent/gradebook/partials/_gradebook_form.html gradebookcomponent/templates/gradebookcomponent/termbook/partials/_termbook_form.html
git commit -m "feat(gradebook): htmx modal create/edit for gradebook + termbook"
```

---

## Task 6: Wire htmx into `grade_book.html`

**Files:**
- Modify: `gradebookcomponent/templates/gradebookcomponent/gradebook/grade_book.html`

- [ ] **Step 1: Read current structure**

```bash
grep -n "gb-table\|tbody\|tfoot\|create-grade-book\|create-term-book" gradebookcomponent/templates/gradebookcomponent/gradebook/grade_book.html
```

Identify (a) the gradebook `<tbody>` to give an id, (b) the termbook `<tbody>` to give an id, (c) the "Add" buttons to swap to htmx, (d) where to mount the modal.

- [ ] **Step 2: Add the modal mount + CSRF header at top of the page wrapper**

Inside the page's outer wrapper element, add `hx-headers='{"X-CSRFToken":"{{ csrf_token }}"}'`.

Just before the closing wrapper, add:

```django
<div id="gb-modal"
     hx-on:gb-modal-close="this.innerHTML=''"
     hx-on:tb-modal-close="this.innerHTML=''"></div>
```

- [ ] **Step 3: Replace the gradebook "Add" link**

Find the link/button that goes to `{% url 'create-grade-book' %}` in the gradebook section. Replace its `href` with htmx attrs:

```django
<button type="button" class="gb-btn gb-btn--primary"
        hx-get="{% url 'gradebook-htmx-form' %}"
        hx-target="#gb-modal"
        hx-swap="innerHTML">
  <i class="fas fa-plus"></i> Add Gradebook
</button>
```

- [ ] **Step 4: Add the search input above the gradebook table**

```django
<input type="search"
       name="q"
       placeholder="Search gradebooks…"
       class="gb-search"
       hx-get="{% url 'gradebook-htmx-list' %}"
       hx-trigger="keyup changed delay:300ms, search"
       hx-target="#gb-tbody"
       hx-swap="innerHTML">
```

- [ ] **Step 5: Give the gradebook tbody an id and the totals tfoot an id**

Change the existing gradebook `<tbody>` opening tag to `<tbody id="gb-tbody">` and the totals `<tr>` (or a wrapping `<tfoot>`) to include `id="gb-totals-row"` and:

```django
hx-get="{% url 'gradebook-htmx-totals' %}"
hx-trigger="gb-totals-refresh from:body"
hx-swap="outerHTML"
```

- [ ] **Step 6: Apply the same treatment to the termbook section** (Add button → htmx, tbody → `id="tb-tbody"`, totals row → htmx-listening, search input → uses `termbook-htmx-list`).

- [ ] **Step 7: Convert existing rows to use the new partials**

In the gradebook section, replace the `{% for component in ... %}<tr>...</tr>{% endfor %}` block with:

```django
{% for component in components %}
  {% include "gradebookcomponent/gradebook/partials/_gradebook_row.html" with component=component %}
{% endfor %}
```

Same in the termbook section using `_termbook_row.html` with `termbook=...`.

- [ ] **Step 8: Verify in browser**

Run dev server, visit `/grade-book/`, and confirm:
- Search input filters table without page reload.
- "Add Gradebook" opens a modal.
- Submit creates a row at the top, modal closes, totals refresh.
- Trash icon removes a row after confirmation.
- Same behaviors on the termbook section.

```bash
python manage.py runserver 9000
```

- [ ] **Step 9: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/gradebook/grade_book.html
git commit -m "feat(gradebook): wire htmx search/modal/delete into grade_book.html"
```

---

## Task 7: Rewrite `term_book.html` to align with gradebook design

**Files:**
- Modify: `gradebookcomponent/templates/gradebookcomponent/termbook/term_book.html`

- [ ] **Step 1: Read the existing termbook list view to confirm context keys**

```bash
sed -n '1,50p' gradebookcomponent/views/termbook_view.py
```

Note the variable names passed in (e.g. `termbooks`, `term_books`).

- [ ] **Step 2: Rewrite the page**

Replace the entire body of `term_book.html` with a layout that mirrors the structure of the termbook section in `grade_book.html`:

```django
{% extends 'base_operation.html' %}
{% block content %}
<div class="gb-page" hx-headers='{"X-CSRFToken":"{{ csrf_token }}"}'>

  <div class="gb-actions">
    <button type="button" class="gb-btn gb-btn--primary"
            hx-get="{% url 'termbook-htmx-form' %}"
            hx-target="#gb-modal"
            hx-swap="innerHTML">
      <i class="fas fa-plus"></i> Add Termbook
    </button>
  </div>

  <input type="search"
         name="q"
         placeholder="Search termbooks…"
         class="gb-search"
         hx-get="{% url 'termbook-htmx-list' %}"
         hx-trigger="keyup changed delay:300ms, search"
         hx-target="#tb-tbody"
         hx-swap="innerHTML">

  <table class="gb-table">
    <thead>
      <tr>
        <th>Subject</th>
        <th>Percentage</th>
        <th>Term</th>
        <th>Base Grade</th>
        <th class="gb-action-cell">Action</th>
      </tr>
    </thead>
    <tbody id="tb-tbody">
      {% for termbook in termbooks %}
        {% include "gradebookcomponent/termbook/partials/_termbook_row.html" with termbook=termbook %}
      {% empty %}
        {% include "gradebookcomponent/gradebook/partials/_empty_state.html" with colspan=5 message="No termbooks found." %}
      {% endfor %}
    </tbody>
    <tfoot>
      <tr id="tb-totals-row"
          hx-get="{% url 'termbook-htmx-totals' %}"
          hx-trigger="tb-totals-refresh from:body"
          hx-swap="outerHTML">
        <th></th>
        <th>Total</th>
        <th colspan="3">{{ termbooks|length }} termbook{{ termbooks|length|pluralize }}</th>
      </tr>
    </tfoot>
  </table>

  <div id="gb-modal"
       hx-on:gb-modal-close="this.innerHTML=''"
       hx-on:tb-modal-close="this.innerHTML=''"></div>
</div>
{% endblock %}
```

If the context variable from the existing view is not `termbooks`, either rename it in the view or in this template — keep them consistent.

- [ ] **Step 3: Verify in browser**

```bash
python manage.py runserver 9000
```

Visit `/term-book/` and confirm the page now visually matches the termbook section inside `/grade-book/` and behaves the same (search, modal create/edit, delete).

- [ ] **Step 4: Commit**

```bash
git add gradebookcomponent/templates/gradebookcomponent/termbook/term_book.html
git commit -m "feat(termbook): align term_book.html with gradebook design and htmx behavior"
```

---

## Task 8: Tests

**Files:**
- Create: `gradebookcomponent/tests/test_htmx_views.py`

- [ ] **Step 1: Write failing tests**

```python
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


User = get_user_model()


class HtmxGuardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t", password="p")
        self.client.force_login(self.user)

    def test_gradebook_list_requires_htmx_header(self):
        url = reverse("gradebook-htmx-list")
        plain = self.client.get(url)
        self.assertEqual(plain.status_code, 400)
        htmx = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(htmx.status_code, 200)
        self.assertTemplateUsed(
            htmx, "gradebookcomponent/gradebook/partials/_gradebook_table.html"
        )

    def test_termbook_list_requires_htmx_header(self):
        url = reverse("termbook-htmx-list")
        self.assertEqual(self.client.get(url).status_code, 400)
        r = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(
            r, "gradebookcomponent/termbook/partials/_termbook_table.html"
        )

    def test_gradebook_delete_returns_totals_trigger(self):
        # create object via ORM, then DELETE via htmx
        from gradebookcomponent.models import GradeBookComponents
        # Provide minimal valid kwargs — adjust to match your schema's required fields.
        # If the model requires foreign keys (subject, term), create them inline.
        pass  # Placeholder: extend once model schema is checked
```

- [ ] **Step 2: Run tests, confirm they fail or skip cleanly**

```bash
python manage.py test gradebookcomponent.tests.test_htmx_views -v 2
```

Expected: First two tests pass (200 + correct template). Third test currently a `pass` — extend with model fixtures matching `GradeBookComponents`' required fields, then re-run.

- [ ] **Step 3: Commit**

```bash
git add gradebookcomponent/tests/test_htmx_views.py
git commit -m "test(gradebook): cover htmx endpoint guards and templates"
```

---

## Task 9: Manual smoke test + final cleanup

- [ ] **Step 1: Run the dev server**

```bash
python manage.py runserver 9000
```

- [ ] **Step 2: Walk both pages**

For `/grade-book/`:
- Search filters gradebook + termbook tables independently without page reload.
- "Add Gradebook" opens modal; submit creates a row at top of `#gb-tbody`; modal closes; totals row updates.
- Edit pencil opens modal pre-filled; save updates the row in place.
- Trash icon: confirm dialog → row fades out → totals refresh.
- Repeat the four flows for the termbook section in the same page.

For `/term-book/`:
- Page visually matches the termbook section in `/grade-book/`.
- Same four flows work.

- [ ] **Step 3: Inspect Network tab**

Confirm htmx requests carry `HX-Request: true`, return small HTML partials (not full pages), and successful create/delete responses include `HX-Trigger` headers.

- [ ] **Step 4: Final commit if any tweaks**

```bash
git status
git add -p
git commit -m "chore(gradebook): polish htmx pilot after smoke test"
```

---

## Self-Review Notes

- Spec coverage: search ✓ (Tasks 2,6,7), modal create/edit ✓ (Task 5,6,7), row-swap delete ✓ (Tasks 2,3,4,6,7), termbook visual+behavioral alignment ✓ (Tasks 4,7), parallel htmx endpoints leaving full-page views intact ✓ (Task 2), CSRF via `hx-headers` ✓ (Task 6,7), `HX-Trigger` for totals refresh ✓ (Tasks 2,5).
- Out-of-scope items from spec (inline cell edit, other pages) intentionally absent — confirmed.
- Type/name consistency: `gradebook-htmx-list`, `gradebook-htmx-form`, `gradebook-htmx-form-edit`, `gradebook-htmx-delete`, `gradebook-htmx-totals` (and `termbook-` mirrors) used identically in views, urls, and templates.
- One known unknown: exact gradebook `Form` class name — Task 5 Step 1 explicitly directs the engineer to discover it before writing the import. This is unavoidable without running the codebase; the alternative is shipping a guess that could be wrong.
