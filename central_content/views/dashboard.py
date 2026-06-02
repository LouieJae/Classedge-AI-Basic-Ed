# central_content/views/dashboard.py
from django.shortcuts import render

from central_content.models import (
    AuditLogEntry,
    CentralActivity,
    CentralModule,
    CentralStaff,
    CentralSubject,
)
from central_content.permissions import central_role_required


_ALL = (CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER)


@central_role_required(*_ALL)
def dashboard(request):
    def _counts(model):
        return {
            "draft": model.objects.filter(state=model.State.DRAFT).count(),
            "in_review": model.objects.filter(state=model.State.IN_REVIEW).count(),
            "approved": model.objects.filter(state=model.State.APPROVED).count(),
        }

    context = {
        "subject_counts": _counts(CentralSubject),
        "module_counts": _counts(CentralModule),
        "activity_counts": _counts(CentralActivity),
        "recent_audit": AuditLogEntry.objects.select_related("actor")[:20],
        "review_queue": CentralSubject.objects.filter(
            state=CentralSubject.State.IN_REVIEW
        )[:10],
    }
    return render(request, "central_content/dashboard.html", context)
