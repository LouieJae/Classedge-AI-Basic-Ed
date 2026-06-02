import logging
from django.conf import settings
from django.utils import timezone

from celery import shared_task

from migration.client.exceptions import AuthError, MigrationClientError, PermanentError, ThrottledError, TransientError
from migration.client.http import OldLmsClient
from migration.mappers.base import MissingFKError, get_mapper
from migration.models import MigrationJob, MigrationRunLog
from migration.services.error_capture import capture
from migration.writers.base import RowWriter

logger = logging.getLogger(__name__)


@shared_task(name="migration.tasks.migrate_model_batch")
def migrate_model_batch(job_id: int) -> dict:
    job = MigrationJob.objects.get(pk=job_id)
    if job.status not in ("pending", "running"):
        logger.info("Job %s status=%s, skipping batch", job_id, job.status)
        return {"skipped": True, "status": job.status}

    if job.started_at is None:
        job.started_at = timezone.now()
    job.status = "running"
    job.save(update_fields=["status", "started_at", "updated_at"])

    client = OldLmsClient()
    run_log = MigrationRunLog.objects.create(
        job=job,
        cursor_in=job.last_cursor,
        is_dry_run=bool(getattr(settings, "MIGRATION_DRY_RUN", False) or job.dry_run),
    )

    try:
        page = client.fetch_page(
            job.app_label, _model_url(job.model_name),
            cursor=job.last_cursor or None,
            limit=settings.MIGRATION_BATCH_SIZE,
        )
        run_log.http_status = 200
    except AuthError as exc:
        capture(job=job, category="auth_error", exc=exc, run_log=run_log)
        job.status = "paused"
        job.save(update_fields=["status", "updated_at"])
        run_log.http_status = 401
        _finalize_log(run_log)
        return {"paused": True}
    except ThrottledError as exc:
        capture(job=job, category="throttled", exc=exc, run_log=run_log)
        run_log.http_status = 429
        run_log.notes = f"retry_after={exc.retry_after}"
        _finalize_log(run_log)
        return {"throttled": True, "retry_after": exc.retry_after}
    except (TransientError, PermanentError, MigrationClientError) as exc:
        capture(job=job, category="transport_error", exc=exc, run_log=run_log)
        run_log.http_status = 0
        _finalize_log(run_log)
        return {"error": "transport"}

    results = page.get("results", [])
    job.total_estimated = page.get("total_estimated", job.total_estimated)
    job.rows_fetched += len(results)
    run_log.rows_in_page = len(results)

    mapper = get_mapper(job.app_label, job.model_name)
    writer = RowWriter(app_label=job.app_label, model_name=job.model_name)
    dry_run = run_log.is_dry_run

    for idx, payload in enumerate(results):
        old_pk = str(payload.get("id", ""))
        try:
            result = mapper(payload)
            writer.write(old_pk=old_pk, mapper_result=result, dry_run=dry_run)
            run_log.rows_written += 1
            job.rows_written += 1
        except MissingFKError as exc:
            capture(job=job, category="missing_fk", exc=exc,
                    payload=payload, old_pk=old_pk,
                    batch_cursor=job.last_cursor, batch_index=idx,
                    field=exc.field_name,
                    expected=f"IDMap {exc.target_app}.{exc.target_model} old_pk={exc.old_pk}",
                    actual="not found", run_log=run_log)
            run_log.rows_errored += 1
            job.rows_errored += 1
        except Exception as exc:
            category = _categorize(exc)
            capture(job=job, category=category, exc=exc,
                    payload=payload, old_pk=old_pk,
                    batch_cursor=job.last_cursor, batch_index=idx,
                    run_log=run_log)
            run_log.rows_errored += 1
            job.rows_errored += 1

    next_cursor = page.get("next_cursor")
    if next_cursor:
        job.last_cursor = str(next_cursor)
    else:
        job.status = "completed"
        job.completed_at = timezone.now()

    run_log.cursor_out = job.last_cursor or ""
    _finalize_log(run_log)
    job.save()
    return {
        "ok": True,
        "rows_written": run_log.rows_written,
        "rows_errored": run_log.rows_errored,
        "next_cursor": next_cursor,
    }


def _finalize_log(run_log: MigrationRunLog) -> None:
    run_log.finished_at = timezone.now()
    run_log.save()


def _model_url(model_name: str) -> str:
    """Role -> role; StudentActivity -> student-activity; Teacher_Attendance -> teacher-attendance."""
    out: list[str] = []
    prev_is_sep = True
    for ch in model_name:
        if ch == "_":
            if out and out[-1] != "-":
                out.append("-")
            prev_is_sep = True
            continue
        if ch.isupper() and not prev_is_sep:
            out.append("-")
        out.append(ch.lower())
        prev_is_sep = False
    return "".join(out)


def _categorize(exc: Exception) -> str:
    from django.core.exceptions import ValidationError
    from django.db import DataError, IntegrityError

    if isinstance(exc, ValidationError):
        return "validation"
    if isinstance(exc, (IntegrityError, DataError)):
        return "db_error"
    return "mapper_error"
