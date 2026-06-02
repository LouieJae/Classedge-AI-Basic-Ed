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
def err():
    job = MigrationJob.objects.create(app_label="roles", model_name="Role")
    return MigrationErrorRecord.objects.create(
        job=job, category="mapper_error", message="boom",
        old_app="roles", old_model="Role", old_pk="7",
        source_file="/abs/path/migration/mappers/roles_role.py",
        source_line=243, source_function="map_role",
        payload_excerpt={"id": 7, "name": "X"},
    )


def test_errors_index_lists_records(super_client, err):
    r = super_client.get("/operations/migration/errors/")
    assert r.status_code == 200
    assert b"boom" in r.content


def test_error_detail_shows_source_line_and_vscode_link(super_client, err):
    r = super_client.get(f"/operations/migration/errors/{err.id}/")
    assert r.status_code == 200
    assert b"roles_role.py:243" in r.content
    assert b"vscode://file" in r.content
    assert b"map_role" in r.content


def test_errors_filter_by_category(super_client, err):
    r = super_client.get("/operations/migration/errors/?category=missing_fk")
    assert r.status_code == 200
    assert b"boom" not in r.content
