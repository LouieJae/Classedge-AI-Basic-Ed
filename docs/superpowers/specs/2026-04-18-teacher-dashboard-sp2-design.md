# Teacher Dashboard — Sub-project 2: Teacher Gamification Engine

**Date:** 2026-04-18
**Status:** Approved
**Depends on:** Teacher Dashboard SP1 (shipped)

---

## Overview

Add a full teacher gamification layer: Impact Points (IP), tiered named ranks, teacher-specific badges, time-boxed and milestone challenges, teacher-to-student recognition shoutouts, and student-to-teacher star ratings. All integrated into the existing teacher dashboard from SP1.

## Design Decisions

- **IP economy:** Hybrid — ~60% outcome-driven (student results), ~40% activity-driven (teaching effort)
- **Ranks:** Named ranks tied to badge tiers (Bronze Mentor → Platinum Legend)
- **Badges:** Separate `TeacherBadgeDefinition` model (not reusing student `BadgeDefinition`)
- **Challenges:** Both rotating (weekly/monthly) and persistent milestones
- **Recognition:** Bidirectional — teacher→student shoutouts (text + XP), student→teacher star ratings only (1-5, anonymous aggregate, no comments)

---

## 1. Data Models

All new models live in `gamification/teacher_models.py`, imported at the bottom of `gamification/models.py`.

### 1a. TeacherGamification

Parallel to `StudentGamification`. One row per teacher.

| Field | Type | Purpose |
|-------|------|---------|
| `teacher` | OneToOneField → AUTH_USER_MODEL | The teacher |
| `total_ip` | PositiveIntegerField(default=0) | Total Impact Points |
| `current_rank` | CharField(max_length=30) | Full rank code, e.g. "bronze_mentor" |
| `rank_tier` | CharField(max_length=20) | bronze / silver / gold / platinum |
| `rank_title` | CharField(max_length=30) | Mentor / Guide / Catalyst / etc. |

**Indexes:** `["-total_ip"]`

### 1b. IPTransaction

Parallel to `XPTransaction`. Tracks every IP award with dedup.

| Field | Type | Purpose |
|-------|------|---------|
| `teacher` | ForeignKey → AUTH_USER_MODEL | |
| `amount` | IntegerField | IP earned |
| `reason` | CharField(max_length=100) | Human-readable reason |
| `source_type` | CharField(max_length=50) | e.g. "grading_ontime", "student_badge_earned" |
| `source_id` | PositiveIntegerField(null=True, blank=True) | Dedup key |
| `created_at` | DateTimeField(auto_now_add=True) | |

**Indexes:** `["teacher", "created_at"]`, `["source_type", "source_id"]`

### 1c. TeacherBadgeDefinition

Separate from student `BadgeDefinition`. Same structure, teacher-specific evaluators.

| Field | Type | Purpose |
|-------|------|---------|
| `code` | CharField(max_length=50, unique=True) | Badge identifier |
| `name` | CharField(max_length=100) | Display name |
| `description` | TextField | |
| `tier` | CharField(max_length=20) | bronze / silver / gold / platinum |
| `icon` | CharField(max_length=50) | Emoji or icon code |
| `criteria_json` | JSONField(default=dict) | Evaluator config |
| `is_active` | BooleanField(default=True) | |

### 1d. TeacherBadge

Earned record for teacher badges.

| Field | Type | Purpose |
|-------|------|---------|
| `teacher` | ForeignKey → AUTH_USER_MODEL | |
| `badge` | ForeignKey → TeacherBadgeDefinition | |
| `earned_at` | DateTimeField(auto_now_add=True) | |
| `progress_percent` | PositiveSmallIntegerField(default=100) | |

**Constraints:** `unique_together = [("teacher", "badge")]`

### 1e. TeacherChallenge

Challenge definitions — both rotating and milestone types.

| Field | Type | Purpose |
|-------|------|---------|
| `code` | CharField(max_length=50, unique=True) | |
| `name` | CharField(max_length=100) | |
| `description` | TextField | |
| `challenge_type` | CharField(max_length=20) | "rotating" or "milestone" |
| `criteria_json` | JSONField(default=dict) | e.g. `{"type": "at_risk_recovery", "count": 3}` |
| `ip_reward` | PositiveIntegerField | Points on completion |
| `duration_days` | PositiveSmallIntegerField(null=True, blank=True) | For rotating: 7 or 30. Null for milestones |
| `is_active` | BooleanField(default=True) | |

