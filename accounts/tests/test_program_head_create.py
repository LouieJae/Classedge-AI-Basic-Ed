"""[Classedge LMS] Tests for the IT Admin 'Add Program Head' flow."""
from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser, Profile
from accounts.models.department_models import Department
from accounts.tests.helpers import make_department, make_profile_for
from roles.models import Role


class AddProgramHeadViewTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="ita_add_ph", email="ita_add_ph@test.io", password="x", is_superuser=True,
        )
        make_profile_for(self.admin, "IT Admin")
        self.teacher = CustomUser.objects.create_user(
            username="t_add_ph", email="t_add_ph@test.io", password="x",
        )
        make_profile_for(self.teacher, "Teacher")
        self.dept = make_department(name="College of Ops")

    def test_teacher_denied(self):
        self.client.force_login(self.teacher)
        resp = self.client.get(reverse("admin_create_program_head"))
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse("admin_create_program_head"))
        self.assertIn(resp.status_code, (302, 403))

    def test_admin_sees_form(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("admin_create_program_head"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "New Program Head")
        self.assertContains(resp, 'name="email"')
        self.assertContains(resp, 'name="password"')

    def test_admin_creates_program_head_happy_path(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_create_program_head"),
            {
                "email": "juan.delacruz@school.edu",
                "first_name": "Juan",
                "last_name": "Dela Cruz",
                "id_number": "PH-0001",
                "department_fields": self.dept.id,
                "password": "temp-pass-123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], reverse("program_head_list"))

        user = CustomUser.objects.get(email="juan.delacruz@school.edu")
        self.assertEqual(user.first_name, "Juan")
        self.assertTrue(user.check_password("temp-pass-123"))

        profile = Profile.objects.get(user=user)
        self.assertIsNotNone(profile.role)
        self.assertEqual(profile.role.name, "Program Head")
        self.assertEqual(profile.id_number, "PH-0001")
        self.assertEqual(profile.department_fields_id, self.dept.id)

    def test_duplicate_email_rejected(self):
        CustomUser.objects.create_user(
            username="dup", email="dup@school.edu", password="x",
        )
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_create_program_head"),
            {
                "email": "DUP@school.edu",
                "first_name": "Dup",
                "last_name": "Licate",
                "id_number": "",
                "department_fields": "",
                "password": "temp-pass-123",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already exists")
        self.assertEqual(CustomUser.objects.filter(email__iexact="dup@school.edu").count(), 1)

    def test_short_password_rejected(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_create_program_head"),
            {
                "email": "short.pw@school.edu",
                "first_name": "Short",
                "last_name": "Pass",
                "id_number": "",
                "department_fields": "",
                "password": "short",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email="short.pw@school.edu").exists())

    def test_optional_fields_truly_optional(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_create_program_head"),
            {
                "email": "minimal@school.edu",
                "first_name": "Min",
                "last_name": "Imal",
                "id_number": "",
                "department_fields": "",
                "password": "temp-pass-123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = CustomUser.objects.get(email="minimal@school.edu")
        profile = Profile.objects.get(user=user)
        self.assertIsNone(profile.id_number)
        self.assertIsNone(profile.department_fields)

    def test_accepted_eula_version_defaults_applied(self):
        """Regression: accounts_customuser.accepted_eula_version is NOT NULL in prod.
        create_user() must hand a value to the INSERT via the model default.
        """
        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin_create_program_head"),
            {
                "email": "eula.test@school.edu",
                "first_name": "Eula",
                "last_name": "Test",
                "id_number": "",
                "department_fields": "",
                "password": "temp-pass-123",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = CustomUser.objects.get(email="eula.test@school.edu")
        self.assertEqual(user.accepted_eula_version, "0.0.0")

    def test_role_is_created_if_missing(self):
        Role.objects.filter(name="Program Head").delete()
        self.client.force_login(self.admin)
        self.client.post(
            reverse("admin_create_program_head"),
            {
                "email": "first.ph@school.edu",
                "first_name": "First",
                "last_name": "PH",
                "id_number": "",
                "department_fields": "",
                "password": "temp-pass-123",
            },
        )
        self.assertTrue(Role.objects.filter(name="Program Head").exists())
        profile = Profile.objects.get(user__email="first.ph@school.edu")
        self.assertEqual(profile.role.name, "Program Head")


class ProgramHeadListCtaTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="ita_list_cta", email="ita_list_cta@test.io", password="x", is_superuser=True,
        )
        make_profile_for(self.admin, "IT Admin")

    def test_list_shows_add_cta(self):
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("program_head_list"))
        self.assertContains(resp, "Add Program Head")
        self.assertContains(resp, reverse("admin_create_program_head"))
