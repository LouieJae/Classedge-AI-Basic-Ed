# Student Profile Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-page edit-profile modal, exactly-5 featured badges with collapsible "more" row, and a tier-tinted avatar ring + XP progress arc + level-up celebration to the student profile.

**Architecture:** Backend changes are additive (one new column on `StudentBadge`, one new POST endpoint, one new XHR branch on the existing `update_header_profile` view, one new template tag). All UI lives in `templates/student/profile.html` — no new global templates or scripts. Confetti runs entirely client-side, gated by `localStorage`.

**Tech Stack:** Django 4.x, Bootstrap 5 modals, vanilla JS (no framework), SweetAlert2 (already loaded), `canvas-confetti` from CDN.

**Spec:** `docs/superpowers/specs/2026-04-30-student-profile-modal-badges-level-design.md`

---

## File map

| File | Change |
|---|---|
| `gamification/models.py` | Add `is_featured` field to `StudentBadge` |
| `gamification/migrations/0002_studentbadge_is_featured.py` | New migration |
| `gamification/views.py` | Append `set_featured_badges` view |
| `gamification/urls.py` | Register `set_featured_badges` URL |
| `gamification/tests/test_featured_badges.py` | New test module |
| `gamification/templatetags/__init__.py` | New (empty) |
| `gamification/templatetags/level_tier.py` | New template tag |
| `gamification/tests/test_level_tier.py` | New tests |
| `accounts/views/user_views.py` | XHR JSON branch on `update_header_profile`; expand student branch of `profile_view` |
| `accounts/tests/test_update_header_profile_xhr.py` | New tests (path may need adjusting if `accounts/tests/` doesn't exist) |
| `templates/student/profile.html` | Avatar wrapper + level visuals; badges section restructure; edit-profile modal; manage-featured modal; JS for both modals and level-up |

---

## Phase 1 — Featured badges backend

### Task 1: Add `is_featured` field to `StudentBadge`

**Files:**
- Modify: `gamification/models.py:73-99`
- Create: `gamification/migrations/0002_studentbadge_is_featured.py`

- [ ] **Step 1: Add the field**

In `gamification/models.py`, inside `class StudentBadge`, append the new field after `award_reason`:

```python
class StudentBadge(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earned_badges",
    )
    badge = models.ForeignKey(
        BadgeDefinition,
        on_delete=models.CASCADE,
    )
    earned_at = models.DateTimeField(auto_now_add=True)
    progress_percent = models.PositiveSmallIntegerField(default=100)
    awarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manually_awarded_badges",
    )
    award_reason = models.CharField(max_length=300, blank=True, default="")
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = [("student", "badge")]

    def __str__(self):
        return f"{self.student} earned {self.badge.name}"
```

- [ ] **Step 2: Generate the migration**

```bash
python manage.py makemigrations gamification --name studentbadge_is_featured
```

Expected: creates `gamification/migrations/0002_studentbadge_is_featured.py`.

- [ ] **Step 3: Verify the migration content**

Read the generated file. It should add a single `AddField` operation for `is_featured`. If anything else appears, investigate before applying.

- [ ] **Step 4: Apply the migration**

```bash
python manage.py migrate gamification
```

Expected: `Applying gamification.0002_studentbadge_is_featured... OK`

- [ ] **Step 5: Commit**

```bash
git add gamification/models.py gamification/migrations/0002_studentbadge_is_featured.py
git commit -m "feat(gamification): add is_featured flag to StudentBadge"
```

---

### Task 2: Add `set_featured_badges` view + URL with tests

**Files:**
- Create: `gamification/tests/test_featured_badges.py`
- Modify: `gamification/views.py` (append view)
- Modify: `gamification/urls.py` (register URL)

- [ ] **Step 1: Write the failing tests**

Create `gamification/tests/test_featured_badges.py`:

```python
import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from gamification.models import BadgeDefinition, StudentBadge

User = get_user_model()


class SetFeaturedBadgesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw')
        self.other = User.objects.create_user(username='bob', password='pw')
        self.client = Client()
        self.client.login(username='alice', password='pw')
        self.badges = []
        for i in range(7):
            defn = BadgeDefinition.objects.create(
                code=f'b{i}', name=f'Badge {i}', description='d',
                tier='bronze', icon='🥉',
            )
            self.badges.append(
                StudentBadge.objects.create(student=self.user, badge=defn)
            )

    def _post(self, ids):
        return self.client.post(
            reverse('set_featured_badges'),
            json.dumps({'badge_ids': ids}),
            content_type='application/json',
        )

    def test_requires_login(self):
        self.client.logout()
        resp = self._post([b.id for b in self.badges[:5]])
        self.assertEqual(resp.status_code, 302)

    def test_rejects_count_below_5(self):
        resp = self._post([self.badges[0].id, self.badges[1].id])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_count_above_5(self):
        resp = self._post([b.id for b in self.badges[:6]])
        self.assertEqual(resp.status_code, 400)

    def test_rejects_badges_not_owned(self):
        other_defn = BadgeDefinition.objects.create(
            code='x', name='X', description='d', tier='gold', icon='🥇',
        )
        other_sb = StudentBadge.objects.create(student=self.other, badge=other_defn)
        ids = [b.id for b in self.badges[:4]] + [other_sb.id]
        resp = self._post(ids)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            StudentBadge.objects.filter(is_featured=True).count(), 0
        )

    def test_replaces_featured_set_atomically(self):
        first = [b.id for b in self.badges[:5]]
        resp = self._post(first)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            set(StudentBadge.objects
                .filter(student=self.user, is_featured=True)
                .values_list('id', flat=True)),
            set(first),
        )

        second = [b.id for b in self.badges[2:7]]
        resp = self._post(second)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            set(StudentBadge.objects
                .filter(student=self.user, is_featured=True)
                .values_list('id', flat=True)),
            set(second),
        )

    def test_get_method_not_allowed(self):
        resp = self.client.get(reverse('set_featured_badges'))
        self.assertEqual(resp.status_code, 405)

    def test_invalid_json(self):
        resp = self.client.post(
            reverse('set_featured_badges'),
            'not json',
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test gamification.tests.test_featured_badges -v 2
```

Expected: errors about `set_featured_badges` URL not existing (`NoReverseMatch`).

- [ ] **Step 3: Add the view**

Append to `gamification/views.py` (top of file: add `import json as _json` and `from django.http import JsonResponse` if not already imported; check first to avoid duplicates):

```python
import json as _json
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def set_featured_badges(request):
    try:
        payload = _json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    ids = payload.get('badge_ids')
    if not isinstance(ids, list) or len(ids) != 5:
        return JsonResponse(
            {'error': 'Exactly 5 badges must be selected.'}, status=400
        )

    try:
        ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid badge id.'}, status=400)

    owned_count = StudentBadge.objects.filter(
        student=request.user, id__in=ids
    ).count()
    if owned_count != 5:
        return JsonResponse(
            {'error': 'One or more badges are not yours.'}, status=400
        )

    with transaction.atomic():
        StudentBadge.objects.filter(
            student=request.user, is_featured=True
        ).update(is_featured=False)
        StudentBadge.objects.filter(
            student=request.user, id__in=ids
        ).update(is_featured=True)

    return JsonResponse({'featured_ids': ids}, status=200)
```

Note: `json` is already imported as the standard library; if the file uses a different alias check before adding. The `_json` alias here avoids any clash.

- [ ] **Step 4: Register the URL**

In `gamification/urls.py`, inside `urlpatterns`, add right after the existing badges-management URLs (around line 22):

```python
    path("gamification/badges/featured/", views.set_featured_badges, name="set_featured_badges"),
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python manage.py test gamification.tests.test_featured_badges -v 2
```

Expected: all 7 tests pass.

- [ ] **Step 6: Commit**

```bash
git add gamification/views.py gamification/urls.py gamification/tests/test_featured_badges.py
git commit -m "feat(gamification): add set_featured_badges endpoint"
```

---

## Phase 2 — Level tier template tag

### Task 3: Add `level_tier` template tag with tests

**Files:**
- Create: `gamification/templatetags/__init__.py` (empty)
- Create: `gamification/templatetags/level_tier.py`
- Create: `gamification/tests/test_level_tier.py`

- [ ] **Step 1: Write the failing tests**

Create `gamification/tests/test_level_tier.py`:

```python
from django.test import TestCase
from gamification.templatetags.level_tier import level_tier


class LevelTierTests(TestCase):
    def test_bronze_band(self):
        self.assertEqual(level_tier(1), 'bronze')
        self.assertEqual(level_tier(9), 'bronze')

    def test_silver_band(self):
        self.assertEqual(level_tier(10), 'silver')
        self.assertEqual(level_tier(19), 'silver')

    def test_gold_band(self):
        self.assertEqual(level_tier(20), 'gold')
        self.assertEqual(level_tier(29), 'gold')

    def test_platinum_band(self):
        self.assertEqual(level_tier(30), 'platinum')
        self.assertEqual(level_tier(49), 'platinum')

    def test_diamond_band(self):
        self.assertEqual(level_tier(50), 'diamond')
        self.assertEqual(level_tier(999), 'diamond')

    def test_zero_or_none_falls_back_to_bronze(self):
        self.assertEqual(level_tier(0), 'bronze')
        self.assertEqual(level_tier(None), 'bronze')
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python manage.py test gamification.tests.test_level_tier -v 2
```

Expected: `ImportError` — `level_tier` module does not exist.

- [ ] **Step 3: Create the template tag package**

Create `gamification/templatetags/__init__.py` (empty file):

```python
```

Create `gamification/templatetags/level_tier.py`:

```python
from django import template

register = template.Library()


@register.filter(name='level_tier')
def level_tier(level):
    """Return tier slug for a level integer.

    Bands: 1-9 bronze, 10-19 silver, 20-29 gold, 30-49 platinum, 50+ diamond.
    Falsy/None defaults to bronze.
    """
    try:
        n = int(level or 0)
    except (TypeError, ValueError):
        return 'bronze'
    if n >= 50:
        return 'diamond'
    if n >= 30:
        return 'platinum'
    if n >= 20:
        return 'gold'
    if n >= 10:
        return 'silver'
    return 'bronze'
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python manage.py test gamification.tests.test_level_tier -v 2
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add gamification/templatetags/ gamification/tests/test_level_tier.py
git commit -m "feat(gamification): add level_tier template tag"
```

---

## Phase 3 — Profile view: pass partitioned badges, tier, XP

### Task 4: Expand student branch of `profile_view`

**Files:**
- Modify: `accounts/views/user_views.py:955-983`

- [ ] **Step 1: Update the student branch**

Replace the `if viewer_role == 'student':` block in `profile_view` (currently at `accounts/views/user_views.py:955-983`) with:

```python
    if viewer_role == 'student':
        from gamification.models import StudentBadge, StudentGamification, BadgeDefinition
        earned = (
            StudentBadge.objects
            .filter(student=profile.user)
            .select_related('badge')
            .order_by('-is_featured', '-earned_at')
        )
        earned_list = list(earned)
        earned_badge_ids = {sb.badge_id for sb in earned_list}
        upcoming_badges = (
            BadgeDefinition.objects
            .filter(is_active=True, target_role='student')
            .exclude(id__in=earned_badge_ids)
            .exclude(tier='hidden')
            .order_by('tier', 'name')[:6]
        )
        try:
            gamification = profile.user.gamification
        except StudentGamification.DoesNotExist:
            gamification = None

        featured_badges = [sb for sb in earned_list if sb.is_featured]
        other_badges = [sb for sb in earned_list if not sb.is_featured]

        current_level = gamification.current_level if gamification else 1
        total_xp = gamification.total_xp if gamification else 0
        current_level_floor = (current_level ** 2) * 100
        next_level_floor = ((current_level + 1) ** 2) * 100
        xp_into_level = max(0, total_xp - current_level_floor)
        xp_span = max(1, next_level_floor - current_level_floor)
        xp_progress_pct = min(100, int((xp_into_level / xp_span) * 100))

        context.update({
            'earned_badges': earned_list,
            'earned_count': len(earned_list),
            'featured_badges': featured_badges,
            'other_badges': other_badges,
            'upcoming_badges': upcoming_badges,
            'gamification': gamification,
            'is_own_profile': profile.user_id == request.user.id,
            'current_level': current_level,
            'xp_into_level': xp_into_level,
            'xp_for_next_level': xp_span,
            'xp_progress_pct': xp_progress_pct,
        })
        return render(request, 'student/profile.html', context)
```

- [ ] **Step 2: Smoke-test the view**

```bash
python manage.py check
```

Expected: `System check identified no issues`.

- [ ] **Step 3: Commit**

```bash
git add accounts/views/user_views.py
git commit -m "feat(profile): partition badges and expose level/XP context"
```

---

## Phase 4 — Profile template: level visuals + badges restructure

### Task 5: Add tier ring, level pill, and XP arc to the avatar

**Files:**
- Modify: `templates/student/profile.html` (top of file: load tag; hero block: avatar wrapper + CSS; styles block)

- [ ] **Step 1: Load the template tag at the top**

In `templates/student/profile.html`, after the existing `{% load static %}`, add:

```django
{% load level_tier %}
```

- [ ] **Step 2: Add CSS for tier ring, pill, and arc**

In the existing `<style>` block (after `.profile-photo` rules around line 49), append:

```css
  .profile-photo-wrap {
    position: relative;
    width: 130px;
    height: 130px;
    flex-shrink: 0;
  }
  .profile-photo-wrap .profile-photo {
    position: absolute;
    inset: 10px;
    width: auto; height: auto;
  }
  .profile-photo.tier-bronze   { border-color: #cd7f32; box-shadow: 0 0 0 4px rgba(205,127,50,0.18); }
  .profile-photo.tier-silver   { border-color: #c0c0c0; box-shadow: 0 0 0 4px rgba(192,192,192,0.20); }
  .profile-photo.tier-gold     { border-color: var(--gold); box-shadow: 0 0 0 4px var(--gold-glow); }
  .profile-photo.tier-platinum { border-color: #e5e4e2; box-shadow: 0 0 0 4px rgba(229,228,226,0.22); }
  .profile-photo.tier-diamond  { border-color: #b9f2ff; box-shadow: 0 0 0 4px rgba(185,242,255,0.28); }

  .xp-ring {
    position: absolute;
    inset: 0;
    width: 130px;
    height: 130px;
    transform: rotate(-90deg);
    pointer-events: none;
  }
  .xp-ring .xp-ring-track {
    fill: none;
    stroke: rgba(255,255,255,0.06);
    stroke-width: 4;
  }
  .xp-ring .xp-ring-arc {
    fill: none;
    stroke-width: 4;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.9s ease-out;
  }
  .xp-ring.tier-bronze   .xp-ring-arc { stroke: #cd7f32; }
  .xp-ring.tier-silver   .xp-ring-arc { stroke: #c0c0c0; }
  .xp-ring.tier-gold     .xp-ring-arc { stroke: var(--gold); }
  .xp-ring.tier-platinum .xp-ring-arc { stroke: #e5e4e2; }
  .xp-ring.tier-diamond  .xp-ring-arc { stroke: #b9f2ff; }

  .level-pill {
    position: absolute;
    bottom: 4px;
    right: 4px;
    padding: 3px 9px;
    border-radius: 100px;
    font-family: var(--display);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #0a0f1f;
    box-shadow: 0 2px 6px rgba(0,0,0,0.35);
  }
  .level-pill.tier-bronze   { background: #cd7f32; }
  .level-pill.tier-silver   { background: #c0c0c0; }
  .level-pill.tier-gold     { background: var(--gold); }
  .level-pill.tier-platinum { background: #e5e4e2; }
  .level-pill.tier-diamond  { background: #b9f2ff; }
```

- [ ] **Step 3: Wrap the avatar with ring + pill**

Replace the existing `<div class="profile-photo">…</div>` block in the hero (around line 432-438) with:

```django
      {% with tier=current_level|level_tier %}
      <div class="profile-photo-wrap" data-current-level="{{ current_level }}" data-tier="{{ tier }}">
        <svg class="xp-ring tier-{{ tier }}" viewBox="0 0 130 130" aria-hidden="true">
          <circle class="xp-ring-track" cx="65" cy="65" r="62"></circle>
          <circle class="xp-ring-arc" cx="65" cy="65" r="62"
                  pathLength="100"
                  stroke-dasharray="100"
                  stroke-dashoffset="{{ 100|add:0|stringformat:'d' }}"
                  data-progress="{{ xp_progress_pct }}"></circle>
        </svg>
        <div class="profile-photo tier-{{ tier }}">
          {% if profile.student_photo %}
            <img src="{{ profile.student_photo.url }}" alt="{{ profile.first_name }} {{ profile.last_name }}" />
          {% else %}
            {{ profile.first_name|slice:":1"|upper }}{{ profile.last_name|slice:":1"|upper }}
          {% endif %}
        </div>
        <span class="level-pill tier-{{ tier }}" title="XP {{ xp_into_level }} / {{ xp_for_next_level }}">Lv {{ current_level }}</span>
      </div>
      {% endwith %}
```

The `stroke-dashoffset` starts at 100 (empty); JS will animate it to the target on load.

- [ ] **Step 4: Add the load-time arc animation (inline JS, end of `{% block content %}`)**

At the very end of the file, just before `{% endblock %}` (the final one), add:

```django
<script>
(function () {
  const arc = document.querySelector('.xp-ring .xp-ring-arc');
  if (!arc) return;
  const progress = parseInt(arc.dataset.progress || '0', 10);
  // dashoffset = 100 - progress (since pathLength is normalized to 100)
  requestAnimationFrame(() => {
    arc.setAttribute('stroke-dashoffset', String(Math.max(0, 100 - progress)));
  });
})();
</script>
```

- [ ] **Step 5: Manual smoke check**

Start the dev server and load the student profile. Verify the tier ring, level pill, and XP arc render. The arc should animate from 0 to its target on load.

```bash
python manage.py runserver
```

Then visit `/profile_view/<your_user_id>/` as a logged-in student.

- [ ] **Step 6: Commit**

```bash
git add templates/student/profile.html
git commit -m "feat(profile): tier-tinted avatar ring, level pill, and XP arc"
```

---

### Task 6: Restructure the badges section into Featured + More

**Files:**
- Modify: `templates/student/profile.html` (badges section + styles)

- [ ] **Step 1: Add styles for the More toggle and empty featured slot**

In the existing `<style>` block, after the `.badges-empty` rules (around line 248), append:

```css
  .featured-empty-slot {
    background: var(--surface-2);
    border: 1px dashed var(--border);
    border-radius: 12px;
    padding: 16px 12px 14px;
    text-align: center;
    color: var(--text-muted);
    font-size: 11.5px;
    cursor: pointer;
    display: grid;
    place-items: center;
    min-height: 110px;
    transition: border-color 0.18s, color 0.18s;
  }
  .featured-empty-slot:hover {
    border-color: var(--gold);
    color: var(--gold);
  }
  .more-badges {
    margin-top: 18px;
  }
  .more-badges-toggle {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-dim);
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 100px;
    cursor: pointer;
    transition: border-color 0.18s, color 0.18s;
  }
  .more-badges-toggle:hover {
    border-color: var(--gold);
    color: var(--gold);
  }
  .more-badges-grid { margin-top: 12px; }
  .more-badges-grid[hidden] { display: none; }
  .manage-featured-btn {
    background: transparent;
    border: 1px solid var(--gold);
    color: var(--gold);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 6px 12px;
    border-radius: 100px;
    cursor: pointer;
    transition: background 0.18s, color 0.18s;
  }
  .manage-featured-btn:hover {
    background: var(--gold);
    color: #0a0f1f;
  }
  .manage-featured-btn:disabled {
    border-color: var(--border);
    color: var(--text-muted);
    background: transparent;
    cursor: not-allowed;
  }
```

- [ ] **Step 2: Replace the badges section markup**

Replace the entire badges section (currently lines ~490-531, the `<section class="profile-section">` containing `Badges`) with:

```django
    <section class="profile-section">
      <div class="profile-section-head">
        <h2 class="profile-section-title">Badges</h2>
        <div style="display:flex; gap:10px; align-items:center;">
          <span class="profile-section-count">{{ earned_count }} earned</span>
          {% if is_own_profile %}
            <button type="button" class="manage-featured-btn" id="manageFeaturedBtn"
                    {% if earned_count < 5 %}disabled title="Earn 5 badges to unlock"{% endif %}>
              <i class="fas fa-star"></i> Manage Featured
            </button>
          {% endif %}
        </div>
      </div>

      {% if featured_badges or is_own_profile and earned_count >= 5 %}
        <div class="badges-grid" id="featuredBadgesGrid">
          {% for sb in featured_badges %}
            <div class="badge-tile" title="{{ sb.badge.description }} &middot; Earned {{ sb.earned_at|date:'M j, Y' }}">
              <span class="badge-icon">{{ sb.badge.icon }}</span>
              <div class="badge-name">{{ sb.badge.name }}</div>
              <span class="badge-tier {{ sb.badge.tier }}">{{ sb.badge.tier }}</span>
            </div>
          {% endfor %}
          {% if is_own_profile %}
            {% with empty_slots=5|add:0 %}
              {% for _ in "12345" %}
                {% if forloop.counter > featured_badges|length %}
                  <div class="featured-empty-slot" data-open-manage="1">
                    <span><i class="fas fa-plus"></i><br>Pick a featured badge</span>
                  </div>
                {% endif %}
              {% endfor %}
            {% endwith %}
          {% endif %}
        </div>
      {% elif earned_badges %}
        {# Viewer with no featured curation yet — show all earned in regular grid #}
        <div class="badges-grid">
          {% for sb in earned_badges %}
            <div class="badge-tile" title="{{ sb.badge.description }} &middot; Earned {{ sb.earned_at|date:'M j, Y' }}">
              <span class="badge-icon">{{ sb.badge.icon }}</span>
              <div class="badge-name">{{ sb.badge.name }}</div>
              <span class="badge-tier {{ sb.badge.tier }}">{{ sb.badge.tier }}</span>
            </div>
          {% endfor %}
        </div>
      {% else %}
        <div class="badges-empty">
          <i class="fas fa-medal"></i>
          No badges earned yet. Complete activities and keep your streak going to start collecting!
        </div>
      {% endif %}

      {% if other_badges and featured_badges %}
        <div class="more-badges">
          <button type="button" class="more-badges-toggle" id="toggleMoreBadges"
                  aria-expanded="false" aria-controls="moreBadgesGrid">
            Show more badges ({{ other_badges|length }})
          </button>
          <div class="badges-grid more-badges-grid" id="moreBadgesGrid" hidden>
            {% for sb in other_badges %}
              <div class="badge-tile" title="{{ sb.badge.description }} &middot; Earned {{ sb.earned_at|date:'M j, Y' }}">
                <span class="badge-icon">{{ sb.badge.icon }}</span>
                <div class="badge-name">{{ sb.badge.name }}</div>
                <span class="badge-tier {{ sb.badge.tier }}">{{ sb.badge.tier }}</span>
              </div>
            {% endfor %}
          </div>
        </div>
      {% endif %}

      {% if upcoming_badges %}
        <div class="profile-section-head" style="margin-top: 26px;">
          <h2 class="profile-section-title" style="font-size: 14px; opacity: 0.8;">Up next</h2>
          <span class="profile-section-count">Locked</span>
        </div>
        <div class="upcoming-list">
          {% for b in upcoming_badges %}
            <div class="upcoming-row">
              <div class="upcoming-icon">{{ b.icon }}</div>
              <div class="upcoming-info">
                <div class="upcoming-name">{{ b.name }}</div>
                <div class="upcoming-desc">{{ b.description }}</div>
              </div>
              <span class="badge-tier {{ b.tier }}">{{ b.tier }}</span>
            </div>
          {% endfor %}
        </div>
      {% endif %}
    </section>
```

- [ ] **Step 3: Add the toggle JS**

Add to the same trailing `<script>` block introduced in Task 5 (or create a new one if Task 5's was self-contained):

```javascript
(function () {
  const btn = document.getElementById('toggleMoreBadges');
  const grid = document.getElementById('moreBadgesGrid');
  if (!btn || !grid) return;
  btn.addEventListener('click', () => {
    const isHidden = grid.hasAttribute('hidden');
    if (isHidden) {
      grid.removeAttribute('hidden');
      btn.setAttribute('aria-expanded', 'true');
      btn.textContent = 'Show fewer badges';
    } else {
      grid.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', 'false');
      const count = grid.querySelectorAll('.badge-tile').length;
      btn.textContent = `Show more badges (${count})`;
    }
  });
})();
```

- [ ] **Step 4: Manual smoke check**

Reload the profile. Verify:
- A user with 0 featured shows the "Pick a featured badge" placeholders (when ≥5 earned).
- A user with featured + extras shows a "Show more badges (N)" toggle that expands/collapses.
- A viewer who isn't the owner sees the same grid but no Manage button or empty slots.

- [ ] **Step 5: Commit**

```bash
git add templates/student/profile.html
git commit -m "feat(profile): split badges into Featured (5) and More with toggle"
```

---

### Task 7: Build the Manage Featured Badges modal

**Files:**
- Modify: `templates/student/profile.html` (modal markup + JS)

- [ ] **Step 1: Add modal styles**

Append to the `<style>` block:

```css
  .featured-modal .modal-content {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }
  .featured-modal .modal-header,
  .featured-modal .modal-footer {
    border-color: var(--border);
  }
  .featured-modal .modal-title {
    font-family: var(--display);
    font-weight: 600;
  }
  .featured-modal .featured-counter {
    font-size: 12px;
    color: var(--text-dim);
    font-weight: 600;
    letter-spacing: 0.04em;
  }
  .featured-modal .featured-counter.full { color: var(--gold); }
  .featured-modal .featured-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
    max-height: 420px;
    overflow-y: auto;
    padding: 4px;
  }
  .featured-modal .featured-tile {
    position: relative;
    background: var(--surface-2);
    border: 2px solid var(--border);
    border-radius: 12px;
    padding: 14px 10px 12px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.15s, transform 0.15s;
  }
  .featured-modal .featured-tile:hover { transform: translateY(-1px); }
  .featured-modal .featured-tile.selected {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px var(--gold-glow);
  }
  .featured-modal .featured-tile input { display: none; }
  .featured-modal .featured-tile .check-mark {
    position: absolute;
    top: 6px;
    right: 6px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--gold);
    color: #0a0f1f;
    display: none;
    place-items: center;
    font-size: 10px;
  }
  .featured-modal .featured-tile.selected .check-mark { display: grid; }
  .featured-modal .featured-error {
    color: var(--coral);
    font-size: 12px;
    margin-top: 8px;
    min-height: 16px;
  }
```

- [ ] **Step 2: Add the modal markup**

Right before the closing `</div>` of `.profile-page` (just before the final closing of the page wrapper), insert:

```django
{% if is_own_profile %}
<div class="modal fade featured-modal" id="featuredBadgesModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <div>
          <h5 class="modal-title">Pick your 5 featured badges</h5>
          <div class="featured-counter" id="featuredCounter"><span id="featuredCount">0</span> / 5 selected</div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <div class="featured-grid" id="featuredGrid">
          {% for sb in earned_badges %}
            <label class="featured-tile {% if sb.is_featured %}selected{% endif %}" data-badge-id="{{ sb.id }}">
              <input type="checkbox" value="{{ sb.id }}" {% if sb.is_featured %}checked{% endif %}>
              <span class="badge-icon" style="font-size:26px;">{{ sb.badge.icon }}</span>
              <div class="badge-name" style="font-size:12px; margin-top:6px;">{{ sb.badge.name }}</div>
              <span class="check-mark"><i class="fas fa-check"></i></span>
            </label>
          {% endfor %}
        </div>
        <div class="featured-error" id="featuredError"></div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
        <button type="button" class="btn btn-primary" id="featuredSaveBtn" disabled>Save</button>
      </div>
    </div>
  </div>
</div>
{% endif %}
```

- [ ] **Step 3: Add the modal JS**

Add to the trailing `<script>` block:

```javascript
(function () {
  const openBtn = document.getElementById('manageFeaturedBtn');
  const modalEl = document.getElementById('featuredBadgesModal');
  if (!openBtn || !modalEl || typeof bootstrap === 'undefined') return;
  const modal = new bootstrap.Modal(modalEl);
  const grid = document.getElementById('featuredGrid');
  const counterEl = document.getElementById('featuredCount');
  const counterWrap = document.getElementById('featuredCounter');
  const saveBtn = document.getElementById('featuredSaveBtn');
  const errorEl = document.getElementById('featuredError');

  function getCSRFToken() {
    return document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';
  }

  function selectedTiles() {
    return grid.querySelectorAll('.featured-tile.selected');
  }

  function updateState() {
    const count = selectedTiles().length;
    counterEl.textContent = String(count);
    counterWrap.classList.toggle('full', count === 5);
    saveBtn.disabled = count !== 5;
    if (count === 5) errorEl.textContent = '';
  }

  grid.addEventListener('click', (e) => {
    const tile = e.target.closest('.featured-tile');
    if (!tile) return;
    e.preventDefault();
    const isSelected = tile.classList.contains('selected');
    if (!isSelected && selectedTiles().length >= 5) {
      errorEl.textContent = 'You can only feature 5 badges. Deselect one first.';
      return;
    }
    tile.classList.toggle('selected');
    const input = tile.querySelector('input[type=checkbox]');
    if (input) input.checked = tile.classList.contains('selected');
    updateState();
  });

  openBtn.addEventListener('click', () => {
    errorEl.textContent = '';
    updateState();
    modal.show();
  });

  // Empty-slot tiles in the featured grid also open the modal
  document.querySelectorAll('.featured-empty-slot[data-open-manage]').forEach(el => {
    el.addEventListener('click', () => modal.show());
  });

  saveBtn.addEventListener('click', async () => {
    const ids = Array.from(selectedTiles()).map(t => parseInt(t.dataset.badgeId, 10));
    if (ids.length !== 5) return;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';
    errorEl.textContent = '';
    try {
      const res = await fetch('/gamification/badges/featured/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken() },
        body: JSON.stringify({ badge_ids: ids }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || 'Save failed.');
      window.location.reload();
    } catch (err) {
      errorEl.textContent = err.message || 'Couldn\'t save. Try again.';
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
    }
  });

  updateState();
})();
```

- [ ] **Step 4: Manual smoke check**

- Click "Manage Featured" → modal opens with current featured pre-checked.
- Try to select a 6th → inline error appears.
- Deselect, select another → counter updates, Save enables when exactly 5 are picked.
- Save → page reloads with the new featured set.
- Click an empty-slot placeholder in the featured grid → modal opens.

- [ ] **Step 5: Commit**

```bash
git add templates/student/profile.html
git commit -m "feat(profile): manage featured badges modal"
```

---

## Phase 5 — Edit Profile modal

### Task 8: Add XHR JSON branch to `update_header_profile` with tests

**Files:**
- Modify: `accounts/views/user_views.py:1038-1084`
- Create: `accounts/tests/test_update_header_profile_xhr.py`

- [ ] **Step 1: Confirm `accounts/tests/` exists; create if missing**

```bash
test -d accounts/tests || mkdir -p accounts/tests && touch accounts/tests/__init__.py
ls accounts/tests
```

- [ ] **Step 2: Write the failing tests**

Create `accounts/tests/test_update_header_profile_xhr.py`:

```python
import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import Profile

User = get_user_model()


class UpdateHeaderProfileXHRTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw')
        # Profile may or may not exist depending on signals; ensure one exists.
        self.profile, _ = Profile.objects.get_or_create(user=self.user)
        self.client = Client()
        self.client.login(username='alice', password='pw')
        self.url = reverse('update_header_profile', kwargs={'user_id': self.user.id})

    def test_xhr_success_returns_json_with_redirect(self):
        resp = self.client.post(
            self.url,
            data={'phone_number': '+639170000000', 'address': '123 Test St'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body.get('ok'))
        self.assertIn('redirect', body)

    def test_xhr_validation_error_returns_400_json(self):
        # Past-date is fine; future date should be rejected by the existing view logic.
        resp = self.client.post(
            self.url,
            data={'date_of_birth': '2999-01-01'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertFalse(body.get('ok'))
        self.assertIn('errors', body)

    def test_non_xhr_still_redirects(self):
        resp = self.client.post(
            self.url,
            data={'phone_number': '+639170000000'},
        )
        self.assertEqual(resp.status_code, 302)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python manage.py test accounts.tests.test_update_header_profile_xhr -v 2
```

Expected: failures on JSON shape (current view always redirects/renders HTML).

- [ ] **Step 4: Modify the view to add the XHR branch**

In `accounts/views/user_views.py`, find `update_header_profile` (around line 1039). Add the XHR helper and branch the responses. Replace the existing function body with:

```python
@login_required  
def update_header_profile(request, user_id):
    profile = get_object_or_404(Profile, user_id=user_id)

    if profile.user != request.user and not request.user.has_perm('accounts.change_profile'):
        return HttpResponseForbidden("You are not allowed to edit this profile.")

    is_xhr = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = StudentUpdateForm(request.POST, request.FILES, instance=profile)

        upload = request.FILES.get('student_photo')
        image_errs = validate_image_file(upload)
        if image_errs:
            if is_xhr:
                return JsonResponse(
                    {'ok': False, 'errors': {'student_photo': image_errs}},
                    status=400,
                )
            for err in image_errs:
                messages.error(request, err, extra_tags='profile_edit')
            url = reverse('view_profile_header', kwargs={'pk': profile.user.id})
            return redirect(f"{url}?edit=1")

        if form.is_valid():
            dob = form.cleaned_data.get('date_of_birth')
            if dob and dob > date.today():
                if is_xhr:
                    return JsonResponse(
                        {'ok': False, 'errors': {'date_of_birth': ['Birthday cannot be in the future.']}},
                        status=400,
                    )
                messages.error(request, 'Birthday cannot be in the future.', extra_tags='profile_edit')
                url = reverse('view_profile_header', kwargs={'pk': profile.user.id})
                return redirect(f"{url}?edit=1")

            updated_profile = form.save(commit=False)
            updated_profile.user = profile.user
            uploaded_photo = form.cleaned_data.get('student_photo')
            updated_profile.save()

            if uploaded_photo:
                Attachment.objects.create(
                    profile=updated_profile,
                    file=updated_profile.student_photo
                )

            if is_xhr:
                return JsonResponse(
                    {
                        'ok': True,
                        'redirect': reverse('view_profile_header', kwargs={'pk': profile.user.id}),
                    },
                    status=200,
                )
            messages.success(request, 'Profile updated successfully.')
            return redirect('view_profile_header', pk=profile.user.id)

        if is_xhr:
            return JsonResponse(
                {'ok': False, 'errors': form.errors},
                status=400,
            )
        return render(
            request,
            'accounts/user_level/update_header_profile.html',
            {'form': form, 'profile': profile}
        )
    else:
        form = StudentUpdateForm(instance=profile)

    return render(request, 'accounts/user_level/update_header_profile.html', {'form': form, 'profile': profile})
```

If `JsonResponse` isn't imported in the file, add it at the top: `from django.http import JsonResponse`.

- [ ] **Step 5: Run tests to verify they pass**

```bash
python manage.py test accounts.tests.test_update_header_profile_xhr -v 2
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add accounts/views/user_views.py accounts/tests/
git commit -m "feat(accounts): XHR JSON branch on update_header_profile"
```

---

### Task 9: Build the Edit Profile modal in the template

**Files:**
- Modify: `templates/student/profile.html` (replace the Edit button anchor with a modal trigger; add modal markup; add JS)

- [ ] **Step 1: Add modal styles**

Append to the `<style>` block:

```css
  .edit-profile-modal .modal-content {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }
  .edit-profile-modal .modal-header,
  .edit-profile-modal .modal-footer {
    border-color: var(--border);
  }
  .edit-profile-modal label.form-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    font-weight: 600;
  }
  .edit-profile-modal .form-control,
  .edit-profile-modal .form-select {
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border);
  }
  .edit-profile-modal .form-control:focus,
  .edit-profile-modal .form-select:focus {
    border-color: var(--gold);
    box-shadow: 0 0 0 3px var(--gold-glow);
    background: var(--surface);
  }
  .edit-profile-modal .form-control[disabled],
  .edit-profile-modal .form-control[readonly] {
    opacity: 0.7;
    cursor: not-allowed;
  }
  .edit-profile-modal .field-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }
  .edit-profile-modal .photo-preview {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid var(--border);
    background: var(--surface-2);
  }
  .edit-profile-modal .field-error {
    color: var(--coral);
    font-size: 12px;
    margin-top: 4px;
    min-height: 14px;
  }
  .edit-profile-modal .form-control.is-invalid,
  .edit-profile-modal .form-select.is-invalid {
    border-color: var(--coral);
  }
```

- [ ] **Step 2: Replace the Edit Profile anchor with a modal trigger**

Find the `is_own_profile` profile-actions block (currently around line 451-455) and change the anchor to a button:

```django
        {% if is_own_profile %}
          <div class="profile-actions">
            <button type="button" class="profile-action primary" data-bs-toggle="modal" data-bs-target="#editProfileModal">
              <i class="fas fa-pen"></i> Edit Profile
            </button>
          </div>
        {% endif %}
```

- [ ] **Step 3: Add the modal markup**

Insert near the bottom of the page (just after the Manage Featured modal added in Task 7, or near the closing `</div>` of `.profile-page`):

```django
{% if is_own_profile %}
<div class="modal fade edit-profile-modal" id="editProfileModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content">
      <form id="editProfileForm" enctype="multipart/form-data" method="post"
            action="{% url 'update_header_profile' user_id=profile.user.id %}">
        {% csrf_token %}
        <div class="modal-header">
          <h5 class="modal-title">Edit Profile</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-12 d-flex align-items-center gap-3">
              {% if profile.student_photo %}
                <img src="{{ profile.student_photo.url }}" class="photo-preview" id="photoPreview" alt="">
              {% else %}
                <div class="photo-preview d-grid" style="place-items:center;">{{ profile.first_name|slice:":1"|upper }}</div>
              {% endif %}
              <div class="flex-grow-1">
                <label class="form-label" for="id_student_photo">Photo</label>
                <input type="file" name="student_photo" id="id_student_photo" class="form-control" accept="image/*">
                <div class="field-error" data-error-for="student_photo"></div>
              </div>
            </div>

            <div class="col-md-6">
              <label class="form-label" for="id_phone_number">Phone number</label>
              <input type="text" name="phone_number" id="id_phone_number" class="form-control"
                     value="{{ profile.phone_number|default:'+63' }}">
              <div class="field-error" data-error-for="phone_number"></div>
            </div>

            <div class="col-md-6">
              <label class="form-label" for="id_gender">Gender</label>
              <select name="gender" id="id_gender" class="form-select">
                <option value="">—</option>
                <option value="Male"   {% if profile.gender == 'Male' %}selected{% endif %}>Male</option>
                <option value="Female" {% if profile.gender == 'Female' %}selected{% endif %}>Female</option>
                <option value="Other"  {% if profile.gender == 'Other' %}selected{% endif %}>Other</option>
              </select>
              <div class="field-error" data-error-for="gender"></div>
            </div>

            <div class="col-md-6">
              <label class="form-label" for="id_date_of_birth">Date of birth</label>
              <input type="date" name="date_of_birth" id="id_date_of_birth" class="form-control"
                     value="{{ profile.date_of_birth|date:'Y-m-d' }}">
              <div class="field-error" data-error-for="date_of_birth"></div>
            </div>

            <div class="col-md-6">
              <label class="form-label" for="id_address">Address</label>
              <textarea name="address" id="id_address" class="form-control" rows="2">{{ profile.address|default:'' }}</textarea>
              <div class="field-error" data-error-for="address"></div>
            </div>

            <div class="col-12"><hr style="border-color: var(--border);"></div>

            <div class="col-md-4">
              <label class="form-label">ID number</label>
              <input type="text" class="form-control" value="{{ profile.id_number|default:'—' }}" disabled>
              <div class="field-hint">Managed by registrar</div>
            </div>
            <div class="col-md-4">
              <label class="form-label">Course</label>
              <input type="text" class="form-control" value="{{ profile.course|default:'—' }}" disabled>
              <div class="field-hint">Managed by registrar</div>
            </div>
            <div class="col-md-4">
              <label class="form-label">Year level</label>
              <input type="text" class="form-control" value="{{ profile.grade_year_level|default:'—' }}" disabled>
              <div class="field-hint">Managed by registrar</div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <div class="field-error me-auto" id="editProfileFormError"></div>
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary" id="editProfileSubmit">Save Changes</button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endif %}
```

- [ ] **Step 4: Add the modal submission JS**

Add to the trailing `<script>` block:

```javascript
(function () {
  const form = document.getElementById('editProfileForm');
  if (!form) return;
  const submitBtn = document.getElementById('editProfileSubmit');
  const formError = document.getElementById('editProfileFormError');
  const photoInput = document.getElementById('id_student_photo');
  const photoPreview = document.getElementById('photoPreview');

  function getCSRFToken() {
    return document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';
  }

  function clearErrors() {
    formError.textContent = '';
    form.querySelectorAll('.field-error').forEach(el => { el.textContent = ''; });
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
  }

  function applyErrors(errors) {
    Object.entries(errors || {}).forEach(([field, msgs]) => {
      const target = form.querySelector(`[data-error-for="${field}"]`);
      const input = form.querySelector(`[name="${field}"]`);
      const text = Array.isArray(msgs) ? msgs.join(' ') : String(msgs);
      if (target) target.textContent = text;
      if (input) input.classList.add('is-invalid');
    });
  }

  if (photoInput && photoPreview) {
    photoInput.addEventListener('change', () => {
      const file = photoInput.files && photoInput.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => { photoPreview.src = e.target.result; };
      reader.readAsDataURL(file);
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving…';
    try {
      const fd = new FormData(form);
      const res = await fetch(form.action, {
        method: 'POST',
        body: fd,
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCSRFToken(),
        },
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.ok) {
        window.location.href = data.redirect || window.location.href;
        return;
      }
      if (data && data.errors) {
        applyErrors(data.errors);
        formError.textContent = 'Please fix the errors above.';
      } else {
        formError.textContent = 'Couldn\'t save. Try again.';
      }
    } catch (err) {
      formError.textContent = 'Network error. Please try again.';
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Save Changes';
    }
  });
})();
```

- [ ] **Step 5: Manual smoke check**

- Click "Edit Profile" → modal opens with current values pre-filled.
- Pick a new photo → preview updates instantly.
- Save with a future DOB → inline error appears under the field.
- Save with valid data → page reloads showing the new info.
- ID number, course, year level inputs are visible but disabled.

- [ ] **Step 6: Commit**

```bash
git add templates/student/profile.html
git commit -m "feat(profile): in-page edit profile modal with XHR submission"
```

---

## Phase 6 — Confetti on level-up

### Task 10: Add level-up celebration JS

**Files:**
- Modify: `templates/student/profile.html` (load CDN script in `extra_js`-style block; add JS)

- [ ] **Step 1: Add the confetti JS**

Append to the trailing `<script>` block (after all previous IIFEs):

```javascript
(function () {
  const wrap = document.querySelector('.profile-photo-wrap');
  if (!wrap) return;
  const userId = '{{ profile.user.id }}';
  const currentLevel = parseInt(wrap.dataset.currentLevel || '1', 10);
  const tier = wrap.dataset.tier || 'bronze';
  const isOwn = {{ is_own_profile|yesno:'true,false' }};
  if (!isOwn) return;

  const storageKey = `lastSeenLevel:${userId}`;
  let stored = null;
  try {
    stored = parseInt(window.localStorage.getItem(storageKey) || 'NaN', 10);
  } catch (_) { return; }

  if (Number.isNaN(stored)) {
    // First load on this device — record silently, don't celebrate.
    try { window.localStorage.setItem(storageKey, String(currentLevel)); } catch (_) {}
    return;
  }

  if (currentLevel <= stored) return;

  // Celebrate.
  const tierName = tier.charAt(0).toUpperCase() + tier.slice(1);
  const fireToast = () => {
    if (typeof Swal !== 'undefined') {
      Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'success',
        title: `Level up! You're now Lv ${currentLevel} · ${tierName}`,
        showConfirmButton: false,
        timer: 4000,
        timerProgressBar: true,
      });
    }
  };

  const fireConfetti = () => {
    if (typeof confetti === 'undefined') { fireToast(); return; }
    const end = Date.now() + 1200;
    (function frame() {
      confetti({ particleCount: 4, angle: 60, spread: 55, origin: { x: 0 } });
      confetti({ particleCount: 4, angle: 120, spread: 55, origin: { x: 1 } });
      if (Date.now() < end) requestAnimationFrame(frame);
    })();
    fireToast();
  };

  if (typeof confetti === 'undefined') {
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.2/dist/confetti.browser.min.js';
    s.onload = fireConfetti;
    s.onerror = fireToast;
    document.head.appendChild(s);
  } else {
    fireConfetti();
  }

  try { window.localStorage.setItem(storageKey, String(currentLevel)); } catch (_) {}
})();
```

- [ ] **Step 2: Manual smoke check**

To force a level-up locally:
1. Open DevTools console on the student profile page and run:
   `localStorage.setItem('lastSeenLevel:{your_user_id}', '1');`
2. Reload the page (assuming `current_level > 1`). Confetti + toast should fire.
3. Reload again — they should NOT fire (now stored value matches current).

- [ ] **Step 3: Commit**

```bash
git add templates/student/profile.html
git commit -m "feat(profile): confetti and toast on level-up"
```

---

## Phase 7 — Cleanup

### Task 11: Remove the now-unused standalone Edit Profile flow (optional)

**Files:**
- The standalone template `accounts/user_level/update_header_profile.html` is still referenced as the non-XHR fallback. Leave it in place so direct hits to `/update_header_profile/<user_id>/` still work (e.g., bookmarks).

- [ ] **Step 1: Confirm nothing else links to the standalone page**

```bash
grep -rn "update_header_profile" templates/ accounts/templates/ social_media/templates/ 2>/dev/null | grep -v ".worktrees"
```

Expected: only the modal form action and the view's own templates appear; the `<a href>` link in `student/profile.html` should be gone (replaced by the modal trigger in Task 9).

- [ ] **Step 2: If a stray link is found, replace it with the modal trigger**

(Code identical to Task 9 Step 2. Skip if grep is clean.)

- [ ] **Step 3: Final commit if anything was changed**

```bash
git add -A
git commit -m "chore(profile): drop residual links to standalone update page"
```

---

## Self-review

**Spec coverage:**
- §1 Edit Profile modal → Tasks 8–9 ✓
- §1 Editable vs read-only fields → Task 9 step 3 ✓
- §1 XHR success/error/redirect contract → Task 8 step 4 ✓
- §2 `is_featured` field + migration → Task 1 ✓
- §2 `set_featured_badges` endpoint with validation → Task 2 ✓
- §2 Featured / More UI partition → Task 6 ✓
- §2 Manage modal with X/5 counter → Task 7 ✓
- §3 Tier mapping (template tag) → Task 3 ✓
- §3 Tier ring + level pill + XP arc → Task 5 ✓
- §3 Confetti on level-up gated by localStorage → Task 10 ✓

**Placeholder scan:** No TBDs, no "implement appropriate validation", no "similar to Task N". Each task contains the full code or command needed.

**Type/name consistency:**
- `set_featured_badges` URL name used in both Task 2 (registration) and Task 7 (fetch) ✓
- `is_featured` field referenced in Task 1 (model), Task 2 (filter), Task 4 (partition), Task 6 (template) ✓
- `current_level`, `xp_into_level`, `xp_for_next_level`, `xp_progress_pct` context keys defined in Task 4, consumed in Task 5 ✓
- `level_tier` template filter registered in Task 3, used in Task 5 ✓
- `data-current-level` / `data-tier` attributes set in Task 5 markup, read in Task 10 JS ✓
