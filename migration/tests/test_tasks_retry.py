import pytest
import responses
from django.test import override_settings

from migration.models import IDMap, MigrationErrorRecord, MigrationJob
from migration.tasks.retry import retry_single_row
from roles.models import Role


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_retry_fetches_single_row_and_writes(job):
    responses.add(responses.GET, "http://old/api/migration/roles/role/9/",
                  json={"id": 9, "name": "Solo", "permissions": [],
                        "created_at": None, "updated_at": None}, status=200)
    retry_single_row.run(job_id=job.id, old_pk="9")
    assert Role.objects.filter(name="Solo").exists()
    assert IDMap.resolve("roles", "Role", "9") is not None


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_retry_marks_matching_errors_resolved(job):
    err = MigrationErrorRecord.objects.create(
        job=job, category="mapper_error", message="x",
        old_app="roles", old_model="Role", old_pk="9",
    )
    responses.add(responses.GET, "http://old/api/migration/roles/role/9/",
                  json={"id": 9, "name": "Solo", "permissions": [],
                        "created_at": None, "updated_at": None}, status=200)
    retry_single_row.run(job_id=job.id, old_pk="9")
    err.refresh_from_db()
    assert err.resolved is True


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_retry_records_new_error_on_failure(job):
    from migration.mappers.base import _REGISTRY
    original = _REGISTRY.get(("roles", "Role"))

    def buggy(p):
        raise ValueError("boom")
    _REGISTRY[("roles", "Role")] = buggy

    responses.add(responses.GET, "http://old/api/migration/roles/role/9/",
                  json={"id": 9, "name": "X", "permissions": []}, status=200)
    try:
        retry_single_row.run(job_id=job.id, old_pk="9")
    finally:
        if original:
            _REGISTRY[("roles", "Role")] = original

    assert MigrationErrorRecord.objects.filter(category="mapper_error").exists()
