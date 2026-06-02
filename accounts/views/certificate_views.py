from accounts.models import Certificate
from accounts.forms import CertificateForm
from accounts.utils import get_pagination_context, paginate_queryset, search_queryset
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages


@login_required
def certificate_list(request):
    """[Classedge LMS] Themed certificate list using the reusable list-table shell."""
    search_query = request.GET.get("search", "").strip()
    qs = Certificate.objects.all().order_by("-issued_date", "title")
    qs = search_queryset(qs, search_query, ["title"])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        "search_query": search_query,
        "form": CertificateForm(),
        "title": "Certificate Library",
        "icon": "fa-certificate",
        "search_placeholder": "Search certificates by title...",
        "empty_icon": "fa-certificate",
        "empty_label": "certificates",
        "columns": [
            {"label": "#", "width": "60px", "type": "index"},
            {"label": "Certificate", "type": "name", "name_attr": "title"},
            {"label": "Issued", "type": "date", "attr": "issued_date"},
            {"label": "Featured", "type": "status", "attr": "is_featured",
             "map": {True: "success", False: "muted"}},
            {"label": "Action", "align": "right", "type": "actions", "items": [
                {"label": "Update", "icon": "fa-edit",
                 "onclick_template": "openCertEditModal({id})"},
                {"divider": True},
                {"label": "Delete", "icon": "fa-trash", "danger": True,
                 "form_post": True, "url_name": "certificate-delete", "url_arg_attr": "id",
                 "confirm": "Delete this certificate? This cannot be undone."},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "accounts/certificate/certificate.html", context)


@login_required
def create_certificate(request):
    if request.method == "POST":
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Certificate created.")
            return redirect("certificate-list")
        messages.error(request, "There were errors creating the certificate. Please review the form.")
        return redirect("certificate-list")
    return redirect("certificate-list")


@login_required
def update_certificate(request, id):
    certificate = get_object_or_404(Certificate, id=id)
    if request.method == "POST":
        form = CertificateForm(request.POST, request.FILES, instance=certificate)
        if form.is_valid():
            form.save()
            messages.success(request, "Certificate updated.")
            return redirect("certificate-list")
        messages.error(request, "There were errors updating the certificate. Please review the form.")
        return redirect("certificate-list")
    form = CertificateForm(instance=certificate)
    return render(request, "accounts/certificate/_certificate_form.html",
                  {"form": form, "certificate": certificate})


@login_required
def delete_certificate(request, id):
    certificate = get_object_or_404(Certificate, id=id)
    certificate.delete()
    messages.success(request, "Certificate deleted.")
    return redirect("certificate-list")
