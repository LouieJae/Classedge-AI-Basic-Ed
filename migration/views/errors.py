from django.views.generic import DetailView, ListView

from migration.models import MigrationErrorRecord
from .overview import _SuperuserOnly


class ErrorsView(_SuperuserOnly, ListView):
    template_name = "migration/errors.html"
    paginate_by = 50
    context_object_name = "errors"

    def get_queryset(self):
        qs = MigrationErrorRecord.objects.select_related("job").all()
        params = self.request.GET
        if params.get("job"):
            qs = qs.filter(job_id=params["job"])
        if params.get("category"):
            qs = qs.filter(category=params["category"])
        if params.get("old_pk"):
            qs = qs.filter(old_pk=params["old_pk"])
        if params.get("resolved") == "true":
            qs = qs.filter(resolved=True)
        elif params.get("resolved") == "false":
            qs = qs.filter(resolved=False)
        return qs


class ErrorDetailView(_SuperuserOnly, DetailView):
    model = MigrationErrorRecord
    template_name = "migration/_error_drawer.html"
    context_object_name = "err"
