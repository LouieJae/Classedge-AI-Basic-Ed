from django.test import TestCase

from central_content.push import build_push_payload
from central_content.tests.factories import (
    make_subject, make_module, make_activity,
)
from subject.models.sdg_models import SDG


class BuildPushPayloadTests(TestCase):
    def test_basic_subject(self):
        subject = make_subject(
            subject_name="Algebra 1",
            version=3,
            subject_code="ALG101",
            unit=3,
        )
        payload, files = build_push_payload(subject)
        self.assertEqual(payload["central_id"], subject.pk)
        self.assertEqual(payload["central_version"], 3)
        self.assertEqual(payload["subject_name"], "Algebra 1")
        self.assertEqual(payload["subject_code"], "ALG101")
        self.assertEqual(payload["modules"], [])
        self.assertEqual(payload["activities"], [])
        self.assertEqual(files, {})

    def test_stripped_fields_not_in_payload(self):
        subject = make_subject()
        payload, _ = build_push_payload(subject)
        for forbidden in [
            "id", "state", "created_by", "submitted_by", "reviewed_by",
            "review_notes", "source_notes", "created_at", "updated_at",
        ]:
            self.assertNotIn(
                forbidden, payload,
                f"Field {forbidden!r} must not appear in push payload",
            )

    def test_sdgs_emitted_as_names(self):
        subject = make_subject()
        sdg, _ = SDG.objects.get_or_create(name="Quality Education")
        subject.target_sdgs.add(sdg)
        payload, _ = build_push_payload(subject)
        self.assertEqual(payload["target_sdgs"], ["Quality Education"])

    def test_modules_included(self):
        subject = make_subject()
        make_module(central_subject=subject, file_name="Mod 1", order=0)
        payload, _ = build_push_payload(subject)
        self.assertEqual(len(payload["modules"]), 1)
        m = payload["modules"][0]
        self.assertEqual(m["file_name"], "Mod 1")
        self.assertEqual(m["order"], 0)
        self.assertIn("central_id", m)

    def test_activity_related_modules_as_central_ids(self):
        subject = make_subject()
        module = make_module(central_subject=subject)
        activity = make_activity(central_subject=subject)
        activity.related_modules.add(module)
        payload, _ = build_push_payload(subject)
        a = payload["activities"][0]
        self.assertEqual(a["related_module_central_ids"], [module.pk])
        self.assertEqual(a["activity_type"], activity.activity_type.name)
