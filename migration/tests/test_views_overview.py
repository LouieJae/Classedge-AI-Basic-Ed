import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from migration.models import MigrationJob

User = get_user_model()


@pytest.fixture
def super_client():
    u = User.objects.create_superuser(username="root", email="r@r", password="pw")
    c = Client()
    c.force_login(u)
    return c


def test_overview_requires_superuser():
    c = Client()
    r = c.get("/operations/migration/")
    assert r.status_code in (302, 403)


def test_overview_renders_job_rows(super_client):
    MigrationJob.objects.create(app_label="roles", model_name="Role", rows_written=3, total_estimated=10)
    r = super_client.get("/operations/migration/")
    assert r.status_code == 200
    assert b"roles" in r.content.lower()
    assert b"Role" in r.content


def test_rows_fragment_returns_tbody(super_client):
    MigrationJob.objects.create(app_label="roles", model_name="Role")
    r = super_client.get("/operations/migration/rows/")
    assert r.status_code == 200
    assert b"<tbody" in r.content
