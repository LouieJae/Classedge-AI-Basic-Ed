from django.db import migrations
from django.utils import timezone


def migrate_legacy_consents(apps, schema_editor):
    """Convert legacy UserLegalConsent rows into LegalDocument + new-shape rows.

    Legacy schema: (user, eula_version, privacy_policy_version, is_accepted, consent_timestamp).
    New schema:   (user, document, accepted_at, ip_address, user_agent).
    For each legacy row, ensure LegalDocument(doc_type, version) placeholders exist
    for EULA and PRIVACY, then create UserLegalConsent rows pointing at them.
    """
    UserLegalConsent = apps.get_model("accounts", "UserLegalConsent")
    LegalDocument = apps.get_model("accounts", "LegalDocument")

    legacy_rows = list(UserLegalConsent.objects.all())
    if not legacy_rows:
        return

    doc_cache = {}

    def get_or_make_doc(doc_type, version):
        key = (doc_type, version)
        if key in doc_cache:
            return doc_cache[key]
        doc, _ = LegalDocument.objects.get_or_create(
            doc_type=doc_type,
            version=version,
            defaults={
                "title": f"{doc_type} v{version}",
                "content": "",
                "is_active": False,
            },
        )
        doc_cache[key] = doc
        return doc

    new_rows = []
    for row in legacy_rows:
        ts = row.consent_timestamp or timezone.now()
        for doc_type, version in (
            ("EULA", row.eula_version),
            ("PRIVACY", row.privacy_policy_version),
        ):
            if not version:
                continue
            doc = get_or_make_doc(doc_type, version)
            new_rows.append(
                UserLegalConsent(
                    user_id=row.user_id,
                    document=doc,
                    accepted_at=ts,
                )
            )

    UserLegalConsent.objects.all().delete()

    seen = set()
    deduped = []
    for r in new_rows:
        key = (r.user_id, r.document_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    UserLegalConsent.objects.bulk_create(deduped)


def noop_reverse(apps, schema_editor):
    """Reverse is destructive (legacy fields are gone in 0007). No-op."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_legaldocument_and_legal_update_required"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_consents, noop_reverse),
    ]
