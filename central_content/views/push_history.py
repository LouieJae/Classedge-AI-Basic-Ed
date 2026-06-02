from django.shortcuts import render

from central_content.models import PushJob, School
from central_content.permissions import central_role_required


@central_role_required("publisher", "reviewer")
def push_history_list(request):
    jobs = PushJob.objects.select_related(
        "central_subject", "target_school", "triggered_by",
    ).all()
    school_id = request.GET.get("school")
    if school_id:
        jobs = jobs.filter(target_school_id=school_id)
    status = request.GET.get("status")
    if status:
        jobs = jobs.filter(status=status)
    kind = request.GET.get("kind")
    if kind:
        jobs = jobs.filter(kind=kind)
    schools = School.objects.order_by("name")
    return render(
        request,
        "central_content/push_history/list.html",
        {
            "jobs": jobs[:200],
            "schools": schools,
            "filter_school": school_id,
            "filter_status": status,
            "filter_kind": kind,
        },
    )
