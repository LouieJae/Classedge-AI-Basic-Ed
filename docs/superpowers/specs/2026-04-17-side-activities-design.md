# Side Activities (Gamified Practice) — Design Spec

## Overview

Optional, ungraded mini-activities that students can play within each subject
to reinforce learning through repetition and play. Award XP and unlock badges
via the existing gamification engine. 15 activity types ranging from simple
multiple-choice to drag-and-drop matching and timed speed rounds.

## Scope

**In scope:**
- 2 new models in `gamification/`: `SideActivity`, `SideActivityAttempt`
- 15 activity types with type-specific `content_json` schemas
- Hybrid rendering: server-rendered forms for simple types, JS gameplay for interactive types
- Student views: list per subject, play, AJAX submit
- Teacher views: CRUD for creating/editing side activities
- Seed management command with sample content
- 10 new badge definitions + evaluator functions
- Integration widget on subject detail page
- ~15 tests

**Out of scope:**
- AI-generated content (future — depends on content pipeline)
- Leaderboard pressure for side activities (these are practice, not competition)
- Spaced repetition algorithm for flashcards (simple sequential for now)
- Sandboxed code execution for code_kata (string-match output comparison only)
- Monaco editor (plain textarea for code_kata)

## Data Models

### `SideActivity`

```python
class SideActivity(models.Model):
    SUB_TYPE_CHOICES = [
        ("daily_challenge", "Daily Challenge"),
        ("flashcard", "Flashcard Review"),
        ("speed_round", "Speed Round"),
        ("match_pair", "Match Pair"),
        ("fill_blank", "Fill in the Blank"),
        ("drag_order", "Drag to Order"),
        ("word_scramble", "Word Scramble"),
        ("equation_balance", "Equation Balancer"),
        ("math_drill", "Math Drill"),
        ("geo_map", "Geography Map"),
        ("timeline_sort", "Timeline Sort"),
        ("code_kata", "Code Kata"),
        ("typing_drill", "Typing Drill"),
        ("reading_mini", "Reading Comprehension Mini"),
        ("practice_quiz", "Practice Quiz"),
    ]
    subject = models.ForeignKey("subject.Subject", on_delete=models.CASCADE,
        related_name="side_activities")
    sub_type = models.CharField(max_length=30, choices=SUB_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    content_json = models.JSONField()
    estimated_minutes = models.PositiveSmallIntegerField(default=3)
    xp_reward = models.PositiveSmallIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["subject", "sub_type"]),
        ]
```

### `SideActivityAttempt`

```python
class SideActivityAttempt(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="side_activity_attempts")
    side_activity = models.ForeignKey(SideActivity, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True)  # 0.0 to 1.0
    time_taken_seconds = models.PositiveIntegerField(null=True)
    xp_awarded = models.PositiveSmallIntegerField(default=0)
    details_json = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["student", "completed_at"]),
            models.Index(fields=["side_activity"]),
        ]
```

## Content JSON Schemas

### Universal types

**daily_challenge** (form, +5 XP):
```json
{"question": "What is the capital of France?", "choices": ["London", "Paris", "Berlin", "Madrid"], "answer": 1}
```

**flashcard** (JS flip, +5 XP per session):
```json
{"cards": [{"front": "Mitosis", "back": "Cell division producing two identical daughter cells"}, ...]}
```

**speed_round** (JS timer 60s, +10 XP):
```json
{"questions": [{"q": "7 × 8", "choices": ["54", "56", "58", "64"], "answer": 1}, ...], "time_limit": 60}
```

**match_pair** (JS drag, +10 XP):
```json
{"pairs": [{"left": "H2O", "right": "Water"}, {"left": "NaCl", "right": "Salt"}, ...]}
```

**practice_quiz** (form, +5 per 5 correct):
```json
{"questions": [{"q": "...", "choices": ["A", "B", "C", "D"], "answer": 0}, ...]}
```

### Subject-specific types

**fill_blank** (form, +10 XP):
```json
{"text": "The ___ is the powerhouse of the cell.", "blanks": ["mitochondria"]}
```

**drag_order** (JS drag, +10 XP):
```json
{"items": ["Egg", "Larva", "Pupa", "Adult"], "correct_order": [0, 1, 2, 3]}
```

**word_scramble** (form, +5 XP):
```json
{"words": [{"scrambled": "TOHMPICANRDIE", "answer": "MITOCHONDRIA", "hint": "Powerhouse of the cell"}]}
```

