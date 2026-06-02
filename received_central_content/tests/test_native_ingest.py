import json

from django.db import connection
from django.test import TestCase, override_settings, Client

from activity.models.activity_model import Activity, ActivityType
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from subject.models.sdg_models import SDG
from subject.models.subject_model import Subject


def _auth():
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
        # Find which NOT-NULL columns (excluding id) actually exist in this DB
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


@override_settings(
    CENTRAL_INGEST_TOKEN="t" * 40,
    ROOT_URLCONF="lms.urls",
    ALLOWED_HOSTS=["*"],
)
class NativeIngestTests(TestCase):
    def setUp(self):
        self.target = _create_subject(
            subject_name="Math 101", subject_code="MATH101",
        )
        SDG.objects.get_or_create(name="Quality Education")
        ActivityType.objects.get_or_create(name="Quiz")
        self.client = Client()

    def _payload(self, **overrides):
        base = {
            "central_id": 42,
            "central_version": 1,
            "target_subject_id": self.target.pk,
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
        base.update(overrides)
        return base

    def test_push_creates_native_module(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 200)
        mod = Module.objects.get(subject=self.target, central_source_id=42)
        self.assertEqual(mod.file_name, "Module 1")
        self.assertEqual(mod.description, "Intro")

    def test_push_creates_native_activity(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 200)
        act = Activity.objects.get(subject=self.target, central_source_id=42)
        self.assertEqual(act.activity_name, "Quiz 1")
        self.assertEqual(act.max_retake, 2)
        self.assertTrue(act.shuffle_questions)

    def test_push_links_activity_to_module_via_m2m(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        act = Activity.objects.get(subject=self.target, central_source_id=42)
        mod = Module.objects.get(subject=self.target, central_source_id=42)
        self.assertIn(mod, act.additional_modules.all())

    def test_push_creates_received_subject_for_version_tracking(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        rs = ReceivedCentralSubject.objects.get(central_id=42)
        self.assertEqual(rs.central_version, 1)
        self.assertEqual(rs.subject_name, "Algebra 1")

    def test_repush_clears_old_central_rows_creates_new(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        old_mod_pk = Module.objects.get(central_source_id=42).pk

        second = self._payload(central_version=2)
        second["modules"][0]["file_name"] = "Module 1 v2"
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(second)},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        new_mod = Module.objects.get(central_source_id=42)
        self.assertNotEqual(new_mod.pk, old_mod_pk)
        self.assertEqual(new_mod.file_name, "Module 1 v2")

    def test_repush_preserves_school_created_content(self):
        Module.objects.create(
            subject=self.target, file_name="School Lesson", order=0,
        )
        Activity.objects.create(
            subject=self.target,
            activity_name="School Quiz",
            activity_type=ActivityType.objects.get(name="Quiz"),
        )
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(
            Module.objects.filter(subject=self.target, central_source_id__isnull=True).count(), 1,
        )
        self.assertEqual(
            Activity.objects.filter(subject=self.target, central_source_id__isnull=True).count(), 1,
        )
        school_mod = Module.objects.get(central_source_id__isnull=True)
        self.assertEqual(school_mod.file_name, "School Lesson")

    def test_missing_target_subject_id_returns_400(self):
        payload = self._payload()
        del payload["target_subject_id"]
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(payload)},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"], "missing_target_subject_id")

    def test_invalid_target_subject_id_returns_404(self):
        resp = self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload(target_subject_id=99999))},
            **_auth(),
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "target_subject_not_found")

    def test_delete_clears_native_rows(self):
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 1)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 1)

        resp = self.client.delete("/api/central/ingest/42/", **_auth())
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Module.objects.filter(central_source_id=42).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=42).count(), 0)

    def test_delete_preserves_school_created_content(self):
        Module.objects.create(
            subject=self.target, file_name="School Lesson", order=0,
        )
        self.client.post(
            "/api/central/ingest/",
            data={"payload": json.dumps(self._payload())},
            **_auth(),
        )
        self.client.delete("/api/central/ingest/42/", **_auth())
        self.assertEqual(
            Module.objects.filter(central_source_id__isnull=True).count(), 1,
        )
