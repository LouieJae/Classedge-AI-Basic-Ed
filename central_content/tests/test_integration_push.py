from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings, Client as DjangoClient

from activity.models.activity_model import Activity, ActivityType
from central_content.push import push_subject_to_school, delete_subject_from_school
from central_content.models import PushJob
from central_content.tests.factories import (
    make_binding, make_subject, make_module, make_activity,
    make_publisher, make_school,
)
from module.models.module import Module
from received_central_content.models import ReceivedCentralSubject
from subject.models.sdg_models import SDG
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


class _FakeResponse:
    def __init__(self, status_code, text="", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json = json_data or {}

    def json(self):
        return self._json


def _dispatch_to_school_view(method):
    from django.test.utils import override_settings as _os

    def fake(url, **kwargs):
        parts = url.split("//", 1)[1].split("/", 1)
        path = "/" + parts[1] if len(parts) > 1 else "/"
        headers = {}
        for k, v in (kwargs.get("headers") or {}).items():
            headers["HTTP_" + k.upper().replace("-", "_")] = v
        with _os(ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"]):
            django_client = DjangoClient()
            if method == "post":
                data = dict(kwargs.get("data") or {})
                for k, (name, fh) in (kwargs.get("files") or {}).items():
                    data[k] = fh
                resp = django_client.post(path, data=data, **headers)
            else:
                resp = django_client.delete(path, **headers)
        ct = resp.get("Content-Type", "")
        text = resp.content.decode() if resp.content else ""
        json_data = {}
        if ct.startswith("application/json") and resp.content:
            try:
                json_data = resp.json()
            except Exception:
                pass
        return _FakeResponse(resp.status_code, text=text, json_data=json_data)

    return fake


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40)
class IntegrationPushTests(TestCase):
    def test_full_loop_push_then_delete(self):
        SDG.objects.get_or_create(name="Quality Education")
        ActivityType.objects.get_or_create(name="Quiz")

        # Create native school Subject for target_subject_id
        native_subject = _create_subject(
            subject_name="Math 101", subject_code="MATH101",
        )

        subject = make_subject(
            subject_name="Algebra 1", version=1, subject_code="ALG101",
        )
        subject.target_sdgs.add(SDG.objects.get(name="Quality Education"))
        module = make_module(central_subject=subject, file_name="Mod 1")
        activity = make_activity(central_subject=subject)
        activity.related_modules.add(module)

        school = make_school(
            base_url="http://testserver",
            api_token="t" * 40,
        )
        binding = make_binding(
            central_subject=subject,
            target_school=school,
            school_subject_id=native_subject.pk,
        )

        with patch("central_content.push.requests.post", _dispatch_to_school_view("post")):
            job = push_subject_to_school(binding, triggered_by=make_publisher())

        self.assertEqual(job.status, "success", f"Push failed: {job.response_body} {job.error_message}")

        # ReceivedCentralSubject still used for version tracking
        self.assertEqual(ReceivedCentralSubject.objects.count(), 1)
        received = ReceivedCentralSubject.objects.get()
        self.assertEqual(received.central_id, subject.pk)
        self.assertEqual(received.subject_name, "Algebra 1")

        # Native Module/Activity rows should exist
        central_id = subject.pk
        self.assertEqual(Module.objects.filter(central_source_id=central_id).count(), 1)
        self.assertEqual(Activity.objects.filter(central_source_id=central_id).count(), 1)

        with patch("central_content.push.requests.delete", _dispatch_to_school_view("delete")):
            del_job = delete_subject_from_school(binding, triggered_by=make_publisher())
        self.assertEqual(del_job.status, "success")
        self.assertEqual(ReceivedCentralSubject.objects.count(), 0)
        # Native rows cleaned up on delete
        self.assertEqual(Module.objects.filter(central_source_id=central_id).count(), 0)
        self.assertEqual(Activity.objects.filter(central_source_id=central_id).count(), 0)
