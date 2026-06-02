from django.db import connection
from django.test import TestCase, override_settings, Client

from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from received_central_content.tests.factories import (
    make_received_subject, make_received_module, make_received_activity,
)
from subject.models.subject_model import Subject


def _create_subject(subject_name="", subject_code=""):
    """Create a Subject via raw SQL, dynamically handling NOT-NULL columns the Django model may not declare."""
    _DEFAULTS = {
        "subject_name": subject_name,
        "subject_code": subject_code,
        "allow_substitute_teacher": False,
        "unit": 3,
        "is_coil": False,
        "is_hali": False,
        "is_cte": False,
        "number_of_enrollees": 0,
        "status": "Available",
        "self_attendance_enabled": False,
        "generation_status": "",
        "ide_languages": "[]",
        "supports_ide": False,
        "total_views": 0,
        "is_hidden": False,
        "is_archived": False,
        "is_deleted": False,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'subject_subject' AND is_nullable = 'NO' "
            "AND column_name != 'id' AND column_default IS NULL"
        )
        needed = {row[0]: row[1] for row in cursor.fetchall()}

        cols = []
        vals = []
        params = []
        for col, dtype in needed.items():
            cols.append(col)
            if col in _DEFAULTS:
                if dtype == "jsonb":
                    vals.append("%s::jsonb")
                else:
                    vals.append("%s")
                params.append(_DEFAULTS[col])
            elif dtype in ("boolean",):
                vals.append("%s")
                params.append(False)
            elif dtype in ("integer", "bigint", "smallint"):
                vals.append("%s")
                params.append(0)
            elif dtype == "jsonb":
                vals.append("%s::jsonb")
                params.append("[]")
            else:
                vals.append("%s")
                params.append("")

        sql = (
            f"INSERT INTO subject_subject ({', '.join(cols)}) "
            f"VALUES ({', '.join(vals)}) RETURNING id"
        )
        cursor.execute(sql, params)
        pk = cursor.fetchone()[0]
    return Subject.objects.get(pk=pk)


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class IngestDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_no_token_returns_401(self):
        make_received_subject(central_id=42)
        resp = self.client.delete("/api/central/ingest/42/")
        self.assertEqual(resp.status_code, 401)

    def test_delete_cascades(self):
        subject = make_received_subject(central_id=42)
        make_received_module(received_subject=subject)
        make_received_activity(received_subject=subject)
        resp = self.client.delete(
            "/api/central/ingest/42/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)

    def test_delete_unknown_returns_404(self):
        resp = self.client.delete(
            "/api/central/ingest/999/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_cleans_up_native_rows(self):
        """Verify DELETE removes native Module/Activity rows with matching central_source_id."""
        target = _create_subject(subject_name="Math 101", subject_code="MATH101")
        ActivityType.objects.get_or_create(name="Quiz")
        atype = ActivityType.objects.get(name="Quiz")

        # Create native rows as if they were ingested from central
        Module.objects.create(
            subject=target, file_name="Central Mod", order=0, central_source_id=42,
        )
        Activity.objects.create(
            subject=target, activity_name="Central Quiz",
            activity_type=atype, central_source_id=42,
        )
        # Also create the ReceivedCentralSubject (version tracking)
        make_received_subject(central_id=42)

        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)

        resp = self.client.delete(
            "/api/central/ingest/42/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)
