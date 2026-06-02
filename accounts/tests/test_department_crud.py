"""[Classedge LMS] Tests for Department create/edit/delete admin flow."""
from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.models.department_models import Department
from accounts.tests.helpers import make_department, make_profile_for


class DepartmentCreateViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="it_admin", email="ita@test.io", password="x", is_superuser=True,
        )
        make_profile_for(self.admin, "IT Admin")
        self.teacher = CustomUser.objects.create_user(
            username="t_crud", email="t_crud@test.io", password="x",
        )
        make_profile_for(self.teacher, "Teacher")

    def test_teacher_denied(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("department_create"))
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_denied(self):
        resp = self.client.get(reverse("department_create"))
        self.assertIn(resp.status_code, (302, 403))

    def test_admin_sees_form(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("department_create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "New Department")
        self.assertContains(resp, 'name="name"')

    def test_admin_creates_department(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_create"),
            {"name": "Engineering", "head": "", "cadence": "semester"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], reverse("department_list"))
        dept = Department.objects.get(name="Engineering")
        self.assertEqual(dept.cadence, "semester")
        self.assertIsNone(dept.head)

    def test_empty_name_rejected(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_create"),
            {"name": "   ", "cadence": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Department.objects.filter(cadence="").exists())

    def test_duplicate_name_rejected(self):
        make_department(name="Law")
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_create"),
            {"name": "law", "cadence": ""},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Department.objects.filter(name__iexact="law").count(), 1)

    def test_bogus_cadence_sanitized_to_null(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("department_create"),
            {"name": "History", "cadence": "not-a-real-choice"},
        )
        dept = Department.objects.get(name="History")
        self.assertIsNone(dept.cadence)


class DepartmentEditNameTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="it_admin2", email="ita2@test.io", password="x", is_superuser=True,
        )
        make_profile_for(self.admin, "IT Admin")
        self.dept = make_department(name="Science")
        self.other = make_department(name="Arts")

    def test_admin_can_rename(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_settings", args=[self.dept.id]),
            {"name": "Applied Sciences", "head": "", "cadence": "trimester"},
        )
        self.assertEqual(resp.status_code, 302)
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.name, "Applied Sciences")
        self.assertEqual(self.dept.cadence, "trimester")

    def test_rename_to_existing_other_blocked(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("department_settings", args=[self.dept.id]),
            {"name": "Arts", "cadence": ""},
        )
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.name, "Science")

    def test_rename_to_own_name_allowed(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("department_settings", args=[self.dept.id]),
            {"name": "Science", "cadence": "quarter"},
        )
        self.assertEqual(resp.status_code, 302)
        self.dept.refresh_from_db()
        self.assertEqual(self.dept.cadence, "quarter")


class DepartmentDeleteViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="it_admin3", email="ita3@test.io", password="x", is_superuser=True,
        )
        make_profile_for(self.admin, "IT Admin")
        self.teacher = CustomUser.objects.create_user(
            username="t_del", email="t_del@test.io", password="x",
        )
        make_profile_for(self.teacher, "Teacher")
        self.dept = make_department(name="To Be Deleted")

    def test_teacher_denied(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("department_delete", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 403)

    def test_get_shows_confirm_page(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("department_delete", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Delete")
        self.assertContains(resp, "To Be Deleted")
        self.assertTrue(Department.objects.filter(pk=self.dept.pk).exists())

    def test_post_deletes(self):
        self.client.force_login(self.admin)
        resp = self.client.post(reverse("department_delete", args=[self.dept.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Department.objects.filter(pk=self.dept.pk).exists())

    def test_delete_missing_returns_404(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("department_delete", args=[99999]))
        self.assertEqual(resp.status_code, 404)


class DepartmentListCrudCtaTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="it_admin4", email="ita4@test.io", password="x", is_superuser=True,
        )
        make_profile_for(self.admin, "IT Admin")
        make_department(name="Visible Department")

    def test_list_shows_new_department_cta(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("department_list"))
        self.assertContains(resp, "New Department")
        self.assertContains(resp, reverse("department_create"))
        self.assertContains(resp, "Edit")
        self.assertContains(resp, "Delete")
