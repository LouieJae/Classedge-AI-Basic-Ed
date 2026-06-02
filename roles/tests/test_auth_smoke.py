"""[Classedge LMS] End-to-end smoke tests for the auth surface Phase 3 touches."""
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models.department_models import Department
from roles.tests.helpers import make_it_admin, make_user_with_role


class DepartmentHeadDropdownTests(TestCase):
    """[Classedge LMS] The candidate_heads dropdown on the department
    settings page must filter to users whose role is Program Head
    (or Principal once the role is created). Regular users — teachers,
    students, registrars — must NOT appear."""

    def setUp(self):
        self.admin = make_it_admin(username="dept_head_admin")
        self.program_head = make_user_with_role(
            "ph_user", "Program Head", grant_phase2=False,
        )
        self.teacher = make_user_with_role(
            "t_user", "Teacher", grant_phase2=False,
        )
        self.dept = Department.objects.create(name="Test Dept")
        self.client = Client()
        self.client.force_login(self.admin)

    @staticmethod
    def _extract_head_select(html):
        """[Classedge LMS] Pull the text content of the <select name="head"> block.

        The department-settings page contains a sidebar URL
        (/import_and_export_user_page/) that embeds the substring 't_user'.
        Checking the full-page HTML would produce false positives, so we scope
        assertions to the dropdown block only.
        """
        start = html.find('<select name="head"')
        end = html.find("</select>", start)
        if start == -1 or end == -1:
            return ""
        return html[start : end + len("</select>")]

    def test_candidate_heads_dropdown_excludes_teachers(self):
        """Only Program Head users appear in the dropdown; teachers don't."""
        resp = self.client.get(
            reverse("department_settings", args=[self.dept.pk])
        )
        self.assertEqual(resp.status_code, 200)
        select_html = self._extract_head_select(resp.content.decode())
        self.assertTrue(select_html, "Could not find <select name='head'> in response")
        self.assertIn(
            self.program_head.username, select_html,
            "Program Head user should appear in candidate_heads",
        )
        self.assertNotIn(
            self.teacher.username, select_html,
            "Teacher user must NOT appear in candidate_heads",
        )

    def test_candidate_heads_dropdown_includes_principal_when_role_exists(self):
        """DEPARTMENT_HEAD_ROLE_NAMES already lists Principal — creating a
        Principal user surfaces them in the dropdown with no code change."""
        principal = make_user_with_role(
            "principal_user", "Principal", grant_phase2=False,
        )
        resp = self.client.get(
            reverse("department_settings", args=[self.dept.pk])
        )
        select_html = self._extract_head_select(resp.content.decode())
        self.assertIn(principal.username, select_html)


class AuthFlowSmokeTests(TestCase):
    """[Classedge LMS] Smoke test: login → protected page → logout → redirect."""

    def test_login_logout_roundtrip(self):
        """IT Admin can log in, reach a protected page, and gets redirected
        to login after logout."""
        admin = make_it_admin(username="login_admin")
        c = Client()
        ok = c.login(username="login_admin", password="Test@1234")
        self.assertTrue(ok, "IT Admin could not log in with test password")

        protected = c.get(reverse("role_list"))
        self.assertEqual(
            protected.status_code, 200,
            "Authenticated IT Admin should reach /role_list/",
        )

        c.logout()
        after_logout = c.get(reverse("role_list"))
        self.assertIn(
            after_logout.status_code, (301, 302),
            "Logged-out user should be redirected away from /role_list/",
        )


class RoleCRUDSmokeTests(TestCase):
    """[Classedge LMS] End-to-end role CRUD roundtrip via the HTTP surface.
    Creates a role, updates its permissions, views it, deletes it."""

    def setUp(self):
        self.admin = make_it_admin(username="crud_admin")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_create_update_view_delete_role_roundtrip(self):
        from django.contrib.auth.models import Permission

        from roles.models import Role

        # CREATE
        some_perm = Permission.objects.filter(codename="view_customuser").first()
        self.assertIsNotNone(some_perm, "fixture: view_customuser must exist")
        resp = self.client.post(
            reverse("create_role"),
            {"name": "SmokeRole", "permissions": [some_perm.id]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        role = Role.objects.get(name="SmokeRole")
        self.assertIn(some_perm, role.permissions.all())

        # UPDATE — add a second permission
        other_perm = Permission.objects.filter(codename="add_customuser").first()
        self.assertIsNotNone(other_perm, "fixture: add_customuser must exist")
        resp = self.client.post(
            reverse("update_role", args=[role.pk]),
            {"name": "SmokeRole", "permissions": [some_perm.id, other_perm.id]},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        role.refresh_from_db()
        self.assertSetEqual(
            set(role.permissions.values_list("id", flat=True)),
            {some_perm.id, other_perm.id},
        )

        # VIEW
        resp = self.client.get(reverse("view_role", args=[role.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "SmokeRole")

        # DELETE
        resp = self.client.post(
            reverse("delete_role", args=[role.pk]),
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Role.objects.filter(pk=role.pk).exists())
