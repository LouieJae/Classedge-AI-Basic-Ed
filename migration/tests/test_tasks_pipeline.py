from unittest.mock import patch

import pytest
from django.test import override_settings

from migration.models import MigrationJob
from migration.tasks.pipeline import DEPENDENCY_ORDER, run_migration_pipeline


def test_dependency_order_starts_with_roles_role():
    assert DEPENDENCY_ORDER[0] == ("roles", "Role")


@override_settings(MIGRATION_ENABLED=True)
def test_run_pipeline_creates_missing_jobs():
    assert MigrationJob.objects.count() == 0
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    assert MigrationJob.objects.filter(app_label="roles", model_name="Role").exists()
    m.assert_called()


@override_settings(MIGRATION_ENABLED=False)
def test_run_pipeline_noop_when_disabled():
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    m.assert_not_called()


@override_settings(MIGRATION_ENABLED=True)
def test_run_pipeline_skips_completed_jobs():
    # Seed every model in DEPENDENCY_ORDER as completed so nothing gets enqueued.
    for app, model in DEPENDENCY_ORDER:
        MigrationJob.objects.create(app_label=app, model_name=model, status="completed")
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    m.assert_not_called()


@override_settings(MIGRATION_ENABLED=True)
def test_run_pipeline_skips_paused_jobs():
    for app, model in DEPENDENCY_ORDER:
        MigrationJob.objects.create(app_label=app, model_name=model, status="paused")
    with patch("migration.tasks.pipeline.migrate_model_batch.delay") as m:
        run_migration_pipeline.run()
    m.assert_not_called()
