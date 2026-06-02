from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for


class DepartmentListViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="adm", email="adm@test.io", password="x",
        )
        make_profile_for(self.admin, "admin")
        self.teacher = CustomUser.objects.create_user(
            username="t", email="t@test.io", password="x",
        )
        make_profile_for(self.teacher, "teacher")
        self.math = make_department(name="Math")

    def test_anonymous_denied(self):
        resp = self.client.get(reverse("department_list"))
        self.assertIn(resp.status_code, (302, 403))

    def test_teacher_denied(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("department_list"))
        self.assertEqual(resp.status_code, 403)

    def test_admin_lists_departments(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("department_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Math")


class DepartmentSettingsViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="adm2", email="adm2@test.io", password="x",
        )
        make_profile_for(self.admin, "admin")
        self.dept = make_department(name="Science")
        self.someone = CustomUser.objects.create_user(
            username="boss", email="boss@test.io", password="x",
        )
        make_profile_for(self.someone, "teacher")

    def test_admin_can_save_head_and_cadence(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_settings", args=[self.dept.id]),
            {"name": self.dept.name, "head": self.someone.id, "cadence": "trimester"},
        )
        self.assertIn(resp.status_code, (200, 302))
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.head_id, self.someone.id)
        self.assertEqual(self.dept.cadence, "trimester")

    def test_teacher_denied(self):
        t = CustomUser.objects.create_user(username="t2", email="t2@x.io", password="x")
        make_profile_for(t, "teacher")
        self.client.force_login(t)
        resp = self.client.get(reverse("department_settings", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 403)


