from django.db import IntegrityError
from django.test import TestCase

from received_central_content.models import (
    ReceivedCentralSubject, ReceivedCentralModule, ReceivedCentralActivity,
)
from received_central_content.tests.factories import (
    make_received_subject, make_received_module, make_received_activity,
    get_or_create_sdg,
)


class ReceivedModelsTests(TestCase):
    def test_create_received_subject(self):
        s = make_received_subject()
        self.assertEqual(s.central_id, 42)
        self.assertEqual(s.central_version, 1)
        self.assertIsNotNone(s.received_at)
        self.assertIsNotNone(s.last_received_at)

    def test_central_id_unique(self):
        make_received_subject(central_id=42)
        with self.assertRaises(IntegrityError):
            make_received_subject(central_id=42)

    def test_m2m_sdgs(self):
        s = make_received_subject()
        s.target_sdgs.add(get_or_create_sdg("Quality Education"))
        self.assertEqual(s.target_sdgs.count(), 1)

    def test_module_fk_cascade(self):
        m = make_received_module()
        subject_pk = m.received_subject.pk
        m.received_subject.delete()
        self.assertFalse(
            ReceivedCentralModule.objects.filter(received_subject_id=subject_pk).exists()
        )

    def test_activity_fk_cascade(self):
        a = make_received_activity()
        a.received_subject.delete()
        self.assertEqual(ReceivedCentralActivity.objects.count(), 0)

    def test_activity_related_modules(self):
        subject = make_received_subject()
        m = make_received_module(received_subject=subject)
        a = make_received_activity(received_subject=subject)
        a.related_modules.add(m)
        self.assertEqual(a.related_modules.count(), 1)
