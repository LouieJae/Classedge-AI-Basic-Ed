"""[Classedge LMS] Gating test for module/views/crud_views.py:deleteModule.

Phase 2 dropped the legacy role decorator that was stacked above the
existing permission_required on this view. The perm decorator alone
must continue to gate correctly.
"""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from gradebookcomponent.tests.helpers import make_subject
from module.models.module import Module
from roles.tests.helpers import make_it_admin, make_user_with_role


class ModuleDeleteGatingTests(TestCase):

    def setUp(self):
        self.teacher = make_user_with_role("phase2_m_teacher", "Teacher")
        # Teacher must also have module.delete_module — grant it directly
        # since PHASE2_GRANTS doesn't include this perm (it's pre-existing
        # on Teacher in production).
        ct = ContentType.objects.get(app_label="module", model="module")
        perm = Permission.objects.get(content_type=ct, codename="delete_module")
        teacher_role = self.teacher.profile.role
        teacher_role.permissions.add(perm)

        self.student = make_user_with_role("phase2_m_student", "Student")
        self.it_admin = make_it_admin(username="phase2_m_itadmin")
        self.subject = make_subject(self.teacher, name="Music 101")
        self.module = Module.objects.create(
            file_name="Lesson 1", subject=self.subject,
        )
        self.url = reverse("delete-material", args=[self.module.id])
        self.client = Client()

    def test_teacher_with_perm_passes(self):
        self.client.force_login(self.teacher)
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (200, 302))

    def test_student_without_perm_denied(self):
        self.client.force_login(self.student)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_it_admin_passes(self):
        self.client.force_login(self.it_admin)
        resp = self.client.post(self.url)
        self.assertIn(resp.status_code, (200, 302))
