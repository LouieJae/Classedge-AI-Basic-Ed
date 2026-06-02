# Addendum — Assessment & Activity Models Coverage

**Date:** 2026-05-20
**Parent doc:** [2026-05-19-old-lms-migration-plan.md](./2026-05-19-old-lms-migration-plan.md)
**Status:** Draft — for review before Phase C begins

---

## 1. Purpose

The parent plan treats "Assessment / Question / Activity data" as a single Phase 7 bucket. In practice this bucket spans **four Django apps** and ~25 models with non-trivial FK relationships, file uploads, and score-integrity constraints. This addendum enumerates every model that must be migrated, the order it must run in, and the per-model concerns the mapper needs to handle.

---

## 2. Models in scope

Grouped by app, with FK dependencies in parentheses.

### 2.1 `course` (structural — must migrate first)

| Model | Depends on | Notes |
|------|------------|------|
| `Semester` | — | Standalone |
| `Term` | Semester | |
| `SubjectEnrollment` | CustomUser, Subject, Term | Links students to subjects per term |
| `Attendance` | SubjectEnrollment | |
| `AttendanceStatus` | Attendance | |
| `TeacherAttendancePoints` | CustomUser | |
| `StudentInvite` | CustomUser, Subject | |
| `StudentParticipationScore` | SubjectEnrollment | Score data — verify against new schema |
| `Retake` | Activity (forward ref) | See ordering note in §3 |

### 2.2 `activity` (core assessment data)

| Model | Depends on | Notes |
|------|------------|------|
| `ActivityType` | — | Lookup table |
| `QuizType` | — | Lookup table |
| `Activity` | CustomUser, Subject, ActivityType, QuizType | Has `activity_file_instruction` FileField |
| `ActivityQuestion` | Activity | Has `question_instruction` FileField |
| `QuestionChoice` | ActivityQuestion | Has `choice_image` ImageField |
| `StudentActivity` | Activity, CustomUser | Has `file` FileField (submitted work). **Holds total_score** — see §5 |
| `StudentQuestion` | StudentActivity, ActivityQuestion, QuestionChoice | Per-question student answers + score |
| `Rubrics` | Activity | |
| `RubricsItem` | Rubrics | |
| `RetakeRecord` | StudentActivity | |
| `RetakeRecordDetail` | RetakeRecord, ActivityQuestion | Has `uploaded_file` FileField |
| `ScoreChangeLog` | StudentActivity, CustomUser | **Audit trail — must preserve `created_at` exactly** |
| `ActivityIdRedirect` | Activity | Old→new id redirect map; may be redundant with IDMap |

### 2.3 `module` (lesson content referenced by activities)

| Model | Depends on | Notes |
|------|------------|------|
| `Module` | Subject, CustomUser | Has `file` FileField |
| `StudentProgress` | Module, CustomUser | Tracks completion |

### 2.4 `gradebookcomponent` (grading configuration)

| Model | Depends on | Notes |
|------|------------|------|
| `GradeBookComponents` | Subject | |
| `TermGradeBookComponents` | GradeBookComponents, Term | |
| `ActivityTypePercentage` | GradeBookComponents, ActivityType | Component weights |
| `TransmutationRule` | — | Grade conversion table |
| `GradeVisibilitySettings` | Subject / Term | |

---

## 3. Migration order (refines §5 of parent plan)

Phase 7 of the parent plan expands into:

```
7a. course.Semester → course.Term
7b. gradebookcomponent.* (config — needed before scores)
    GradeBookComponents → TermGradeBookComponents → ActivityTypePercentage
    TransmutationRule, GradeVisibilitySettings
7c. course.SubjectEnrollment (links users to subjects/terms)
7d. module.Module → module.StudentProgress
7e. activity lookups: ActivityType, QuizType
7f. activity.Activity → ActivityQuestion → QuestionChoice
7g. activity.Rubrics → RubricsItem
7h. activity.StudentActivity → StudentQuestion
7i. activity.RetakeRecord → RetakeRecordDetail (and course.Retake)
7j. activity.ScoreChangeLog
7k. course.Attendance → AttendanceStatus, TeacherAttendancePoints
7l. course.StudentInvite, StudentParticipationScore
7m. activity.ActivityIdRedirect (if still meaningful post-IDMap)
```

Rule of thumb: **structural → config → content → student responses → audit/derivatives**.

---

## 4. File / image fields requiring the media pipeline

