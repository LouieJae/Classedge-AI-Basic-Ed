from rest_framework import serializers

from accounts.models import LegalDocument, UserLegalConsent


class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = [
            "id",
            "doc_type",
            "version",
            "title",
            "content",
            "effective_date",
        ]
        read_only_fields = fields


class UserLegalConsentSerializer(serializers.ModelSerializer):
    doc_type = serializers.CharField(source="document.doc_type", read_only=True)
    version = serializers.CharField(source="document.version", read_only=True)
    title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = UserLegalConsent
        fields = [
            "id",
            "user",
            "document",
            "doc_type",
            "version",
            "title",
            "accepted_at",
            "ip_address",
            "user_agent",
        ]
        read_only_fields = fields
