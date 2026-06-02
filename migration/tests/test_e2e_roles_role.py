"""Opt-in end-to-end test against a real running simulation-lms server.

Skipped by default. Enable with `MIGRATION_E2E=1` and the env vars below.

Procedure:
    1. In one terminal, boot the simulation server:
       cd /home/classify/Desktop/Projects/simulation-lms/classedge
       /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/env/bin/python \\
           manage.py runserver 127.0.0.1:8001
    2. Mint a token (one-time):
       /home/classify/Desktop/Projects/HCCCI-Frontend/Classedge-Ai/env/bin/python \\
           manage.py shell -c "from migration_api.models import MigrationToken; \\
               p,_=MigrationToken.objects.create_token(label='e2e'); print(p)"
    3. In a second terminal, run:
       MIGRATION_E2E=1 \\
       MIGRATION_OLD_LMS_BASE_URL=http://127.0.0.1:8001 \\
       MIGRATION_OLD_LMS_TOKEN=<paste> \\
       env/bin/python -m pytest migration/tests/test_e2e_roles_role.py -v
"""
import os

import pytest

from migration.models import IDMap, MigrationJob
from migration.tasks.batch import migrate_model_batch
from migration.tasks.verify import verify_migration
from roles.models import Role

pytestmark = pytest.mark.skipif(
    os.environ.get("MIGRATION_E2E") != "1",
    reason="E2E test requires running simulation server and MIGRATION_E2E=1",
)


def test_full_role_migration_end_to_end(settings):
    settings.MIGRATION_OLD_LMS_BASE_URL = os.environ["MIGRATION_OLD_LMS_BASE_URL"]
    settings.MIGRATION_OLD_LMS_TOKEN = os.environ["MIGRATION_OLD_LMS_TOKEN"]
    settings.MIGRATION_BATCH_SIZE = 500

    job = MigrationJob.objects.create(app_label="roles", model_name="Role", status="running")
    # Drain pages until completion or 50 batches (safety).
    for _ in range(50):
        migrate_model_batch.run(job_id=job.id)
        job.refresh_from_db()
        if job.status == "completed":
            break

    assert job.status == "completed"
    new_count = Role.objects.count()
    assert new_count > 0
    assert IDMap.objects.filter(app_label="roles", model_name="Role").count() == new_count

    report = verify_migration.run(job_id=job.id)
    assert report["count_parity"] is True


def test_e2e_rerun_is_idempotent(settings):
    """Running the migration twice should not duplicate rows or errors."""
    settings.MIGRATION_OLD_LMS_BASE_URL = os.environ["MIGRATION_OLD_LMS_BASE_URL"]
    settings.MIGRATION_OLD_LMS_TOKEN = os.environ["MIGRATION_OLD_LMS_TOKEN"]
    settings.MIGRATION_BATCH_SIZE = 500

    job = MigrationJob.objects.get_or_create(app_label="roles", model_name="Role")[0]
    job.status = "running"
    job.last_cursor = ""
    job.rows_written = 0
    job.save()

    for _ in range(50):
        migrate_model_batch.run(job_id=job.id)
        job.refresh_from_db()
        if job.status == "completed":
            break

    first_pass_count = Role.objects.count()
    first_pass_idmap = IDMap.objects.filter(app_label="roles", model_name="Role").count()

    # Re-run from scratch
    job.status = "running"
    job.last_cursor = ""
    job.rows_written = 0
    job.save()
    for _ in range(50):
        migrate_model_batch.run(job_id=job.id)
        job.refresh_from_db()
        if job.status == "completed":
            break

    assert Role.objects.count() == first_pass_count
    assert IDMap.objects.filter(app_label="roles", model_name="Role").count() == first_pass_idmap
