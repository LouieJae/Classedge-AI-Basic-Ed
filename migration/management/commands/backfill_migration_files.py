"""Backfill files for rows already migrated by the migration pipeline.

Use after running the main migration with MIGRATION_DOWNLOAD_FILES=false:
the row data is in place, but file/image fields are empty. This command
walks each model's file field, pulls the relative path from the sim's
payload (via the migration API), and downloads only what's missing.

Forces downloads even when MIGRATION_DOWNLOAD_FILES is off, so dev
environments can backfill without flipping the master switch.

Usage:
    manage.py backfill_migration_files                    # all known models
    manage.py backfill_migration_files --model module.Module
    manage.py backfill_migration_files --limit 50         # cap rows per model
    manage.py backfill_migration_files --dry-run          # report counts only
"""
from django.core.management.base import BaseCommand

from migration.tasks.backfill_files import FILE_FIELDS, backfill_files_for_model


class Command(BaseCommand):
    help = "Backfill file/image fields for previously migrated rows."

    def add_arguments(self, parser):
        parser.add_argument("--model", help="Limit to one model, e.g. 'module.Module'.")
        parser.add_argument("--limit", type=int, help="Max rows per model.")
        parser.add_argument("--dry-run", action="store_true", help="Count only, don't download.")

    def handle(self, *args, **options):
        model_filter = options.get("model")
        limit = options.get("limit")
        dry_run = options.get("dry_run", False)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "--dry-run is no longer supported; the backfill task always "
                "skips rows whose file already exists locally. Re-run without --dry-run."
            ))
            return

        targets = list(FILE_FIELDS.keys())
        if model_filter:
            wanted = model_filter.lower()
            targets = [(a, m) for (a, m) in targets if f"{a}.{m}".lower() == wanted]
            if not targets:
                known = [f"{a}.{m}" for (a, m) in FILE_FIELDS.keys()]
                self.stderr.write(f"No known file field for {model_filter}. Known: {known}")
                return

        for app_label, model_name in targets:
            field = FILE_FIELDS[(app_label, model_name)]
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n=== {app_label}.{model_name}.{field} ==="))
            # Run the same Celery task synchronously so the CLI shares the
            # exact code path the dashboard's Fetch Files button uses.
            result = backfill_files_for_model.run(
                app_label=app_label, model_name=model_name, limit=limit,
            )
            self.stdout.write(self.style.SUCCESS("  " + " ".join(
                f"{k}={v}" for k, v in result.items() if k not in ("app", "model", "field")
            )))