### 1f. TeacherChallengeProgress

Per-teacher tracking of challenge instances.

| Field | Type | Purpose |
|-------|------|---------|
| `teacher` | ForeignKey → AUTH_USER_MODEL | |
| `challenge` | ForeignKey → TeacherChallenge | |
| `started_at` | DateTimeField(auto_now_add=True) | |
| `expires_at` | DateTimeField(null=True, blank=True) | For rotating challenges |
| `current_value` | PositiveIntegerField(default=0) | Current progress |
| `target_value` | PositiveIntegerField | Goal to hit |
| `completed_at` | DateTimeField(null=True, blank=True) | Null until done |

**Constraints:** `unique_together = [("teacher", "challenge", "started_at")]` — allows re-issuing rotating challenges.

### 1g. TeacherRecognition

Teacher → student shoutouts.

| Field | Type | Purpose |
|-------|------|---------|
| `teacher` | ForeignKey → AUTH_USER_MODEL (related_name="recognitions_given") | Who gave it |
| `student` | ForeignKey → AUTH_USER_MODEL (related_name="recognitions_received") | Who received it |
| `message` | CharField(max_length=300) | Short recognition text |
| `xp_awarded` | PositiveIntegerField(default=0) | XP given to student |
| `created_at` | DateTimeField(auto_now_add=True) | |

### 1h. TeacherRating

Student → teacher star ratings. Anonymous aggregate only — teachers never see individual ratings.

| Field | Type | Purpose |
|-------|------|---------|
| `teacher` | ForeignKey → AUTH_USER_MODEL (related_name="ratings_received") | Rated teacher |
| `student` | ForeignKey → AUTH_USER_MODEL (related_name="ratings_given") | Rating student |
| `stars` | PositiveSmallIntegerField | 1-5 |
| `semester` | ForeignKey → Semester | One rating per semester |
| `created_at` | DateTimeField(auto_now_add=True) | |

**Constraints:** `unique_together = [("teacher", "student", "semester")]`

---

## 2. Rank System

### Rank Tiers

| Rank | Tier | IP Threshold |
|------|------|-------------:|
| Bronze Mentor | bronze | 0 |
| Bronze Guide | bronze | 100 |
| Silver Catalyst | silver | 300 |
| Silver Architect | silver | 600 |
| Gold Luminary | gold | 1,200 |
| Gold Visionary | gold | 2,000 |
| Platinum Legend | platinum | 3,500 |

### Rank Calculation

Defined as a constant list in `teacher_services.py`:

```python
RANK_THRESHOLDS = [
    (3500, "platinum", "Legend", "platinum_legend"),
    (2000, "gold", "Visionary", "gold_visionary"),
    (1200, "gold", "Luminary", "gold_luminary"),
    (600, "silver", "Architect", "silver_architect"),
    (300, "silver", "Catalyst", "silver_catalyst"),
    (100, "bronze", "Guide", "bronze_guide"),
    (0, "bronze", "Mentor", "bronze_mentor"),
]
```

`recalculate_rank(teacher_gam)` iterates top-down, first match wins.

---

## 3. IP Economy

### Effort-based (activity-driven)

| Action | IP | Source Type | Dedup |
|--------|---:|------------|-------|
| Grade an activity on time (before deadline) | 2 | `grading_ontime` | activity_id |
| Grade an activity late | 1 | `grading_late` | activity_id |
| Create a new graded activity | 3 | `activity_created` | activity_id |
| Award a badge manually to a student | 2 | `manual_badge_award` | studentbadge_id |
| Send a recognition shoutout | 1 | `recognition_sent` | recognition_id |

### Outcome-based (student results)

| Action | IP | Source Type | Dedup |
|--------|---:|------------|-------|
| Student in your class earns a badge | 3 | `student_badge_earned` | studentbadge_id |
| At-risk student recovers (down a risk level) | 5 | `at_risk_recovery` | student_id + semester_id |
| Class average rises above 85% (per subject/term) | 10 | `class_avg_milestone` | subject_id + term_id |
| 100% completion rate on an activity | 4 | `full_completion` | activity_id |

