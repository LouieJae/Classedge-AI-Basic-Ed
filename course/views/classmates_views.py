from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from course.models.subject_enrollment_model import SubjectEnrollment
from subject.models import Subject


@login_required
def classmates(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)

    viewer_enrollment = (
        SubjectEnrollment.objects
        .filter(subject=subject, student=request.user, status="enrolled")
        .select_related("semester")
        .order_by("-enrollment_date")
        .first()
    )
    if not viewer_enrollment or not viewer_enrollment.semester:
        raise Http404("You are not enrolled in this subject.")

    semester = viewer_enrollment.semester
    classmates_qs = (
        SubjectEnrollment.objects
        .filter(
            subject=subject,
            semester=semester,
            status="enrolled",
            student__isnull=False,
        )
        .exclude(student=request.user)
        .select_related("student", "student__profile")
        .order_by("student__last_name", "student__first_name")
    )

    return render(
        request,
        "student/classmates.html",
        {
            "subject": subject,
            "semester": semester,
            "classmates": classmates_qs,
            "classmates_count": classmates_qs.count(),
        },
    )
