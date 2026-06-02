from django.http import JsonResponse

ALLOWLIST_PREFIXES = (
    "/accept-legal/",
    "/api/me/legal-status/",
    "/api/legal-consents/accept-all/",
    "/api/legal-documents/active/",
    "/api/auth/logout/",
    "/Classify/Login/",
    "/admin/",
    "/static/",
    "/media/",
)


class LegalConsentRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "legal_update_required", False)
            and not self._is_allowlisted(request.path)
        ):
            pending = self._pending_types(user)
            # Self-heal: if the flag is on but no docs are actually pending
            # (e.g. no active LegalDocuments exist, or all were accepted under
            # a stale flag), clear it and let the request through instead of
            # 409-locking the user forever.
            if not pending:
                user.legal_update_required = False
                user.save(update_fields=["legal_update_required"])
                return self.get_response(request)
            if self._wants_json(request):
                return JsonResponse(
                    {
                        "error": "legal_update_required",
                        "pending": pending,
                    },
                    status=409,
                )
            # HTML requests fall through; the consent modal is rendered inline
            # by the base templates via accounts.context_processors.legal_modal_context.
        return self.get_response(request)

    @staticmethod
    def _is_allowlisted(path: str) -> bool:
        return any(path.startswith(prefix) for prefix in ALLOWLIST_PREFIXES)

    @staticmethod
    def _wants_json(request) -> bool:
        if request.path.startswith("/api/"):
            return True
        return "application/json" in request.META.get("HTTP_ACCEPT", "")

    @staticmethod
    def _pending_types(user):
        from accounts.models import LegalDocument, UserLegalConsent

        active_ids = set(
            LegalDocument.objects.filter(is_active=True).values_list("id", flat=True)
        )
        accepted_ids = set(
            UserLegalConsent.objects.filter(user=user).values_list("document_id", flat=True)
        )
        missing_ids = active_ids - accepted_ids
        return list(
            LegalDocument.objects.filter(id__in=missing_ids).values_list("doc_type", flat=True)
        )
