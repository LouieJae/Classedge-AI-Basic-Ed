import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings, Client

from activity.models.activity_model import Activity
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from received_central_content.tests.factories import (
    get_or_create_sdg, get_or_create_activity_type,
)
from subject.models.subject_model import Subject


def _auth_headers():
    return {"HTTP_AUTHORIZATION": "Bearer " + "t" * 40}


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


def _base_payload(target_subject_id):
    return {
        "central_id": 42,
        "central_version": 1,
        "target_subject_id": target_subject_id,
        "subject_name": "Algebra 1",
        "subject_descriptive_title": "Foundations of Algebra",
        "subject_short_name": "ALG1",
        "subject_description": "Central description",
        "subject_code": "ALG101",
        "subject_type": "Lec",
        "unit": 3,
        "target_grade_level": "Grade 7",
        "target_curriculum": "K-12",
        "target_sdgs": ["Quality Education"],
        "modules": [
            {
                "central_id": 101,
                "file_name": "Module 1",
                "description": "Intro",
                "order": 0,
                "url": "",
                "iframe_code": "",
            }
        ],
        "activities": [
            {
                "central_id": 201,
                "activity_name": "Quiz 1",
                "activity_instruction": "Answer all",
                "activity_type": "Quiz",
                "max_score": 100,
                "time_duration": 30,
                "passing_score": 75,
                "passing_score_type": "percentage",
                "max_retake": 2,
                "retake_method": "highest",
                "shuffle_questions": True,
                "is_graded": True,
                "related_module_central_ids": [101],
            }
        ],
    }


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class IngestHappyPathTests(TestCase):
    def setUp(self):
        get_or_create_sdg("Quality Education")
        get_or_create_activity_type("Quiz")
        self.target = _create_subject(
            subject_name="Math 101", subject_code="MATH101",
        )
        self.client = Client()

    def _payload(self, **overrides):
        p = _base_payload(self.target.pk)
        p.update(overrides)
        return p

    def test_no_token_returns_401(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
        )
        self.assertEqual(resp.status_code, 401)

    def test_first_push_creates_rows(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)
        subject = ReceivedCentralSubject.objects.get()
        self.assertEqual(subject.central_id, 42)
        self.assertEqual(subject.central_version, 1)
        self.assertEqual(subject.target_sdgs.count(), 1)
        activity = Activity.objects.get(central_source_id=42)
        self.assertEqual(activity.additional_modules.count(), 1)

    def test_response_shape(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth_headers(),
        )
        body = resp.json()
        self.assertIn("received_subject_id", body)
        self.assertEqual(body["central_version"], 1)
        self.assertIn("received_at", body)

    def test_repush_upserts_and_deletes_orphans(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth_headers(),
        )
        second = self._payload()
        second["central_version"] = 2
        second["subject_name"] = "Algebra 1 Updated"
        second["modules"] = []
        second["activities"][0]["related_module_central_ids"] = []
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(second)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        subject = ReceivedCentralSubject.objects.get()
        self.assertEqual(subject.central_version, 2)
        self.assertEqual(subject.subject_name, "Algebra 1 Updated")
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class IngestValidationTests(TestCase):
    def setUp(self):
        get_or_create_sdg("Quality Education")
        get_or_create_activity_type("Quiz")
        self.target = _create_subject(
            subject_name="Math 101", subject_code="MATH101",
        )
        self.client = Client()

    def _payload(self, **overrides):
        p = _base_payload(self.target.pk)
        p.update(overrides)
        return p

    def test_unresolved_sdg_returns_422(self):
        payload = self._payload(target_sdgs=["Not A Real SDG"])
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"], "unresolved_sdgs")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)

    def test_unresolved_activity_type_returns_422(self):
        payload = self._payload()
        payload["activities"][0]["activity_type"] = "Made Up"
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"], "unresolved_activity_types")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)

    def test_missing_file_part_returns_400(self):
        payload = self._payload()
        payload["modules"][0]["file_part"] = "module_0_file"
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "missing_file_part")

    def test_subject_photo_uploaded(self):
        payload = self._payload()
        payload["subject_photo_part"] = "subject_photo"
        image = SimpleUploadedFile(
            "photo.png", b"fake-png-bytes", content_type="image/png",
        )
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload), "subject_photo": image},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        s = ReceivedCentralSubject.objects.get()
        self.assertTrue(s.subject_photo.name)

    def test_module_file_uploaded(self):
        payload = self._payload()
        payload["modules"][0]["file_part"] = "module_0_file"
        pdf = SimpleUploadedFile(
            "m.pdf", b"fake-pdf-bytes", content_type="application/pdf",
        )
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload), "module_0_file": pdf},
            **_auth_headers(),
        )
        self.assertEqual(resp.status_code, 200)
        m = Module.objects.get(central_source_id=42)
        self.assertTrue(m.file.name)
