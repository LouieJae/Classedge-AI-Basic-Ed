"""Wrapper task that drains an entire migration job in one shot.

Used by the RMS-style "Import" button so a single click migrates an entire
model (all pages, all batches) without depending on Celery beat.
"""
import time

from celery import shared_task

from migration.models import MigrationJob
from .batch import migrate_model_batch


MAX_BATCHES = 500  # safety cap — 500 * default 500 rows = 250k rows max per click


@shared_task(name="migration.tasks.run_job_to_completion", bind=True)
def run_job_to_completion(self, job_id: int) -> dict:
    """Run migrate_model_batch in a loop until the job completes, pauses, or fails.

    Returns a summary dict including the number of batches processed. The Celery
    task_id (`self.request.id`) is the polling handle the frontend uses.
    """
    job = MigrationJob.objects.get(pk=job_id)
    if job.status == "completed":
        return {"already_completed": True, "job_id": job_id}

    batches = 0
    try:
        for _ in range(MAX_BATCHES):
            result = migrate_model_batch.run(job_id=job_id)
            batches += 1
            job.refresh_from_db()

            if job.status in ("completed", "paused", "failed"):
                break

            # If this batch returned a transport error, back off briefly
            if isinstance(result, dict) and result.get("error") == "transport":
                time.sleep(2)

            # If throttled, sleep retry_after then continue
            if isinstance(result, dict) and result.get("throttled"):
                time.sleep(float(result.get("retry_after", 1)))
    finally:
        # If the loop ends without migrate_model_batch flipping the status
        # (MAX_BATCHES cap, raised exception, or this task being terminated by
        # Celery's task_time_limit before its parent SIGKILL hits), park the
        # job in "paused" so the UI reflects reality. The user can click
        # Resume to re-enqueue from last_cursor; IDMap keeps re-runs idempotent.
        job.refresh_from_db()
        update_fields = ["current_task_id", "updated_at"]
        job.current_task_id = ""
        if job.status == "running":
            job.status = "paused"
            update_fields.append("status")
        job.save(update_fields=update_fields)

    return {
        "job_id": job_id,
        "batches_processed": batches,
        "final_status": job.status,
        "rows_written": job.rows_written,
        "rows_errored": job.rows_errored,
    }