### Rating-based

| Action | IP | Source Type |
|--------|---:|------------|
| Receive a 5-star rating | 3 | `star_rating_5` |
| Receive a 4-star rating | 1 | `star_rating_4` |

### Challenge rewards

Defined per challenge definition (typically 6-25 IP for rotating, 15-50 IP for milestones).

---

## 4. Teacher Badges (Initial Set — 8 badges)

| Badge | Tier | Evaluator Type | Criteria |
|-------|------|---------------|----------|
| First Impact | bronze | `teacher_ip_total` | `{"threshold": 10}` |
| Grading Machine | bronze | `teacher_grading_count` | `{"threshold": 50}` |
| Mentor's Touch | silver | `teacher_recognition_count` | `{"threshold": 20}` |
| Risk Responder | silver | `teacher_at_risk_recovery` | `{"threshold": 5}` |
| Class Champion | gold | `teacher_class_avg` | `{"threshold": 85, "count": 3}` |
| Badge Bestower | gold | `teacher_manual_awards` | `{"threshold": 25}` |
| Student Favorite | gold | `teacher_star_avg` | `{"min_avg": 4.5, "min_ratings": 10}` |
| Legendary Educator | platinum | `teacher_rank` | `{"rank": "platinum_legend"}` |

Each evaluator is a function in `teacher_badges.py` following the pattern `_eval_<type>(teacher, teacher_gam, criteria) -> bool`. Progress computers follow `_progress_<type>` pattern returning 0-100.

---

## 5. Challenges (Initial Set — 10 challenges)

### Rotating (weekly/monthly, auto-assigned)

| Challenge | Duration | Target | IP Reward | Criteria Type |
|-----------|----------|--------|----------:|--------------|
| Quick Grader | 7 days | Grade all pending activities | 10 | `grade_all_pending` |
| Streak Builder | 7 days | Get 5 students to start a login streak | 8 | `student_streaks_started` (count: 5) |
| Recognition Week | 7 days | Send 5 recognition shoutouts | 6 | `recognitions_sent` (count: 5) |
| Full House | 30 days | Reach 90%+ completion rate across all subjects | 20 | `completion_rate` (threshold: 90) |
| Risk Rescue | 30 days | Move 3 at-risk students down a risk level | 25 | `at_risk_recoveries` (count: 3) |

### Milestone (always available, one-time)

| Challenge | Target | IP Reward | Criteria Type |
|-----------|--------|----------:|--------------|
| First Steps | Earn 50 IP | 15 | `ip_milestone` (threshold: 50) |
| Badge Collector | Earn 5 teacher badges | 20 | `teacher_badges_earned` (count: 5) |
| Perfect Term | 100% activity completion rate for a full term | 30 | `perfect_term_completion` |
| Honor Roll | All subjects above 80% class avg simultaneously | 40 | `all_subjects_above` (threshold: 80) |
| Century Club | Send 100 recognitions | 50 | `recognitions_sent` (count: 100) |

### Challenge Lifecycle

- **Rotating:** Management command `assign_weekly_challenges` (run Monday) picks 2 random weekly challenges per teacher. `assign_monthly_challenges` (run 1st of month) picks 1 monthly. Both skip teachers with active unexpired instances of the same challenge.
- **Milestones:** Auto-assigned on first dashboard load via `get_or_create` for each milestone challenge.
- **Completion:** Checked inside `award_ip()` — after updating IP, call `evaluate_teacher_challenges(teacher)`. If target met, mark `completed_at`, award bonus IP.

---

## 6. Recognition & Ratings

### Teacher → Student Recognition

**Endpoint:** `POST /gamification/recognition/send/` (AJAX, `@teacher_or_admin_required`)

**Request:** `{"student_id": int, "message": str, "xp_amount": int}` — xp_amount must be 10, 25, or 50.

**On submit:**
1. Create `TeacherRecognition` record
2. Call `award_xp(student, xp_amount, "Teacher recognition", "recognition", recognition.id)`
3. Call `award_ip(teacher, 1, "Sent recognition", "recognition_sent", recognition.id)`
4. Return JSON `{"ok": true}`

