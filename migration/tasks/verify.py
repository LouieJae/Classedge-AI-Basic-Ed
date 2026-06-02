from celery import shared_task
from django.apps import apps

from migration.client.http import OldLmsClient
from migration.models import IDMap, MigrationJob
from migration.tasks.batch import _model_url


@shared_task(name="migration.tasks.verify_migration")
def verify_migration(job_id: int) -> dict:
    job = MigrationJob.objects.get(pk=job_id)
    target_model = apps.get_model(job.app_label, job.model_name)

    client = OldLmsClient()
    head = client.fetch_page(job.app_label, _model_url(job.model_name), limit=1)
    old_count = int(head.get("total_estimated", 0))

    new_count = target_model.objects.count()
    idmap_count = IDMap.objects.filter(app_label=job.app_label, model_name=job.model_name).count()

    report = {
        "old_count": old_count,
        "new_count": new_count,
        "idmap_count": idmap_count,
        "count_parity": old_count == new_count,
        "idmap_complete": idmap_count == new_count,
    }
    job.last_verification = report
    job.save(update_fields=["last_verification", "updated_at"])
    return report