**equation_balance** (form, +15 XP):
```json
{"equation": "_ H2 + _ O2 -> _ H2O", "coefficients": [2, 1, 2]}
```

**math_drill** (JS timer, +10 XP):
```json
{"problems": [{"expression": "12 × 7", "answer": 84}, ...], "time_limit": 120}
```

**geo_map** (JS click, +10 XP):
```json
{"image_url": "/static/images/maps/philippines.svg", "targets": [{"name": "Manila", "x": 52, "y": 38, "radius": 5}]}
```

**timeline_sort** (JS drag, +10 XP):
```json
{"events": [{"text": "Philippine Independence", "year": 1898}, {"text": "EDSA Revolution", "year": 1986}, ...]}
```

**code_kata** (JS textarea, +15 XP):
```json
{"prompt": "Write a function that returns the sum of two numbers.", "test_cases": [{"input": "add(2, 3)", "expected": "5"}], "language": "python"}
```

**typing_drill** (JS keypress, +5 XP):
```json
{"text": "def hello_world():\n    print('Hello, World!')"}
```

**reading_mini** (form, +10 XP):
```json
{"passage": "The water cycle describes how water evaporates...", "questions": [{"q": "What drives evaporation?", "choices": ["Wind", "Sun", "Moon", "Rain"], "answer": 1}]}
```

## Scoring

All types produce a `score` from 0.0 to 1.0:
- **Choice-based** (daily_challenge, practice_quiz, reading_mini, speed_round, math_drill): correct / total
- **Exact match** (fill_blank, word_scramble, equation_balance): all-or-nothing per item, averaged
- **Order/matching** (match_pair, drag_order, timeline_sort): correct pairs / total pairs
- **Flashcard**: self-rated "knew it" count / total cards
- **Code kata**: test cases passed / total test cases (string comparison of output)
- **Typing drill**: accuracy percentage (correct chars / total chars)
- **Geo map**: correct clicks / total targets

XP awarded = `xp_reward` if `score >= 0.5`, else `xp_reward // 2`. Full XP only on first completion; repeat attempts award no XP (tracked via `SideActivityAttempt`).

## Views

### Student views

**`side_activity_list(request, subject_id)`**
- URL: `/gamification/side-activities/<subject_id>/`
- Shows all active SideActivity for the subject
- Grouped by type, shows title, XP reward, estimated time
- Checkmark on completed activities (student has a completed attempt)
- Template: `gamification/templates/gamification/side_activity_list.html`

**`side_activity_play(request, activity_id)`**
- URL: `/gamification/side-activity/<activity_id>/play/`
- Renders the type-specific template
- For form-based types: handles POST, scores, creates attempt, awards XP
- For JS types: renders template with `content_json` as JS variable, provides CSRF token
- Template: `gamification/templates/gamification/side_activity_play.html`
  - Includes type-specific partial: `gamification/templates/gamification/types/_<sub_type>.html`

**`side_activity_submit(request, activity_id)`**
- URL: `/gamification/side-activity/<activity_id>/submit/`
- AJAX POST endpoint for JS-driven types
- Accepts JSON: `{score, time_taken_seconds, details}`
- Creates `SideActivityAttempt`, awards XP via `award_xp` if first completion
- Returns JSON: `{xp_awarded, score, badge_earned}`

### Teacher views

**`side_activity_create(request, subject_id)`**
- URL: `/gamification/side-activities/<subject_id>/create/`
- Teacher picks type, fills title + content JSON via structured form
- Protected: teacher/admin only (check_subject_access)

**`side_activity_edit(request, activity_id)`**
- URL: `/gamification/side-activity/<activity_id>/edit/`

**`side_activity_delete(request, activity_id)`**
- URL: `/gamification/side-activity/<activity_id>/delete/`
- POST only, redirects to list

## Templates

### Gameplay templates

Base wrapper: `side_activity_play.html` — shows title, XP reward, timer slot, includes type partial.

15 type partials in `gamification/templates/gamification/types/`:
```
_daily_challenge.html    — radio buttons, submit
_flashcard.html          — flip cards with JS
_speed_round.html        — timed MCQ with JS countdown
_match_pair.html         — drag left to right with JS
_practice_quiz.html      — sequential MCQ form
_fill_blank.html         — text inputs in passage
_drag_order.html         — sortable list with JS
_word_scramble.html      — text input per word
_equation_balance.html   — number inputs for coefficients
_math_drill.html         — timed math with JS
_geo_map.html            — clickable SVG/image with JS
_timeline_sort.html      — drag events to timeline with JS
_code_kata.html          — textarea + test results with JS
_typing_drill.html       — typing input with JS WPM tracker
_reading_mini.html       — passage + MCQ form
```

