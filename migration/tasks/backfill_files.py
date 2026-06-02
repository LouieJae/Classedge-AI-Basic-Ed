"""Per-model file backfill for migrated rows.

Walks IDMap for the given (app, model), pulls the file path from the sim
for each row whose target FileField is empty (or whose file is missing
on disk), downloads it, and saves the path back. Idempotent: re-runs
skip rows whose files already exist locally.

Independent of the MIGRATION_DOWNLOAD_FILES master switch — this task
always attempts downloads. That lets the UI offer a per-model "Fetch
Files" button without forcing a global toggle.
"""
import time
from pathlib import Path

from celery import shared_task
from django.apps import apps
from django.conf import settings

from migration.client.exceptions import ThrottledError
from migration.client.http import OldLmsClient
from migration.models import IDMap


def _fetch_by_pk_with_throttle_retry(client, app_label, model_name, old_pk, max_attempts=6):
    """fetch_by_pk that honors 429 Retry-After instead of failing.

    The shared `_get` raises ThrottledError on 429 because the page-list path
    has an orchestrator (run_job_to_completion) that handles backoff. The
    backfill task has no such orchestrator — it would otherwise mark every
    throttled row as failed and skip its file. So we retry here, sleeping
    retry_after seconds between attempts, with a hard cap on attempts."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return client.fetch_by_pk(app_label, model_name, old_pk)
        except ThrottledError as exc:
            last_exc = exc
            time.sleep(max(float(getattr(exc, "retry_after", 1) or 1), 1.0))
    raise last_exc if last_exc else RuntimeError("throttle retry exhausted")


# (app_label, model_name) → field_name. Same fields the mappers write to.
FILE_FIELDS = {
    ("accounts", "Profile"): "student_photo",
    ("subject", "Subject"): "subject_photo",
    ("module", "Module"): "file",
    ("activity", "Activity"): "activity_file_instruction",
    ("activity", "ActivityQuestion"): "question_instruction",
    ("activity", "QuestionChoice"): "choice_image",
    ("activity", "StudentQuestion"): "uploaded_file",
}


def has_file_field(app_label: str, model_name: str) -> bool:
    return (app_label, model_name) in FILE_FIELDS


@shared_task(name="migration.tasks.backfill_files_for_model", bind=True)
def backfill_files_for_model(self, app_label: str, model_name: str, limit: int | None = None) -> dict:
    field_name = FILE_FIELDS.get((app_label, model_name))
    if field_name is None:
        return {"error": "no_file_field", "app": app_label, "model": model_name}

    Model = apps.get_model(app_label, model_name)
    client = OldLmsClient()
    media_root = Path(settings.MEDIA_ROOT)

    counters = {"scanned": 0, "downloaded": 0, "already_local": 0,
                "no_path_on_sim": 0, "sim_missing": 0, "failed": 0}

    id_pairs = IDMap.objects.filter(
        app_label=app_label, model_name=model_name,
    ).values_list("old_pk", "new_pk")

    for old_pk, new_pk in id_pairs:
        if limit and counters["scanned"] >= limit:
            break
        counters["scanned"] += 1

        instance = Model.objects.filter(pk=new_pk).only(field_name).first()
        if instance is None:
            continue

        current = getattr(instance, field_name)
        if current and (media_root / str(current)).is_file():
            counters["already_local"] += 1
            continue

        try:
            payload = _fetch_by_pk_with_throttle_retry(client, app_label, model_name, old_pk)
        except Exception:
            counters["failed"] += 1
            continue

        rel_path = (payload or {}).get(field_name) or ""
        if not rel_path:
            counters["no_path_on_sim"] += 1
            continue

        target_path = media_root / rel_path
        if target_path.is_file() and target_path.stat().st_size > 0:
            setattr(instance, field_name, rel_path)
            instance.save(update_fields=[field_name])
            counters["already_local"] += 1
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            blob = client.fetch_file_bytes(rel_path)
        except Exception:
            counters["failed"] += 1
            continue
        if blob is None:
            counters["sim_missing"] += 1
            continue

        tmp = target_path.with_suffix(target_path.suffix + ".partial")
        tmp.write_bytes(blob)
        tmp.replace(target_path)
        setattr(instance, field_name, rel_path)
        instance.save(update_fields=[field_name])
        counters["downloaded"] += 1

    return {"app": app_label, "model": model_name, "field": field_name, **counters}
