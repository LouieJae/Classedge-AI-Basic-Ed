# IDE for IT Students — Code Editor + Execution Engine (Sub-A)

## Overview

A browser-based code editor (Monaco) with sandboxed execution (Judge0) that
lets IT students write, run, and submit code directly in the LMS. Teachers
create "Coding" activities with test cases; the system auto-grades by running
student code and comparing output. Supports Python 3 and JavaScript (Node.js)
in Phase 1.

Sub-B (Activity integration + 9 coding badges) is a separate spec.

## Scope

**In scope:**
- New `ide/` Django app with 2 models
- Judge0 REST client for code execution
- Celery task for async test-case evaluation
- Monaco Editor loaded via CDN
- Student views: exercise detail, code submission, result polling
- Teacher views: exercise setup (test cases, starter code), edit
- "Coding" ActivityType seeded via data migration
- Integration link on activity detail page
- Gradebook integration via StudentActivity score update
- XP awards on successful submissions
- Docker Compose file for Judge0 deployment
- ~15 tests (Judge0 mocked)

**Out of scope:**
- HTML/CSS preview mode (Phase 2)
- C/C++, Java, SQL languages (Phase 2)
- 9 coding-specific badges (Sub-B)
- Real-time collaboration
- AI-assisted code completion
- Plagiarism detection

## Data Models

### `ide/models.py`

**CodingExercise** — extends an Activity with coding metadata.

```python
class CodingExercise(models.Model):
    LANGUAGE_CHOICES = [
        ("python", "Python 3"),
        ("javascript", "JavaScript (Node.js)"),
    ]
    activity = models.OneToOneField(
        "activity.Activity", on_delete=models.CASCADE,
        related_name="coding_exercise",
    )
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    starter_code = models.TextField(blank=True, default="")
    solution_code = models.TextField(blank=True, default="")
    test_cases = models.JSONField()
    # test_cases format: [{"input": "2 3", "expected_output": "5", "label": "Test 1"}, ...]
    time_limit_seconds = models.PositiveSmallIntegerField(default=5)
    memory_limit_kb = models.PositiveIntegerField(default=256000)
    created_at = models.DateTimeField(auto_now_add=True)
```

**CodeSubmission** — one per student attempt.

```python
class CodeSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("error", "Error"),
    ]
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="code_submissions",
    )
    exercise = models.ForeignKey(CodingExercise, on_delete=models.CASCADE)
    code = models.TextField()
    language = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    result_json = models.JSONField(default=dict)
    # result_json format: {"tests": [{"label": "Test 1", "passed": true, "stdout": "5", "expected": "5", "time": "0.01"}, ...]}
    score = models.FloatField(null=True)
    execution_time_ms = models.PositiveIntegerField(null=True)
    memory_used_kb = models.PositiveIntegerField(null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "exercise"]),
            models.Index(fields=["status"]),
        ]
```

## Judge0 Client

### `ide/judge0_client.py`

Thin wrapper around Judge0 REST API.

**Configuration** (in `lms/settings.py`):
```python
JUDGE0_API_URL = os.getenv("JUDGE0_API_URL", "http://localhost:2358")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY", "")
```

**Language ID mapping:**
```python
LANGUAGE_IDS = {
    "python": 71,       # Python 3.8
    "javascript": 63,   # Node.js 12
}
```

**Functions:**

`submit_code(source_code, language, stdin="", time_limit=5, memory_limit=256000) -> dict`
- POST to `{JUDGE0_API_URL}/submissions/?base64_encoded=false&wait=true`
- Headers: `X-Auth-Token: {JUDGE0_API_KEY}` if set
- Body: `{source_code, language_id, stdin, cpu_time_limit, memory_limit, wall_time_limit: time_limit * 2}`
- Uses `wait=true` — blocks until execution completes (safe inside Celery worker)
- Returns parsed JSON response: `{status: {id, description}, stdout, stderr, time, memory, compile_output}`
- Raises `Judge0Error` on HTTP errors or connection failures

**Status IDs:** 3 = Accepted (ran successfully), 4 = Wrong Answer, 5 = Time Limit Exceeded,
6 = Compilation Error, 7-12 = Runtime errors

## Celery Task

### `ide/tasks.py`

```python
@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def run_code_submission(self, submission_id):
```

**Flow:**
1. Load `CodeSubmission` and its `CodingExercise`
2. Set `status = "running"`
3. For each test case in `exercise.test_cases`:
   - Call `submit_code(submission.code, submission.language, test_case["input"], ...)`
   - Compare `result["stdout"].strip()` to `test_case["expected_output"].strip()`
   - Record pass/fail, stdout, time, memory per test case
4. Calculate `score = passed / total`
5. Update `CodeSubmission`: `status="completed"`, `result_json`, `score`, `execution_time_ms`, `memory_used_kb`
6. Update `StudentActivity.total_score = score * activity.max_score`
   - Find or create `StudentActivity` for this student + activity
7. Award XP: `award_xp(student, 30, ...)` if score >= 0.9, `award_xp(student, 10, ...)` if score >= 0.5
8. On exception: set `status = "error"`, retry if retriable

## Views

### Student views

**`exercise_detail(request, activity_id)`**
- URL: `/ide/exercise/<activity_id>/`
- GET: renders Monaco editor with starter code, language badge, test case labels (not expected outputs), time/memory limits, previous submissions list
- Login required
- Template: `ide/templates/ide/exercise_detail.html`

