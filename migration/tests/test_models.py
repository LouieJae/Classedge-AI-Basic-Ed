import pytest

from migration.models import IDMap, MigrationErrorRecord, MigrationJob, MigrationRunLog


def test_migrationjob_unique_per_app_model():
    MigrationJob.objects.create(app_label="roles", model_name="Role")
    with pytest.raises(Exception):
        MigrationJob.objects.create(app_label="roles", model_name="Role")


def test_migrationjob_default_status_pending():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    assert job.status == "pending"


def test_idmap_unique_per_app_model_old_pk():
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk="11")
    with pytest.raises(Exception):
        IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk="22")


def test_idmap_lookup_returns_new_pk():
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="7", new_pk="77")
    assert IDMap.resolve("roles", "Role", "7") == "77"
    assert IDMap.resolve("roles", "Role", "missing") is None


def test_runlog_links_to_job():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    log = MigrationRunLog.objects.create(job=job, rows_in_page=10, rows_written=10)
    assert log.job_id == job.id
    assert log.is_retry is False
    assert log.is_dry_run is False


def test_error_record_required_fields():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    err = MigrationErrorRecord.objects.create(
        job=job,
        category="mapper_error",
        message="boom",
        old_app="roles",
        old_model="Role",
    )
    assert err.resolved is False
    assert err.payload_excerpt == {}
