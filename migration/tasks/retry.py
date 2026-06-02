from celery import shared_task
from django.utils import timezone

from migration.client.http import OldLmsClient
from migration.mappers.base import MissingFKError, get_mapper
from migration.models import MigrationErrorRecord, MigrationJob
from migration.services.error_capture import capture
from migration.tasks.batch import _categorize, _model_url
from migration.writers.base import RowWriter


@shared_task(name="migration.tasks.retry_single_row")
def retry_single_row(job_id: int, old_pk: str) -> dict:
    job = MigrationJob.objects.get(pk=job_id)
    client = OldLmsClient()
    mapper = get_mapper(job.app_label, job.model_name)
    writer = RowWriter(app_label=job.app_label, model_name=job.model_name)

    try:
        payload = client.fetch_by_pk(job.app_label, _model_url(job.model_name), old_pk)
    except Exception as exc:
        capture(job=job, category="transport_error", exc=exc, old_pk=old_pk)
        return {"ok": False, "stage": "fetch"}

    try:
        result = mapper(payload)
        writer.write(old_pk=str(old_pk), mapper_result=result, dry_run=False)
    except MissingFKError as exc:
        capture(job=job, category="missing_fk", exc=exc, payload=payload, old_pk=str(old_pk),
                field=exc.field_name,
                expected=f"IDMap {exc.target_app}.{exc.target_model} old_pk={exc.old_pk}",
                actual="not found")
        return {"ok": False, "stage": "fk"}
    except Exception as exc:
        capture(job=job, category=_categorize(exc), exc=exc, payload=payload, old_pk=str(old_pk))
        return {"ok": False, "stage": "write"}

    MigrationErrorRecord.objects.filter(
        job=job, old_pk=str(old_pk), resolved=False,
    ).update(resolved=True, resolved_at=timezone.now(), resolution_note="resolved via retry_single_row")
    return {"ok": True}
