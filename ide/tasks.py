import logging

from celery import shared_task

from activity.models.student_activity_model import StudentActivity
from gamification.services import award_xp
from gamification.coding_stats_service import update_coding_stats
from ide.judge0_client import submit_code, Judge0Error
from ide.models import CodeSubmission

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def run_code_submission(self, submission_id):
    submission = CodeSubmission.objects.select_related(
        "exercise", "exercise__activity", "student",
    ).get(pk=submission_id)

    submission.status = "running"
    submission.save(update_fields=["status"])

    exercise = submission.exercise
    test_cases = exercise.test_cases
    time_limit = exercise.time_limit_seconds
    memory_limit = exercise.memory_limit_kb

    results = []
    passed = 0
    max_time = 0.0
    max_memory = 0

    for i, tc in enumerate(test_cases):
        try:
            result = submit_code(
                submission.code,
                submission.language,
                tc.get("input", ""),
                time_limit,
                memory_limit,
            )
        except Judge0Error as exc:
            results.append({
                "test": i + 1,
                "passed": False,
                "stdout": "",
                "expected": tc["expected_output"],
                "time": None,
                "status_description": f"Judge0 error: {exc}",
                "stderr": "",
                "compile_output": "",
            })
            continue

        stdout = (result.get("stdout") or "").strip()
        expected = tc["expected_output"].strip()
        test_passed = stdout == expected

        status_desc = ""
        status_obj = result.get("status")
        if isinstance(status_obj, dict):
            status_desc = status_obj.get("description", "")

        time_val = result.get("time")
        memory_val = result.get("memory")

        if time_val is not None:
            try:
                max_time = max(max_time, float(time_val))
            except (ValueError, TypeError):
                pass

        if memory_val is not None:
            try:
                max_memory = max(max_memory, int(memory_val))
            except (ValueError, TypeError):
                pass

        if test_passed:
            passed += 1

        results.append({
            "test": i + 1,
            "passed": test_passed,
            "stdout": stdout,
            "expected": expected,
            "time": time_val,
            "status_description": status_desc,
            "stderr": result.get("stderr") or "",
            "compile_output": result.get("compile_output") or "",
        })

    total = len(test_cases)
    score = passed / total if total > 0 else 0.0

    submission.status = "completed"
    submission.score = score
    submission.result_json = {"tests": results}
    submission.execution_time_ms = int(max_time * 1000) if max_time else None
    submission.memory_used_kb = max_memory if max_memory else None
    submission.save(update_fields=[
        "status", "score", "result_json", "execution_time_ms", "memory_used_kb",
    ])

    # Create or update StudentActivity — only update if new score is higher
    activity = exercise.activity
    total_score = score * (activity.max_score or 100)
    sa, created = StudentActivity.objects.get_or_create(
        student=submission.student,
        activity=activity,
        defaults={
            "total_score": total_score,
            "term": activity.term,
            "subject": activity.subject,
        },
    )
    if not created and total_score > sa.total_score:
        sa.total_score = total_score
        sa.save(update_fields=["total_score"])

    # Update coding stats
    update_coding_stats(submission.student, submission)

    # Award XP based on score
    if score >= 0.9:
        award_xp(submission.student, 30, "Coding exercise score >= 90%", "coding", source_id=submission.pk)
    elif score >= 0.5:
        award_xp(submission.student, 10, "Coding exercise score >= 50%", "coding", source_id=submission.pk)

    return {"submission_id": submission.pk, "score": score, "passed": passed, "total": total}