## JavaScript Modules

Shared JS in `static/js/side_activities/`:

**`timer.js`** — countdown timer for speed_round, math_drill. Exports `startTimer(seconds, onTick, onExpire)`.

**`drag.js`** — HTML5 drag-and-drop for match_pair, drag_order, timeline_sort. Touch-friendly via pointer events. Exports `initDragSort(container, onComplete)` and `initDragMatch(leftContainer, rightContainer, onComplete)`.

**`flashcard.js`** — card flip logic. Exports `initFlashcards(container, onComplete)`.

**`geo_map.js`** — click target on image. Exports `initGeoMap(container, targets, onComplete)`.

**`typing.js`** — keystroke tracking, WPM calculation. Exports `initTypingDrill(container, text, onComplete)`.

**`code_kata.js`** — textarea with submit. Output comparison done server-side. Exports `initCodeKata(container, onSubmit)`.

**`submit.js`** — shared AJAX submission helper. All JS types call this on completion:
```javascript
function submitAttempt(activityId, score, timeTaken, details) {
    return fetch(`/gamification/side-activity/${activityId}/submit/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json'},
        body: JSON.stringify({score, time_taken_seconds: timeTaken, details})
    }).then(r => r.json());
}
```

## Badges

10 new badge definitions added via data migration. New evaluator functions in `gamification/badges.py`:

| Code | Name | Tier | Criteria | Icon |
|------|------|------|----------|------|
| `play_hard` | Play Hard | bronze | Complete 10 side activities | 🎲 |
| `speed_demon` | Speed Demon | silver | 10 speed rounds under 45s | 🏃 |
| `sharp_shooter_sa` | Sharp Shooter | silver | 5 consecutive 100% daily challenges | 🎯 |
| `early_bird_quiz` | Early Bird Quiz | silver | 5 daily challenges before 8am | 🌅 |
| `lifelong_learner` | Lifelong Learner | gold | Complete a side activity every day for 30 days | 🧠 |
| `subject_champion` | Subject Champion | gold | Complete all side activities in one subject | 🏅 |
| `flashcard_master` | Flashcard Master | silver | Review 500 flashcards | 🃏 |
| `fast_fingers` | Fast Fingers | silver | Typing drill >= 80 WPM | ⌨️ |
| `mad_scientist` | Mad Scientist | silver | 50 equation balance completions | 🧪 |
| `explorer_geo` | Explorer | gold | 100% on all geo map activities | 🗺️ |

New evaluator types in the `EVALUATORS` registry:
- `side_activity_count` — total completed attempts
- `side_activity_count_type` — completed attempts for a specific sub_type
- `side_activity_speed` — completed under time threshold for a sub_type
- `side_activity_streak` — consecutive perfect scores on a sub_type
- `side_activity_early` — completed before a specific hour
- `side_activity_daily` — consecutive days with at least one completion
- `side_activity_all_in_subject` — all activities in any one subject completed
- `side_activity_typing_wpm` — WPM from details_json
- `side_activity_perfect_type` — all activities of a sub_type completed with score 1.0

## Seed Command

`manage.py seed_side_activities` — for each subject with enrolled students, creates 2-3 sample activities per type using generic template content. Idempotent (checks for existing by title + subject + sub_type).

## Subject Detail Integration

In `course/templates/course/view_subject_dashboard.html`, add a "Side Activities" section visible to students:

```html
{% if is_student %}
<div class="card mt-3">
    <div class="card-header">Play & Learn</div>
    <div class="card-body">
        <!-- Show 5 random active side activities for this subject -->
        <a href="{% url 'side_activity_list' subject.pk %}">See all activities →</a>
    </div>
</div>
{% endif %}
```

The side activity list view provides the full browsing experience.

## Testing

### Test files

- `gamification/tests/test_side_activities.py`

### Key test cases (~15):
- Create SideActivity with content_json
- Create SideActivityAttempt, verify score/xp fields
- Play view renders for each form-based type (daily_challenge, fill_blank, practice_quiz, reading_mini, word_scramble, equation_balance)
- Submit view scores correctly and awards XP
- Duplicate attempt does not award XP again
- Teacher can create/edit/delete activities
- Student cannot access teacher CRUD
- Seed command creates activities
- Badge evaluators: side_activity_count, side_activity_count_type
- List view shows completion status
