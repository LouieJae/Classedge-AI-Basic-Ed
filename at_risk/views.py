from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from activity.utils.authorization import check_subject_access
from at_risk.calculator import calculate_risk_scores
from course.models.semester_model import Semester
from subject.models.subject_model import Subject


@login_required
def dashboard(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)

    has_access, redirect_resp = check_subject_access(
        request, subject, require_teacher=True,
    )
    if not has_access:
        return redirect_resp

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()

    results = []
    high_count = 0
    medium_count = 0

    if semester:
        results = calculate_risk_scores(subject, semester)
        high_count = sum(1 for r in results if r["risk_level"] == "high")
        medium_count = sum(1 for r in results if r["risk_level"] == "medium")

    return render(
        request,
        "at_risk/dashboard.html",
        {
            "subject": subject,
            "semester": semester,
            "results": results,
            "high_count": high_count,
            "medium_count": medium_count,
            "total_enrolled": len(results),
        },
    )