These models will be incomplete until the media-files sub-plan (parent §6 open decision #5) is resolved:

| Field | Model |
|------|------|
| `Activity.activity_file_instruction` | activity |
| `ActivityQuestion.question_instruction` | activity |
| `QuestionChoice.choice_image` | activity |
| `StudentActivity.file` | activity |
| `RetakeRecordDetail.uploaded_file` | activity |
| `Module.file` | module |

Mapper recommendation: store the **old URL** in a temporary `legacy_file_url` column (or a side table) during JSON migration, then have the media pipeline backfill the real FileField afterward. Do not block Phase 7 on media.

---

## 5. Integrity constraints to enforce in mappers / verification

These are easy to get wrong and hard to detect after the fact.

1. **`StudentActivity.total_score` must equal sum of related `StudentQuestion` scores** (per existing CI grep guard `6bb4640f`). Verification step must assert this for a sample of rows.
2. **`ScoreChangeLog` rows are append-only and timestamped** — preserve `created_at` from old side; do not let `auto_now_add` overwrite.
3. **`StudentQuestion` writes are guarded in CI** (grep guard exists). Migration code is the legitimate writer — document the exemption explicitly or route through a dedicated `migration.writers` module that's whitelisted.
4. **`QuestionChoice.is_correct` must round-trip exactly** — a flipped boolean silently destroys scoring. Add a per-question checksum to the verification phase.
5. **Retake chains:** `RetakeRecord` → `RetakeRecordDetail` must remain consistent with the parent `StudentActivity`. If the old side has orphans, log and skip rather than crash.
6. **Rubric scoring:** `Rubrics`/`RubricsItem` must migrate before any `StudentActivity` that references rubric-based grading, else scores cannot be recomputed.

---

## 6. Endpoints to expose on the old LMS

One read-only DRF endpoint per model listed in §2 — naming follows parent plan convention:

```
/api/migration/course/semester/
/api/migration/course/term/
/api/migration/course/subject-enrollment/
/api/migration/course/attendance/
/api/migration/course/attendance-status/
/api/migration/course/teacher-attendance-points/
/api/migration/course/student-invite/
/api/migration/course/student-participation-score/
/api/migration/course/retake/
/api/migration/activity/activity-type/
/api/migration/activity/quiz-type/
/api/migration/activity/activity/
/api/migration/activity/activity-question/
/api/migration/activity/question-choice/
/api/migration/activity/student-activity/
/api/migration/activity/student-question/
/api/migration/activity/rubrics/
/api/migration/activity/rubrics-item/
/api/migration/activity/retake-record/
/api/migration/activity/retake-record-detail/
/api/migration/activity/score-change-log/
/api/migration/activity/activity-id-redirect/
/api/migration/module/module/
/api/migration/module/student-progress/
/api/migration/gradebookcomponent/grade-book-components/
/api/migration/gradebookcomponent/term-grade-book-components/
/api/migration/gradebookcomponent/activity-type-percentage/
/api/migration/gradebookcomponent/transmutation-rule/
/api/migration/gradebookcomponent/grade-visibility-settings/
```

**Throttling:** the high-volume tables — `StudentQuestion`, `ScoreChangeLog`, `StudentActivity` — need their own throttle scope (slower than the default 30/min).

---

## 7. Verification (in addition to parent §8)

Per-model assertions during the verification phase:

- Row count parity per model: `old_count == new_count + skipped_count`
- For every migrated `StudentActivity`: recomputed `sum(StudentQuestion.score) == total_score`
- For every migrated `QuestionChoice`: `is_correct` matches old payload exactly
- For a sampled 1% of `StudentQuestion`: full field-by-field equality
- `ScoreChangeLog`: `min(created_at)` and `max(created_at)` match old side (catches truncated history)
- IDMap completeness: no `StudentQuestion.student_activity_id` resolves to NULL via IDMap lookup

---

## 8. Open questions for this addendum

1. Is **`ActivityIdRedirect`** still needed once `IDMap` exists? If not, drop it from scope.
2. **Score recomputation vs. score copy:** do we trust old `total_score` values, or recompute on the new side after `StudentQuestion` import? (Recommend: copy + verify, don't recompute.)
3. **Retake data** — do retake attempts get separate `StudentActivity` rows on the new side, or are they nested under the original? Confirm before writing the retake mappers.
4. **Rubric grading history** — if rubric items changed on the old side after a score was given, do we migrate the rubric as-of-grading or as-of-now?
5. **Module file content vs. metadata** — does the new LMS expect module files in the same bucket layout, or does the media pipeline need to re-key them?

---

## 9. Next steps

1. Confirm model list against the old LMS variant chosen in parent §6 item 3 (model set may differ across `classedge-newhope` / `classedge` / `sncfilms`).
2. Resolve the 5 open questions in §8.
3. Fold this ordering into the Phase C rollout schedule.
4. Design the media pipeline (parent §6 item 5) in parallel — Phase 7 mappers should write `legacy_file_url` placeholders so the media pipeline can backfill without re-migrating rows.
