import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from migration.models import MigrationErrorRecord, MigrationJob

User = get_user_model()


@pytest.fixture
def super_client():
    u = User.objects.create_superuser(username="root", email="r@r", password="pw")
    c = Client()
    c.force_login(u)
    return c


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role", status="pending")


def test_pause_job(super_client, job):
    r = super_client.post(f"/operations/migration/actions/job/{job.id}/pause/")
    assert r.status_code in (200, 302)
    job.refresh_from_db()
    assert job.status == "paused"


def test_resume_job(super_client, job):
    job.status = "paused"; job.save()
    super_client.post(f"/operations/migration/actions/job/{job.id}/resume/")
    job.refresh_from_db()
    assert job.status == "running"


def test_restart_job_clears_cursor_and_counters(super_client, job):
    job.last_cursor = "42"; job.rows_written = 10; job.rows_errored = 2; job.status = "completed"; job.save()
    super_client.post(f"/operations/migration/actions/job/{job.id}/restart/", {"confirm": "yes"})
    job.refresh_from_db()
    assert job.last_cursor == ""
    assert job.rows_written == 0
    assert job.rows_errored == 0
    assert job.status == "pending"


def test_pause_all_and_resume_all(super_client):
    MigrationJob.objects.create(app_label="a", model_name="A", status="running")
    MigrationJob.objects.create(app_label="b", model_name="B", status="running")
    super_client.post("/operations/migration/actions/pause-all/")
    assert MigrationJob.objects.filter(status="paused").count() == 2
    super_client.post("/operations/migration/actions/resume-all/")
    assert MigrationJob.objects.filter(status="running").count() == 2


def test_resolve_error(super_client, job):
    err = MigrationErrorRecord.objects.create(job=job, category="mapper_error", message="x",
                                              old_app="roles", old_model="Role")
    super_client.post(f"/operations/migration/actions/errors/{err.id}/resolve/", {"note": "manual"})
    err.refresh_from_db()
    assert err.resolved is True
    assert "manual" in err.resolution_note
