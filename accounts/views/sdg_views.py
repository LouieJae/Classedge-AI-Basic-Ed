"""[Classedge LMS] SDG (Sustainable Development Goal) management view —
operational admins curate the SDG catalog used by COIL and student tagging.
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render

from accounts.utils import (
    get_pagination_context,
    paginate_queryset,
    search_queryset,
)
from subject.models import SDG


@login_required
def sdg_list(request):
    """[Classedge LMS] Paginated, themed list of every SDG entry."""
    search_query = request.GET.get("search", "").strip()
    qs = SDG.objects.all().order_by("name")
    qs = search_queryset(qs, search_query, ["name", "description"])

    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)
    context = {
        "search_query": search_query,
        "title": "Sustainable Development Goals",
        "icon": "fa-globe",
        "search_placeholder": "Search SDGs by name or description...",
        "empty_icon": "fa-globe",
        "empty_label": "SDGs",
        "columns": [
            {"label": "#", "width": "60px", "type": "index"},
            {"label": "SDG", "type": "name", "name_attr": "name", "desc_attr": "description"},
            {"label": "Created", "type": "date", "attr": "created_at"},
        ],
    }
    context.update(get_pagination_context(page_obj, request))

    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "accounts/sdg/sdg_list.html", context)
