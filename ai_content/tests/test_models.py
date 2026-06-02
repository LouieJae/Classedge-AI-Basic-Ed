from django.test import TestCase

from ai_content.models import GenerationRequest
from course.models.term_model import Term
from course.models.semester_model import Semester
from accounts.models import CustomUser
from subject.models.subject_model import Subject
from datetime import date
from django.db import connection


def _create_test_user(username="teacher1", role_name="teacher"):
    from roles.models import Role
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass",
    )
    from accounts.models import Profile
    Profile.objects.filter(user=user).update(role=role)
    return user


def _create_subject(subject_name="Math 101"):
    """Create a Subject via raw SQL for compatibility with NOT-NULL orphan columns."""
    _DEFAULTS = {
        "subject_name": subject_name,
        "subject_code": "MATH101",
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
            val = _DEFAULTS.get(col)
            if val is None:
                if "int" in dtype:
                    val = 0
                elif "bool" in dtype:
                    val = False
                else:
                    val = ""
            cols.append(f'"{col}"')
            vals.append("%s")
            params.append(val)

        sql = f'INSERT INTO subject_subject ({", ".join(cols)}) VALUES ({", ".join(vals)}) RETURNING id, subject_name'
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return Subject.objects.get(pk=row[0])


class GenerationRequestModelTests(TestCase):
    def setUp(self):
        self.user = _create_test_user()
        self.subject = _create_subject()
        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )

    def test_create_request(self):
        req = GenerationRequest.objects.create(
            subject=self.subject,
            term=self.term,
            requested_by=self.user,
            topic="Algebra Basics",
            objectives="Students will learn variables and expressions.",
            content_type=GenerationRequest.ContentType.BOTH,
            model_key="haiku",
        )
        self.assertEqual(req.status, GenerationRequest.Status.PENDING)
        self.assertIsNone(req.generated_module_id)
        self.assertIsNone(req.generated_activity_id)
        self.assertEqual(req.reference_text, "")

    def test_cascade_delete_with_subject(self):
        GenerationRequest.objects.create(
            subject=self.subject,
            term=self.term,
            requested_by=self.user,
            topic="Test",
            objectives="Test",
            model_key="haiku",
        )
        self.assertEqual(GenerationRequest.objects.count(), 1)
        self.subject.delete()
        self.assertEqual(GenerationRequest.objects.count(), 0)

    def test_status_transitions(self):
        req = GenerationRequest.objects.create(
            subject=self.subject,
            term=self.term,
            requested_by=self.user,
            topic="Test",
            objectives="Test",
            model_key="haiku",
        )
        for status_val in ["pending", "running", "complete", "failed"]:
            req.status = status_val
            req.save(update_fields=["status"])
            req.refresh_from_db()
            self.assertEqual(req.status, status_val)

    def test_content_type_choices(self):
        for ct in ["module", "quiz", "both"]:
            req = GenerationRequest.objects.create(
                subject=self.subject,
                term=self.term,
                requested_by=self.user,
                topic=f"Test {ct}",
                objectives="Test",
                content_type=ct,
                model_key="haiku",
            )
            self.assertEqual(req.content_type, ct)
