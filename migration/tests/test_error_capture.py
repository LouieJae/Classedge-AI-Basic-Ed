import pytest

from migration.models import MigrationErrorRecord, MigrationJob
from migration.services.error_capture import capture


@pytest.fixture
def job():
    return MigrationJob.objects.create(app_label="roles", model_name="Role")


def _raise_from_inside_project(payload):
    raise ValueError("forced failure")


def test_capture_records_minimal_fields(job):
    try:
        _raise_from_inside_project({"id": 1})
    except ValueError as exc:
        capture(job=job, category="mapper_error", exc=exc, payload={"id": 1}, old_pk="1")
    err = MigrationErrorRecord.objects.get()
    assert err.category == "mapper_error"
    assert err.message == "forced failure"
    assert err.old_pk == "1"
    assert err.payload_excerpt == {"id": 1}
    assert err.traceback


def test_capture_source_line_points_at_project_frame(job):
    raising_line = _raise_from_inside_project.__code__.co_firstlineno + 1  # the `raise` line
    try:
        _raise_from_inside_project({})
    except Exception as exc:
        capture(job=job, category="mapper_error", exc=exc)
    err = MigrationErrorRecord.objects.get()
    assert err.source_file.endswith("test_error_capture.py")
    assert err.source_function == "_raise_from_inside_project"
    assert err.source_line == raising_line


def test_capture_redacts_secret_keys(job):
    try:
        raise ValueError("x")
    except Exception as exc:
        capture(job=job, category="mapper_error", exc=exc,
                payload={"id": 1, "password": "hunter2", "api_key": "k", "name": "ok"})
    err = MigrationErrorRecord.objects.get()
    assert err.payload_excerpt["password"] == "***"
    assert err.payload_excerpt["api_key"] == "***"
    assert err.payload_excerpt["name"] == "ok"


def test_capture_caps_long_message(job):
    long_msg = "x" * 1000
    try:
        raise ValueError(long_msg)
    except ValueError as exc:
        capture(job=job, category="mapper_error", exc=exc)
    err = MigrationErrorRecord.objects.get()
    assert len(err.message) <= 500
