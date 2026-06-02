from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.models import LegalDocument, UserLegalConsent
from accounts.serializers.legal_serializers import LegalDocumentSerializer

DOC_TYPES = ["EULA", "PRIVACY", "NDA"]


@api_view(["GET"])
@permission_classes([AllowAny])
def active_legal_documents(request):
    docs = {d.doc_type: d for d in LegalDocument.objects.filter(is_active=True)}
    body = {}
    missing = []
    for doc_type in DOC_TYPES:
        doc = docs.get(doc_type)
        body[doc_type.lower()] = LegalDocumentSerializer(doc).data if doc else None
        if doc is None:
            missing.append(doc_type)
    if missing:
        body["missing"] = missing
    response = Response(body)
    response["Cache-Control"] = "public, max-age=300"
    return response


@api_view(["GET"])
@permission_classes([AllowAny])
def active_legal_document_by_type(request, doc_type: str):
    doc_type = doc_type.upper()
    if doc_type not in DOC_TYPES:
        return Response(status=404)
    doc = get_object_or_404(LegalDocument, doc_type=doc_type, is_active=True)
    return Response(LegalDocumentSerializer(doc).data)


@api_view(["GET"])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def my_legal_status(request):
    user = request.user
    active = LegalDocument.objects.filter(is_active=True)
    if not active.exists():
        return Response({
            "needs_acceptance": False,
            "pending": [],
            "current_versions": {
                "EULA": user.accepted_eula_version,
                "PRIVACY": user.accepted_privacy_version,
                "NDA": user.accepted_nda_version,
            },
        })

    accepted_doc_ids = set(
        UserLegalConsent.objects.filter(user=user).values_list("document_id", flat=True)
    )
    pending = [d.doc_type for d in active if d.id not in accepted_doc_ids]

    return Response({
        "needs_acceptance": bool(pending),
        "pending": pending,
        "current_versions": {
            "EULA": user.accepted_eula_version,
            "PRIVACY": user.accepted_privacy_version,
            "NDA": user.accepted_nda_version,
        },
    })


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


@api_view(["POST"])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def accept_all_legal_documents(request):
    user = request.user
    active = list(LegalDocument.objects.filter(is_active=True))
    if not active:
        return Response(
            {"error": "no_documents_to_accept"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    snapshot_field = {
        "EULA": "accepted_eula_version",
        "PRIVACY": "accepted_privacy_version",
        "NDA": "accepted_nda_version",
    }

    ip = _client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "") or None
    accepted_types = []
    changed_user_fields = []

    with transaction.atomic():
        for doc in active:
            UserLegalConsent.objects.get_or_create(
                user=user,
                document=doc,
                defaults={"ip_address": ip, "user_agent": ua},
            )
            accepted_types.append(doc.doc_type)

            field = snapshot_field.get(doc.doc_type)
            if field and getattr(user, field) != doc.version:
                setattr(user, field, doc.version)
                changed_user_fields.append(field)

        if user.legal_update_required:
            user.legal_update_required = False
            changed_user_fields.append("legal_update_required")

        if changed_user_fields:
            user.save(update_fields=changed_user_fields)

    return Response({"accepted": accepted_types}, status=status.HTTP_200_OK)


@login_required
def accept_legal_page(request):
    active = LegalDocument.objects.filter(is_active=True).order_by("doc_type")
    accepted_ids = set(
        UserLegalConsent.objects.filter(user=request.user).values_list("document_id", flat=True)
    )
    docs = [
        {
            "doc": d,
            "is_pending": d.id not in accepted_ids,
        }
        for d in active
    ]
    base_template = "student_base.html" if getattr(request.user, "is_student", False) else "base_operation.html"
    return render(
        request,
        "accounts/legal/accept.html",
        {"docs": docs, "base_template": base_template},
    )