**`submit_code(request, activity_id)`**
- URL: `/ide/exercise/<activity_id>/submit/`
- AJAX POST: accepts `{code}` JSON body
- Creates `CodeSubmission(status="pending")`, dispatches `run_code_submission.delay(submission.id)`
- Returns `{submission_id}`
- Login required

**`submission_status(request, submission_id)`**
- URL: `/ide/submission/<submission_id>/status/`
- AJAX GET: returns `{status, score, score_pct, result_json, execution_time_ms, memory_used_kb}`
- Frontend polls every 2 seconds until `status == "completed"` or `"error"`
- Login required

### Teacher views

**`exercise_create(request, activity_id)`**
- URL: `/ide/exercise/<activity_id>/setup/`
- Attach CodingExercise to an existing Activity (type="Coding")
- Form: language (select), starter_code (Monaco textarea), solution_code (Monaco textarea), test_cases (JSON textarea), time_limit, memory_limit
- Protected: teacher only via `check_subject_access(require_teacher=True)`

**`exercise_edit(request, exercise_id)`**
- URL: `/ide/exercise/<exercise_id>/edit/`
- Same form, pre-populated
- Teacher only

## Templates

**`ide/templates/ide/exercise_detail.html`** — extends `student_base.html`:
- Split layout: left panel = problem description + test case labels, right panel = Monaco editor
- Monaco loaded via CDN, initialized with `exercise.language` and dark/light theme matching `data-theme`
- "Run Code" button triggers AJAX submit
- Results panel below editor: shows per-test pass/fail badges, execution time, memory, stderr
- Previous submissions list with scores and timestamps

**`ide/templates/ide/exercise_setup.html`** — extends `student_base.html` (teachers access the student theme too via the conditional extends):
- Form for language, starter code, solution code, test cases JSON, limits
- Test case helper: "Add Test Case" button that appends input/expected fields

**Monaco initialization JS** (inline in exercise_detail.html):
```javascript
require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }});
require(['vs/editor/editor.main'], function() {
    var editor = monaco.editor.create(document.getElementById('editor-container'), {
        value: starterCode,
        language: language,
        theme: document.body.dataset.theme === 'dark' ? 'vs-dark' : 'vs',
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 14,
    });
});
```

## Activity Type Integration

**Data migration** seeds `ActivityType(name="Coding")` if it doesn't exist.

**Activity detail template** (`activity/templates/activity/activities/activity_detail.html`):
Add conditional block:
```django
{% if activity.activity_type.name == "Coding" %}
    {% if activity.coding_exercise %}
        <a href="{% url 'exercise_detail' activity.pk %}">Open Code Editor</a>
    {% elif is_teacher %}
        <a href="{% url 'exercise_create' activity.pk %}">Setup Test Cases</a>
    {% endif %}
{% endif %}
```

## Docker Compose

**`docker-compose.judge0.yml`** at project root — documentation for deploying Judge0:
```yaml
services:
  judge0-server:
    image: judge0/judge0:1.13.0
    ports:
      - "2358:2358"
    depends_on:
      - judge0-redis
      - judge0-db
    environment:
      - REDIS_URL=redis://judge0-redis:6379
      - POSTGRES_HOST=judge0-db
      - POSTGRES_DB=judge0
      - POSTGRES_USER=judge0
      - POSTGRES_PASSWORD=judge0
  judge0-worker:
    image: judge0/judge0:1.13.0
    command: ["./scripts/workers"]
    depends_on:
      - judge0-server
    environment:
      - REDIS_URL=redis://judge0-redis:6379
      - POSTGRES_HOST=judge0-db
      - POSTGRES_DB=judge0
      - POSTGRES_USER=judge0
      - POSTGRES_PASSWORD=judge0
    privileged: true
  judge0-redis:
    image: redis:7-alpine
  judge0-db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=judge0
      - POSTGRES_USER=judge0
      - POSTGRES_PASSWORD=judge0
    volumes:
      - judge0-db-data:/var/lib/postgresql/data

volumes:
  judge0-db-data:
```

## Configuration

In `lms/settings.py`:
```python
# IDE / Judge0
JUDGE0_API_URL = os.getenv("JUDGE0_API_URL", "http://localhost:2358")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY", "")
```

## Testing

### Test files

- `ide/tests/test_models.py` — model creation, constraints
- `ide/tests/test_judge0_client.py` — mock HTTP, verify request format, parse responses
- `ide/tests/test_views.py` — exercise detail renders, submit creates submission, status endpoint, teacher CRUD access
- `ide/tests/test_tasks.py` — mock Judge0, verify scoring logic, StudentActivity update

### Key test cases (~15):
- Create CodingExercise with test cases JSON
- Create CodeSubmission, verify defaults
- OneToOne constraint on CodingExercise → Activity
- Judge0 client formats request correctly (mocked)
- Judge0 client handles error responses
- Celery task scores 2/3 test cases → score 0.667
- Celery task updates StudentActivity total_score
- Celery task awards XP on high score
- Exercise detail renders for student
- Submit endpoint creates submission and returns ID
- Status endpoint returns submission state
- Teacher can create exercise
- Student cannot access setup
- Exercise not accessible for non-Coding activity type
