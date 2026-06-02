from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from migration.models import MigrationErrorRecord, MigrationJob
from migration.tasks.pipeline import DEPENDENCY_ORDER, run_migration_pipeline
from migration.tasks.backfill_files import backfill_files_for_model, has_file_field
from migration.tasks.retry import retry_single_row
from migration.tasks.run_job import run_job_to_completion
from migration.tasks.verify import verify_migration


class _SuperuserOnlyMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_superuser


def _back(request, fallback="migration:overview"):
    return HttpResponseRedirect(request.META.get("HTTP_REFERER") or reverse(fallback))


class StartPipelineView(_SuperuserOnlyMixin, View):
    def post(self, request):
        for app, model in DEPENDENCY_ORDER:
            MigrationJob.objects.get_or_create(app_label=app, model_name=model)
        run_migration_pipeline.delay()
        return _back(request)


class PauseAllView(_SuperuserOnlyMixin, View):
    def post(self, request):
        MigrationJob.objects.exclude(status__in=("completed", "failed")).update(status="paused")
        return _back(request)


class ResumeAllView(_SuperuserOnlyMixin, View):
    def post(self, request):
        # Pull IDs first so we can enqueue per job; the previous version only
        # updated DB status without dispatching, leaving rows in "running"
        # state with no worker actually pulling from the sim.
        job_ids = list(MigrationJob.objects.filter(status="paused").values_list("pk", flat=True))
        MigrationJob.objects.filter(pk__in=job_ids).update(status="running")
        for jid in job_ids:
            result = run_job_to_completion.delay(job_id=jid)
            MigrationJob.objects.filter(pk=jid).update(current_task_id=result.id)
        return _back(request)


class ToggleDryRunView(_SuperuserOnlyMixin, View):
    def post(self, request):
        from django.conf import settings
        settings.MIGRATION_DRY_RUN = not getattr(settings, "MIGRATION_DRY_RUN", False)
        return _back(request)


class PauseJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        MigrationJob.objects.filter(pk=pk).update(status="paused")
        return _back(request)


class StopJobView(_SuperuserOnlyMixin, View):
    """Hard-stop a running job: revoke the Celery task and flip the DB row to
    paused. Unlike PauseJobView (which just sets status and lets the current
    batch finish), Stop sends SIGTERM to the worker process so the task halts
    immediately — useful when the in-flight batch is slow (file downloads,
    throttling waits) and the user wants to bail."""
    def post(self, request, pk):
        from lms.celery import app as celery_app
        job = MigrationJob.objects.filter(pk=pk).first()
        if job and job.current_task_id:
            try:
                celery_app.control.revoke(job.current_task_id, terminate=True, signal="SIGTERM")
            except Exception:
                # Broker unreachable — fall through; status update below still
                # tells the loop to break on its next iteration if it survives.
                pass
        MigrationJob.objects.filter(pk=pk).update(status="paused", current_task_id="")
        return _back(request)


class ResumeJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        # Flip the DB then dispatch a fresh Celery task — the previous version
        # only updated status, so the job appeared "running" in the UI but no
        # worker was actually pulling from the sim. IDMap + last_cursor keep
        # the re-enqueued run idempotent and resume from where it stopped.
        MigrationJob.objects.filter(pk=pk).update(status="running")
        result = run_job_to_completion.delay(job_id=pk)
        MigrationJob.objects.filter(pk=pk).update(current_task_id=result.id)
        return _back(request)


class RestartJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        if request.POST.get("confirm") != "yes":
            return _back(request)
        MigrationJob.objects.filter(pk=pk).update(
            status="pending", last_cursor="", rows_written=0, rows_errored=0,
            rows_skipped=0, rows_fetched=0, completed_at=None, started_at=None,
        )
        return _back(request)


class VerifyJobView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        verify_migration.delay(job_id=pk)
        return _back(request)


class BackfillFilesView(_SuperuserOnlyMixin, View):
    """Trigger an async file backfill for a single model. Independent of the
    MIGRATION_DOWNLOAD_FILES global switch — useful for fetching photos / PDFs
    after the row migration has completed without re-running the whole pipeline."""
    def post(self, request, pk):
        job = MigrationJob.objects.filter(pk=pk).first()
        if job and has_file_field(job.app_label, job.model_name):
            backfill_files_for_model.delay(
                app_label=job.app_label, model_name=job.model_name,
            )
        return _back(request)


class RetryErrorView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        err = MigrationErrorRecord.objects.get(pk=pk)
        retry_single_row.delay(job_id=err.job_id, old_pk=err.old_pk)
        return _back(request)


class ResolveErrorView(_SuperuserOnlyMixin, View):
    def post(self, request, pk):
        note = request.POST.get("note", "manual resolution")
        MigrationErrorRecord.objects.filter(pk=pk).update(
            resolved=True, resolved_at=timezone.now(), resolution_note=note,
        )
        return _back(request)
