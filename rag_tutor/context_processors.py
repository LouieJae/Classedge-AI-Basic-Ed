from django.conf import settings


def rag_tutor_flags(request):
    """Expose the tutor availability flag to templates so they can render the
    chat bubble only when both API keys are configured. Students may also be
    on pages that have no subject context (dashboards, etc.) — those uses are
    template-side: the include itself requires a subject_id."""
    return {
        "rag_tutor_available": getattr(settings, "RAG_TUTOR_AVAILABLE", False),
    }
