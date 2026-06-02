"""Defaults loaded into Django settings for the migration app.

Import and merge in lms/settings.py:

    from migration.settings_defaults import apply as apply_migration_defaults
    apply_migration_defaults(globals())
"""
import os


def apply(settings_globals: dict) -> None:
    settings_globals.setdefault("MIGRATION_OLD_LMS_BASE_URL", os.environ.get("MIGRATION_OLD_LMS_BASE_URL", "http://localhost:8001"))
    settings_globals.setdefault("MIGRATION_OLD_LMS_TOKEN", os.environ.get("MIGRATION_OLD_LMS_TOKEN", ""))
    settings_globals.setdefault("MIGRATION_BATCH_SIZE", int(os.environ.get("MIGRATION_BATCH_SIZE", "500")))
    settings_globals.setdefault("MIGRATION_BATCH_INTERVAL_SECONDS", int(os.environ.get("MIGRATION_BATCH_INTERVAL_SECONDS", "30")))
    settings_globals.setdefault("MIGRATION_DRY_RUN", os.environ.get("MIGRATION_DRY_RUN", "False").lower() == "true")
    settings_globals.setdefault("MIGRATION_HTTP_TIMEOUT", int(os.environ.get("MIGRATION_HTTP_TIMEOUT", "30")))
    settings_globals.setdefault("MIGRATION_MAX_RETRIES", int(os.environ.get("MIGRATION_MAX_RETRIES", "5")))
    settings_globals.setdefault("MIGRATION_ENABLED", os.environ.get("MIGRATION_ENABLED", "False").lower() == "true")
    settings_globals.setdefault("MIGRATION_DASHBOARD_POLL_SECONDS", int(os.environ.get("MIGRATION_DASHBOARD_POLL_SECONDS", "3")))
    # Master switch for downloading files (Module PDFs, Profile photos,
    # ActivityQuestion instructions, etc.) from the sim during migration.
    # Default off so first-time imports finish quickly; set to true once row
    # migration is done, then re-run to backfill files (helper is idempotent).
    settings_globals.setdefault(
        "MIGRATION_DOWNLOAD_FILES",
        os.environ.get("MIGRATION_DOWNLOAD_FILES", "false").lower() == "true",
    )
