# central_content/tests/test_models.py
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase

from central_content.models import AuditLogEntry, CentralStaff


class CentralStaffModelTests(TestCase):
    def test_create_editor(self):
        staff = CentralStaff.objects.create_user(
            email="editor@example.com",
            full_name="Edna Editor",
            password="testpass123",
            role=CentralStaff.Role.EDITOR,
        )
        self.assertEqual(staff.role, "editor")
        self.assertTrue(staff.is_active)
        self.assertTrue(staff.check_password("testpass123"))

    def test_email_unique(self):
        CentralStaff.objects.create_user(
            email="dup@example.com",
            full_name="A",
            password="x",
            role=CentralStaff.Role.EDITOR,
        )
        with self.assertRaises(IntegrityError):
            CentralStaff.objects.create_user(
                email="dup@example.com",
                full_name="B",
                password="y",
                role=CentralStaff.Role.EDITOR,
            )

    def test_role_choices_enforced(self):
        staff = CentralStaff.objects.create_user(
            email="pub@example.com",
            full_name="Paula Publisher",
            password="x",
            role=CentralStaff.Role.PUBLISHER,
        )
        staff.role = "superking"
        with self.assertRaises(Exception):
            staff.full_clean()

    def test_str(self):
        staff = CentralStaff.objects.create_user(
            email="a@b.com", full_name="A B", password="x",
            role=CentralStaff.Role.REVIEWER,
        )
        self.assertIn("a@b.com", str(staff))


class AuditLogEntryModelTests(TestCase):
    def setUp(self):
        self.staff = CentralStaff.objects.create_user(
            email="actor@example.com", full_name="Actor", password="x",
            role=CentralStaff.Role.REVIEWER,
        )

    def test_create_entry(self):
        ct = ContentType.objects.get_for_model(CentralStaff)
        entry = AuditLogEntry.objects.create(
            content_type=ct,
            object_id=self.staff.id,
            from_state="draft",
            to_state="in_review",
            actor=self.staff,
            notes="submitted for review",
        )
        self.assertEqual(entry.from_state, "draft")
        self.assertEqual(entry.to_state, "in_review")
        self.assertIsNotNone(entry.created_at)

    def test_actor_protect(self):
        """Deleting a staff user with audit history should be blocked."""
        from django.db.models import ProtectedError
        ct = ContentType.objects.get_for_model(CentralStaff)
        AuditLogEntry.objects.create(
            content_type=ct, object_id=1,
            from_state="draft", to_state="in_review",
            actor=self.staff,
        )
        with self.assertRaises(ProtectedError):
            self.staff.delete()


from central_content.models import CentralSubject


class CentralSubjectModelTests(TestCase):
    def setUp(self):
        self.creator = CentralStaff.objects.create_user(
            email="creator@example.com", full_name="Creator", password="x",
            role=CentralStaff.Role.EDITOR,
        )

    def test_create_draft(self):
        subj = CentralSubject.objects.create(
            subject_name="Grade 7 Mathematics",
            target_grade_level="Grade 7",
            target_curriculum="K-12 DepEd Philippines",
            created_by=self.creator,
        )
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.version, 1)
        self.assertIsNotNone(subj.created_at)
        self.assertIn("Grade 7", str(subj))

    def test_created_by_protected(self):
        from django.db.models import ProtectedError
        CentralSubject.objects.create(
            subject_name="X", created_by=self.creator,
        )
        with self.assertRaises(ProtectedError):
            self.creator.delete()


from central_content.models import CentralModule


class CentralModuleModelTests(TestCase):
    def setUp(self):
        self.creator = CentralStaff.objects.create_user(
            email="c@example.com", full_name="C", password="x",
            role=CentralStaff.Role.EDITOR,
        )
        self.subject = CentralSubject.objects.create(
            subject_name="Grade 7 Math", created_by=self.creator,
        )

    def test_create_module(self):
        m = CentralModule.objects.create(
            central_subject=self.subject,
            file_name="Lesson 1: Introduction",
            description="Intro to integers",
            order=0,
            created_by=self.creator,
        )
        self.assertEqual(m.state, "draft")
        self.assertEqual(m.central_subject, self.subject)

    def test_ordering_by_order(self):
        for i in range(3):
            CentralModule.objects.create(
                central_subject=self.subject,
                file_name=f"L{i}", order=2 - i, created_by=self.creator,
            )
        ordered = list(self.subject.modules.all().values_list("order", flat=True))
        self.assertEqual(ordered, [0, 1, 2])

    def test_cascade_on_subject_delete(self):
        CentralModule.objects.create(
            central_subject=self.subject, file_name="L1", created_by=self.creator,
        )
        self.subject.delete()
        self.assertEqual(CentralModule.objects.count(), 0)


from central_content.models import CentralActivity
from activity.models.activity_model import ActivityType


class CentralActivityModelTests(TestCase):
    def setUp(self):
        self.creator = CentralStaff.objects.create_user(
            email="c@example.com", full_name="C", password="x",
            role=CentralStaff.Role.EDITOR,
        )
        self.subject = CentralSubject.objects.create(
            subject_name="S", created_by=self.creator,
        )
        self.atype, _ = ActivityType.objects.get_or_create(name="Quiz")

    def test_create_activity(self):
        act = CentralActivity.objects.create(
            central_subject=self.subject,
            activity_name="Unit 1 Quiz",
            activity_type=self.atype,
            max_score=50,
            created_by=self.creator,
        )
        self.assertEqual(act.state, "draft")
        self.assertEqual(act.passing_score_type, "percentage")
        self.assertEqual(act.retake_method, "highest")

    def test_related_modules_m2m(self):
        m = CentralModule.objects.create(
            central_subject=self.subject, file_name="L1", created_by=self.creator,
        )
        act = CentralActivity.objects.create(
            central_subject=self.subject, activity_name="Q",
            activity_type=self.atype, created_by=self.creator,
        )
        act.related_modules.add(m)
        self.assertIn(m, act.related_modules.all())
