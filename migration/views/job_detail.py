from django.views.generic import TemplateView

from migration.models import MigrationJob, MigrationRunLog
from .overview import _SuperuserOnly


class JobDetailView(_SuperuserOnly, TemplateView):
    template_name = "migration/job_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = MigrationJob.objects.get(pk=kwargs["pk"])
        ctx["job"] = job
        ctx["logs"] = MigrationRunLog.objects.filter(job=job)[:50]
        ctx["recent_errors"] = job.errors.all()[:10]
        return ctx


class JobDetailFragment(_SuperuserOnly, TemplateView):
    template_name = "migration/_run_log_tail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        job = MigrationJob.objects.get(pk=kwargs["pk"])
        ctx["job"] = job
        ctx["logs"] = MigrationRunLog.objects.filter(job=job)[:50]
        return ctx
