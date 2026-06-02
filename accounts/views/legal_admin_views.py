from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.forms import LegalDocumentForm
from accounts.models import LegalDocument


@staff_member_required
def legal_document_list(request):
    docs = LegalDocument.objects.all().order_by("doc_type", "-effective_date")
    return render(request, "accounts/legal/admin/list.html", {"docs": docs})


@staff_member_required
def legal_document_create(request):
    if request.method == "POST":
        form = LegalDocumentForm(request.POST)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.created_by = request.user
            doc.save()
            messages.success(request, f"Created {doc.doc_type} v{doc.version}.")
            return redirect("legal-document-list")
    else:
        form = LegalDocumentForm()
    return render(
        request,
        "accounts/legal/admin/form.html",
        {"form": form, "mode": "create"},
    )


@staff_member_required
def legal_document_edit(request, pk):
    doc = get_object_or_404(LegalDocument, pk=pk)
    if request.method == "POST":
        form = LegalDocumentForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated {doc.doc_type} v{doc.version}.")
            return redirect("legal-document-list")
    else:
        form = LegalDocumentForm(instance=doc)
    return render(
        request,
        "accounts/legal/admin/form.html",
        {"form": form, "mode": "edit", "doc": doc},
    )


@staff_member_required
def legal_document_delete(request, pk):
    doc = get_object_or_404(LegalDocument, pk=pk)
    if request.method == "POST":
        label = f"{doc.doc_type} v{doc.version}"
        doc.delete()
        messages.success(request, f"Deleted {label}.")
        return redirect("legal-document-list")
    return render(
        request,
        "accounts/legal/admin/confirm_delete.html",
        {"doc": doc},
    )


@staff_member_required
@require_POST
def legal_document_activate(request, pk):
    doc = get_object_or_404(LegalDocument, pk=pk)
    doc.is_active = True
    doc.save()
    messages.success(
        request,
        f"Activated {doc.doc_type} v{doc.version}. Users will be prompted to re-consent.",
    )
    return redirect("legal-document-list")
