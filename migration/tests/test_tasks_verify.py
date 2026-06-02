import pytest
import responses
from django.test import override_settings

from migration.models import IDMap, MigrationJob
from migration.tasks.verify import verify_migration
from roles.models import Role


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="completed")


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_verify_matches_counts_when_equal(job):
    role = Role.objects.create(name="A")
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk=str(role.pk))
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": [], "next_cursor": None, "has_more": False, "total_estimated": 1},
                  status=200)
    report = verify_migration.run(job_id=job.id)
    assert report["count_parity"] is True
    assert report["old_count"] == 1
    assert report["new_count"] == 1


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_verify_flags_count_mismatch(job):
    Role.objects.create(name="A")
    Role.objects.create(name="B")
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="1", new_pk="1")
    IDMap.objects.create(app_label="roles", model_name="Role", old_pk="2", new_pk="2")
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": [], "next_cursor": None, "has_more": False, "total_estimated": 5},
                  status=200)
    report = verify_migration.run(job_id=job.id)
    assert report["count_parity"] is False
    assert report["old_count"] == 5
    assert report["new_count"] == 2


@override_settings(MIGRATION_OLD_LMS_BASE_URL="http://old/", MIGRATION_OLD_LMS_TOKEN="t")
@responses.activate
def test_verify_persists_report_on_job(job):
    Role.objects.create(name="A")
    responses.add(responses.GET, "http://old/api/migration/roles/role/",
                  json={"results": [], "next_cursor": None, "has_more": False, "total_estimated": 1},
                  status=200)
    verify_migration.run(job_id=job.id)
    job.refresh_from_db()
    assert "old_count" in job.last_verification
