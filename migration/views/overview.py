from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

from migration.models import MigrationJob, MigrationSettings
from migration.services.progress import eta_seconds, rows_per_minute
from migration.tasks.backfill_files import has_file_field


class _SuperuserOnly(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser


def _augment(jobs):
    return [
        {
            "job": j,
            "rpm": round(rows_per_minute(j), 1),
            "eta": eta_seconds(j),
            "error_count": j.errors.filter(resolved=False).count(),
            "percent": (int((j.rows_written / j.total_estimated) * 100) if j.total_estimated else 0),
            "has_files": has_file_field(j.app_label, j.model_name),
        }
        for j in jobs
    ]


class OverviewView(_SuperuserOnly, TemplateView):
    template_name = "migration/overview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = _augment(MigrationJob.objects.all())
        ctx["jobs"] = rows
        ctx["totals"] = {
            "jobs": len(rows),
            "running": sum(1 for r in rows if r["job"].status == "running"),
            "completed": sum(1 for r in rows if r["job"].status == "completed"),
            "failed": sum(1 for r in rows if r["job"].status == "failed"),
            "errors": sum(r["error_count"] for r in rows),
        }
        ctx["old_lms_base_url"] = MigrationSettings.load().effective_base_url()
        ctx["poll_seconds"] = settings.MIGRATION_DASHBOARD_POLL_SECONDS
        ctx["dry_run"] = settings.MIGRATION_DRY_RUN
        return ctx


class JobRowsFragment(_SuperuserOnly, TemplateView):
    template_name = "migration/_job_row.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["jobs"] = _augment(MigrationJob.objects.all())
        return ctx
