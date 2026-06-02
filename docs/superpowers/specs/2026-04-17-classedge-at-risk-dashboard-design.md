# Prime — At-risk Student Dashboard

## Overview

A teacher/admin-facing dashboard on the subject detail page that flags
students at risk of failing. Scores each enrolled student using existing
grade, activity completion, and attendance data. No ML — simple weighted
scoring that teachers can understand and trust.

## Scope

**In scope:**
- New Django app `at_risk/`
- Risk calculator: grade, completion, attendance scores → weighted risk score
- Risk levels: High (0-40), Medium (40-65), Low (65-100)
- Dashboard view: table of students sorted by risk score
- Integration as a section on the subject detail page (teacher/admin only)
- Configurable weights in settings

**Out of scope:**
- Automated actions (no auto-emails, no notifications to students)
- ML-based prediction models
- Historical trend tracking / snapshots (v2)
- Cross-subject risk aggregation (v2)

## Risk Calculation

### `at_risk/calculator.py`

Function: `calculate_risk_scores(subject, semester) -> list[dict]`

For each enrolled student in the subject for the given semester:

**Grade score (0-100):**
- Collect all graded activity scores for the student in this subject/semester.
- Calculate current average percentage.
- If average >= passing_grade (from Semester.passing_grade, default 75): score = 100.
- If average == 0: score = 0.
- Otherwise: score = (average / passing_grade) * 100, capped at 100.
- If no graded activities yet: score = 50 (neutral, no data).

**Completion score (0-100):**
- Count total activities in the subject for this semester's terms.
- Count activities the student has submitted (has StudentQuestion records).
- score = (submitted / total) * 100.
- If no activities exist: score = 50 (neutral).

**Attendance score (0-100):**
- Count total class sessions (from Teacher_Attendance records for the subject).
- Count sessions where the student was marked present.
- score = (present / total) * 100.
- If no attendance records: score = 50 (neutral).

**Risk score:**
- weighted = grade_score * 0.5 + completion_score * 0.3 + attendance_score * 0.2
- Weights from settings: `AT_RISK_WEIGHTS = {"grade": 0.5, "completion": 0.3, "attendance": 0.2}`

**Risk level:**
- 0-40: "high"
- 40-65: "medium"
- 65-100: "low"

Returns:
```python
[
    {
        "student_id": 42,
        "student_name": "Juan Dela Cruz",
        "risk_score": 35.5,
        "risk_level": "high",
        "grade_score": 20.0,
        "completion_score": 60.0,
        "attendance_score": 45.0,
    },
    ...
]
```

Sorted by risk_score ascending (most at-risk first).

## Dashboard View

### Endpoint

`GET /at-risk/dashboard/<int:subject_id>/`

Protected by `@login_required` + `check_subject_access(require_teacher=True)`.
Teachers and admins only — students cannot see this.

### Response

HTML page extending `base.html`. Shows:
- Subject name + semester
- Summary: X high risk, Y medium risk, Z total enrolled
- Table: student name, risk score (colored badge), grade %, completion %,
  attendance %, risk level
- Rows colored: red for high, yellow for medium, no color for low
- Sortable columns (client-side JS sorting via DataTables, already loaded
  in base.html)

### Integration with subject detail

Add an "At-risk Students" link/button on the subject detail page, visible
only to teachers and admins. Links to the dashboard page.

## Data Sources (existing models, no changes)

**Grades:**
- `activity.StudentQuestion` — `score` field, FK to `activity_question__activity`
- `activity.Activity` — `max_score`, `is_graded`, FK to `subject`, `term`

**Activity completion:**
- `activity.StudentQuestion` — existence of records = submission
- `activity.Activity` — total activities per subject/term

**Attendance:**
- `classroom.Teacher_Attendance` — has `student` FK, `subject` FK, `status`
  (Present/Absent/Late/Excused), `date`

**Enrollment:**
- `course.SubjectEnrollment` — `student`, `subject`, `semester`, `status`

## Configuration

Settings additions (in gitignored `lms/settings.py`):

```python
# At-risk Dashboard
AT_RISK_WEIGHTS = {
    "grade": 0.5,
    "completion": 0.3,
    "attendance": 0.2,
}
AT_RISK_HIGH_THRESHOLD = 40
AT_RISK_MEDIUM_THRESHOLD = 65
```

## Testing

### Calculator tests
- Student with low grades → high risk score.
- Student with perfect grades + full completion + full attendance → low risk.
- Student with no graded activities → neutral grade score (50).
- Student with no attendance records → neutral attendance score (50).
- Empty subject (no students) → empty list.
- Weights applied correctly.

### View tests
- Dashboard renders for teacher.
- Dashboard shows at-risk students.
- Student cannot access dashboard.
- Unauthenticated redirects.

## URL Configuration

`at_risk/urls.py`:
```
at-risk/dashboard/<int:subject_id>/ → dashboard view
```

Included in `lms/urls.py`.
