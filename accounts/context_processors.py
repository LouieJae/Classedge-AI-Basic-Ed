from accounts.models import SchoolName
import os
import time
from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError


def school_context(request):
    try:
        school = SchoolName.objects.first()
    except (ProgrammingError, OperationalError):
        # Table might not exist yet (e.g., before initial migrations). Provide safe defaults.
        school = None
    # SCHOOL_BRAND_COLOR drives the --brand-primary token across every page.
    # Falls back to forest (#1b4332) when no row exists OR the brand_color
    # field hasn't been migrated yet (older deployments still on 0004).
    brand_color = getattr(school, "brand_color", None) if school else None
    return {
        "SCHOOL_NAME": school.name if school else "",
        "SCHOOL_SHORT_NAME": school.short_name if school and school.short_name else "",
        "SCHOOL_BRAND_COLOR": brand_color or "#1b4332",
    }

def logo_update_time(request):
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'HCCCI-logo.png')
    if os.path.exists(logo_path):
        return {"logo_update_time": int(os.path.getmtime(logo_path))}
    return {"logo_update_time": int(time.time())}


def department_context(request):
    """[Classedge LMS] Provide the logged-in user's first headed department (if any)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    head = user.headed_departments.first() if hasattr(user, "headed_departments") else None
    return {"headed_department": head}


def quick_action_subjects(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"cl_quick_subjects": []}
    try:
        from subject.models import Subject
        from django.db.models import Q
        qs = (
            Subject.objects.filter(
                Q(assign_teacher=user) | Q(collaborators=user)
            )
            .distinct()
            .order_by("subject_name")
        )
    except (ProgrammingError, OperationalError, ImportError):
        return {"cl_quick_subjects": []}
    return {"cl_quick_subjects": qs}


def legal_modal_context(request):
    """Inject pending legal documents so base templates can render the consent modal inline."""
    empty = {"legal_modal_open": False, "legal_modal_docs": []}
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return empty
    if not getattr(user, "legal_update_required", False):
        return empty
    try:
        from accounts.models import LegalDocument, UserLegalConsent
        active = LegalDocument.objects.filter(is_active=True).order_by("doc_type")
        if not active.exists():
            return empty
        accepted_ids = set(
            UserLegalConsent.objects.filter(user=user).values_list("document_id", flat=True)
        )
        docs = [{"doc": d, "is_pending": d.id not in accepted_ids} for d in active]
        has_pending = any(entry["is_pending"] for entry in docs)
        is_first_time = not accepted_ids
        return {
            "legal_modal_open": has_pending,
            "legal_modal_docs": docs,
            "legal_modal_is_first_time": is_first_time,
        }
    except (ProgrammingError, OperationalError):
        return empty
