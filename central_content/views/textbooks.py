from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from central_content.forms import TextbookUploadForm
from central_content.models import CentralSubject, ParsedTextbook
from central_content.permissions import central_role_required
from central_content.tasks import parse_textbook_toc


@central_role_required("publisher", "editor")
def textbook_upload(request, subject_id: int):
    subject = get_object_or_404(CentralSubject, pk=subject_id)

    if request.method == "POST":
        form = TextbookUploadForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.cleaned_data["title"] or request.FILES["file"].name.replace(".pdf", "")
            textbook = ParsedTextbook.objects.create(
                central_subject=subject,
                title=title,
                original_file=form.cleaned_data["file"],
                uploaded_by=request.user,
                status=ParsedTextbook.Status.UPLOADING,
            )
            parse_textbook_toc.delay(textbook.pk)
            return redirect(f"/subjects/{subject_id}/textbooks/{textbook.pk}/")
    else:
        form = TextbookUploadForm()

    return render(
        request,
        "central_content/textbooks/upload.html",
        {"subject": subject, "form": form},
    )


@central_role_required("publisher", "editor", "reviewer")
def textbook_detail(request, subject_id: int, textbook_id: int):
    textbook = get_object_or_404(
        ParsedTextbook.objects.select_related("central_subject", "uploaded_by"),
        pk=textbook_id,
        central_subject_id=subject_id,
    )
    chapters = textbook.chapters.all()
    plans = textbook.plans.select_related("generated_by").all()

    return render(
        request,
        "central_content/textbooks/detail.html",
        {
            "textbook": textbook,
            "subject": textbook.central_subject,
            "chapters": chapters,
            "plans": plans,
        },
    )


@central_role_required("publisher", "editor", "reviewer")
def textbook_status_badge(request, subject_id: int, textbook_id: int):
    textbook = get_object_or_404(
        ParsedTextbook, pk=textbook_id, central_subject_id=subject_id,
    )
    return render(
        request,
        "central_content/textbooks/status_badge.html",
        {"textbook": textbook},
    )
