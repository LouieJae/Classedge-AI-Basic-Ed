from django.urls import path

from accounts.views.legal_admin_views import (
    legal_document_activate,
    legal_document_create,
    legal_document_delete,
    legal_document_edit,
    legal_document_list,
)
from accounts.views.legal_views import (
    accept_all_legal_documents,
    accept_legal_page,
    active_legal_documents,
    active_legal_document_by_type,
    my_legal_status,
)

urlpatterns = [
    path("api/legal-documents/active/", active_legal_documents, name="legal-documents-active"),
    path(
        "api/legal-documents/active/<str:doc_type>/",
        active_legal_document_by_type,
        name="legal-documents-active-by-type",
    ),
    path("api/me/legal-status/", my_legal_status, name="my-legal-status"),
    path(
        "api/legal-consents/accept-all/",
        accept_all_legal_documents,
        name="legal-consents-accept-all",
    ),
    path("accept-legal/", accept_legal_page, name="accept-legal"),

    # Staff-only legal document management (Django template UI)
    path("legal-documents/", legal_document_list, name="legal-document-list"),
    path("legal-documents/new/", legal_document_create, name="legal-document-create"),
    path("legal-documents/<int:pk>/edit/", legal_document_edit, name="legal-document-edit"),
    path("legal-documents/<int:pk>/delete/", legal_document_delete, name="legal-document-delete"),
    path("legal-documents/<int:pk>/activate/", legal_document_activate, name="legal-document-activate"),
]
