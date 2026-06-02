from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from activity.utils.authorization import check_subject_access
from ai_content.forms import GenerationRequestForm
from ai_content.models import GenerationRequest
from ai_content.tasks import generate_school_content
from course.models.semester_model import Semester
from course.models.term_model import Term
from django.utils import timezone
from subject.models.subject_model import Subject


@login_required
def generate_content(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)

    has_access, redirect_resp = check_subject_access(
        request, subject, require_teacher=True,
    )
    if not has_access:
        return redirect_resp

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(
        start_date__lte=now, end_date__gte=now,
    ).first()
    terms = Term.objects.filter(semester=current_semester) if current_semester else Term.objects.none()

    model_keys = list(settings.AI_CONTENT_MODELS.keys())

    if request.method == "POST":
        form = GenerationRequestForm(request.POST, request.FILES, model_keys=model_keys)
        if form.is_valid():
            term_id = request.POST.get("term_id")
            term = get_object_or_404(Term, pk=term_id)

            gen_request = GenerationRequest.objects.create(
                subject=subject,
                term=term,
                requested_by=request.user,
                topic=form.cleaned_data["topic"],
                objectives=form.cleaned_data["objectives"],
                content_type=form.cleaned_data["content_type"],
                reference_file=form.cleaned_data.get("reference_file"),
                model_key=form.cleaned_data["model_key"],
            )
            generate_school_content.delay(gen_request.pk)

            messages.success(
                request,
                f"Content generation started for \"{gen_request.topic}\". "
                "New content will appear in your subject shortly.",
            )
            return redirect("material-list", id=subject_id)
    else:
        form = GenerationRequestForm(model_keys=model_keys)

    return render(
        request,
        "ai_content/generate.html",
        {
            "subject": subject,
            "form": form,
            "terms": terms,
        },
    )
