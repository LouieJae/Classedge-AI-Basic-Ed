import pytest
import responses
from django.test import override_settings

from migration.models import IDMap, MigrationErrorRecord, MigrationJob, MigrationRunLog
from migration.tasks.batch import migrate_model_batch
from roles.models import Role


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")


def _page(results, next_cursor=None, has_more=False, total=None):
    return {
        "results": results,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total_estimated": total if total is not None else len(results),
    }


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_writes_rows_and_advances_cursor(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([{"id": 1, "name": "Teacher", "permissions": [],
                               "created_at": None, "updated_at": None}],
                             next_cursor="1", has_more=True, total=2),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    job.refresh_from_db()
    assert job.rows_written == 1
    assert job.last_cursor == "1"
    assert Role.objects.filter(name="Teacher").exists()
    assert IDMap.resolve("roles", "Role", "1") is not None


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_completes_job_when_no_next_cursor(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([], next_cursor=None, has_more=False, total=0),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    job.refresh_from_db()
    assert job.status == "completed"


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_paused_job_returns_early(job):
    job.status = "paused"
    job.save()
    migrate_model_batch.run(job_id=job.id)
    assert len(responses.calls) == 0


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_mapper_error_recorded_with_source_info(job, monkeypatch):
    def boom(payload):
        raise ValueError("mapper exploded")
    from migration.mappers.base import _REGISTRY
    original = _REGISTRY.get(("roles", "Role"))
    _REGISTRY[("roles", "Role")] = boom

    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([{"id": 1, "name": "Teacher", "permissions": []}],
                             next_cursor=None, has_more=False, total=1),
                  status=200)
    try:
        migrate_model_batch.run(job_id=job.id)
    finally:
        if original:
            _REGISTRY[("roles", "Role")] = original

    err = MigrationErrorRecord.objects.get()
    assert err.category == "mapper_error"
    assert err.old_pk == "1"
    assert err.source_file
    job.refresh_from_db()
    assert job.rows_errored == 1


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_auth_error_pauses_job(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/", status=401)
    migrate_model_batch.run(job_id=job.id)
    job.refresh_from_db()
    assert job.status == "paused"
    assert MigrationErrorRecord.objects.filter(category="auth_error").exists()


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_batch_writes_run_log_entry(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json=_page([{"id": 1, "name": "T", "permissions": [],
                               "created_at": None, "updated_at": None}],
                             next_cursor=None, has_more=False, total=1),
                  status=200)
    migrate_model_batch.run(job_id=job.id)
    log = MigrationRunLog.objects.get()
    assert log.job_id == job.id
    assert log.rows_in_page == 1
    assert log.rows_written == 1
    assert log.http_status == 200