**UI:** Inline modal triggered from Student Spotlight items. Fields: student name (readonly), message textarea (300 char limit), XP dropdown (10/25/50).

**Student-side display:** "Recent Recognition" section on student dashboard — small card showing teacher first name + message. Last 3 recognitions shown.

### Student → Teacher Star Rating

**Endpoint:** `POST /gamification/rating/submit/` (AJAX, `@login_required`)

**Request:** `{"teacher_id": int, "stars": int}` — stars must be 1-5.

**On submit:**
1. `TeacherRating.objects.update_or_create(teacher_id=teacher_id, student=request.user, semester=current_semester, defaults={"stars": stars})`
2. Award IP to teacher (3 IP for 5 stars, 1 IP for 4 stars, 0 for 1-3)
3. Return JSON `{"ok": true}`

**Student-side UI:** "Rate Your Teachers" card on student dashboard. Shows each current teacher with a 5-star clickable selector. Auto-saves on click. Shows once per semester per teacher; if already rated, shows current selection (editable).

**Teacher-side display:** Aggregate only — `★ 4.3 (24 ratings)` in the growth section. Teachers never see individual ratings or student identities.

---

## 7. Dashboard Integration

### Growth Section Update

Add to the right side of the existing growth card:
- **Rank badge:** Tier-colored border (bronze=#cd7f32, silver=#c0c0c0, gold=#b7925a, platinum=#e5e4e2) + rank title
- **IP counter:** "{total_ip} Impact Points" with progress bar to next rank threshold
- **Star rating:** `★ {avg} ({count} ratings)` — from `TeacherRating` aggregate

### New Section: Active Challenges (after metrics, before My Classes)

Row of challenge cards:
- Challenge name, progress bar (current_value / target_value), days remaining (rotating) or "Ongoing" (milestone), IP reward
- Completed: checkmark + "Claimed" state
- Max 3 visible + "View all" link

### New Section: My Badges (after Active Challenges)

Compact horizontal badge shelf:
- Badge icons with tooltips (name + earned date)
- "{earned} / {total}" label
- "View all" link to full badge collection page

### Spotlight Section Update

- "Send recognition" becomes per-student inline modal trigger
- After sending, item shows "Recognized" state

### Sidebar Update

Add "My Progress" to Insight section (links to `#` for now — dedicated page is future work).

### New Template Fragments

| Template | Purpose |
|----------|---------|
| `gamification/teacher_challenges.html` | Challenges section (`{% include %}` in dashboard) |
| `gamification/teacher_badges_shelf.html` | Badge shelf section (`{% include %}` in dashboard) |
| `gamification/teacher_recognition_modal.html` | Recognition modal (`{% include %}` in dashboard) |

---

## 8. Services & Business Logic

### `gamification/teacher_services.py`

```python
def award_ip(teacher, amount, reason, source_type, source_id=None):
    """Award IP to a teacher. Returns IPTransaction or None if duplicate."""
    # Dedup check on source_type + source_id
    # Create IPTransaction
    # Update TeacherGamification.total_ip (F-expression)
    # Recalculate rank
    # Evaluate teacher badges
    # Evaluate active challenges

def recalculate_rank(teacher_gam):
    """Map total_ip to rank tier + title using RANK_THRESHOLDS."""

def evaluate_teacher_challenges(teacher):
    """Check all active (non-expired, non-completed) challenges. Mark complete + award bonus IP."""
```

### `gamification/teacher_badges.py`

8 evaluator functions + 8 progress computers, following existing patterns from `badges.py`:
- `TEACHER_EVALUATORS` dict mapping criteria type → evaluator function
- `TEACHER_PROGRESS_COMPUTERS` dict mapping criteria type → progress function
- `evaluate_teacher_badges(teacher)` — main entry point
- `compute_teacher_badge_progress(teacher, badge)` — returns 0-100

---

## 9. Signals

Extend `gamification/signals.py` with IP-awarding handlers:

| Signal | Model | Trigger | IP Action |
|--------|-------|---------|-----------|
| `post_save` | `StudentActivity` | Student submits graded work | Find teacher(s) for subject, check if graded on time → award 1-2 IP |
| `post_save` | `StudentBadge` | Student earns a badge | Find teacher(s) for student's subjects → award 3 IP each |
| `post_save` | `TeacherRecognition` | Teacher sends recognition | Award 1 IP (handled in view, not signal) |
| `post_save` | `TeacherRating` | Student rates teacher | Award 1-3 IP based on stars |

At-risk recovery and class average milestones are checked via `evaluate_teacher_challenges`, not signals — they require aggregation across multiple records.

---

## 10. Management Commands

| Command | Purpose | Schedule |
|---------|---------|----------|
| `assign_weekly_challenges` | Pick 2 random weekly challenges per teacher | Monday (cron/Celery beat) |
| `assign_monthly_challenges` | Pick 1 random monthly challenge per teacher | 1st of month |
| `seed_teacher_badges` | Create 8 badge definitions (idempotent via `get_or_create` on `code`) | One-time |
| `seed_teacher_challenges` | Create 10 challenge definitions (idempotent via `get_or_create` on `code`) | One-time |

---

## 11. Tests — `gamification/tests/test_teacher_gamification.py`

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | `test_award_ip_creates_transaction` | `award_ip()` creates IPTransaction + updates total_ip |
| 2 | `test_award_ip_dedup` | Duplicate source_type+source_id is skipped |
| 3 | `test_rank_progression` | IP thresholds map to correct rank tier + title |
| 4 | `test_teacher_badge_evaluation` | Badge awarded when criteria met |
| 5 | `test_teacher_badge_not_awarded_twice` | unique_together enforced |
| 6 | `test_teacher_badge_progress` | Progress computer returns 0-100 |
| 7 | `test_challenge_completion` | Challenge marked complete + bonus IP when target hit |
| 8 | `test_challenge_expiry` | Expired rotating challenge not completable |
| 9 | `test_recognition_creates_and_awards` | Recognition creates record + awards XP to student + IP to teacher |
| 10 | `test_rating_creates_and_awards_ip` | Rating saved + IP awarded based on stars |
| 11 | `test_rating_unique_per_semester` | Can't rate same teacher twice in same semester |
| 12 | `test_rating_aggregate` | Avg stars computed correctly |
| 13 | `test_dashboard_shows_rank` | Dashboard context includes rank info |
| 14 | `test_dashboard_shows_challenges` | Dashboard context includes active challenges |
| 15 | `test_dashboard_shows_badges` | Dashboard context includes earned badges |
| 16 | `test_signal_student_badge_awards_ip` | StudentBadge save triggers teacher IP |
| 17 | `test_seed_teacher_badges_command` | Management command creates 8 badges |
| 18 | `test_seed_teacher_challenges_command` | Management command creates 10 challenges |

**Total: 18 tests**

---

## 12. File Changes Summary

### New Files

| File | Purpose |
|------|---------|
| `gamification/teacher_models.py` | 8 new models |
| `gamification/teacher_services.py` | award_ip, recalculate_rank, evaluate_challenges |
| `gamification/teacher_badges.py` | 8 evaluators + 8 progress computers |
| `gamification/tests/test_teacher_gamification.py` | 18 tests |
| `gamification/management/commands/assign_weekly_challenges.py` | Weekly challenge assignment |
| `gamification/management/commands/assign_monthly_challenges.py` | Monthly challenge assignment |
| `gamification/management/commands/seed_teacher_badges.py` | Badge seeder |
| `gamification/management/commands/seed_teacher_challenges.py` | Challenge seeder |
| `gamification/templates/gamification/teacher_challenges.html` | Challenges include fragment |
| `gamification/templates/gamification/teacher_badges_shelf.html` | Badge shelf include fragment |
| `gamification/templates/gamification/teacher_recognition_modal.html` | Recognition modal |

### Modified Files

| File | Changes |
|------|---------|
| `gamification/models.py` | Import from `teacher_models.py` |
| `gamification/signals.py` | Add IP-awarding signal handlers |
| `gamification/urls.py` | Add recognition + rating endpoints |
| `gamification/teacher_dashboard.py` | Add rank, challenges, badges, rating to context |
| `gamification/templates/gamification/teacher_dashboard.html` | Add new sections (challenges, badges, recognition modal) |
| `templates/teacher_base.html` | Add "My Progress" sidebar link |
| `templates/gamification/student_dashboard.html` | Add recognition display + rating card |
