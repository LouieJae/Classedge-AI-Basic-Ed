from celery.result import AsyncResult
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView

from migration.models import MigrationJob, MigrationSettings
from migration.sequence_metadata import get_cards
from migration.tasks.run_job import run_job_to_completion
from .overview import _SuperuserOnly


class SequenceView(_SuperuserOnly, TemplateView):
    template_name = "migration/sequence.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cards"] = get_cards()
        ctx["old_lms_base_url"] = MigrationSettings.load().effective_base_url()
        return ctx


class RunJobView(_SuperuserOnly, View):
    """Kick off a one-click drain of the named migration job.

    Resets the job to a clean 'running' state and enqueues `run_job_to_completion`
    which loops through batches until the job completes or pauses.
    Responds with JSON: {ok, task_id, job_id} so the frontend can poll.
    """

    def post(self, request, app, model):
        job, _created = MigrationJob.objects.get_or_create(
            app_label=app, model_name=model,
        )
        # Reset for a fresh run unless the caller passed resume=true
        if request.POST.get("resume") != "true":
            job.status = "running"
            job.last_cursor = ""
            job.rows_written = 0
            job.rows_errored = 0
            job.rows_skipped = 0
            job.rows_fetched = 0
            job.started_at = None
            job.completed_at = None
            job.save()
        else:
            job.status = "running"
            job.save(update_fields=["status", "updated_at"])

        result = run_job_to_completion.delay(job_id=job.id)
        # Record the Celery task ID so a later Stop action can revoke it
        # (terminate=True) instead of waiting for the loop to notice "paused".
        MigrationJob.objects.filter(pk=job.id).update(current_task_id=result.id)
        return JsonResponse({
            "ok": True,
            "task_id": result.id,
            "job_id": job.id,
        })


class JobStatusView(_SuperuserOnly, View):
    """Poll endpoint for the sequence dashboard.

    Returns:
        {
          app, model, status, written, errored, total_estimated, percent,
          last_cursor, started_at, completed_at, error_count,
          task_state (if task_id provided)
        }
    """

    def get(self, request, app, model):
        job = MigrationJob.objects.filter(app_label=app, model_name=model).first()
        if not job:
            return JsonResponse({
                "app": app, "model": model,
                "status": "idle",
                "written": 0, "errored": 0, "total_estimated": 0, "percent": 0,
                "error_count": 0,
            })

        percent = (
            int((job.rows_written / job.total_estimated) * 100)
            if job.total_estimated else 0
        )
        out = {
            "app": app,
            "model": model,
            "job_id": job.id,
            "status": job.status,
            "written": job.rows_written,
            "errored": job.rows_errored,
            "total_estimated": job.total_estimated,
            "percent": percent,
            "last_cursor": job.last_cursor,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_count": job.errors.filter(resolved=False).count(),
        }

        task_id = request.GET.get("task_id")
        if task_id:
            res = AsyncResult(task_id)
            out["task_state"] = res.state
            if res.successful():
                out["task_result"] = res.result
        return JsonResponse(out)
