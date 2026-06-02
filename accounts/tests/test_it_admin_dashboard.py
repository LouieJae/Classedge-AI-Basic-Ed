"""[Classedge LMS] Dashboard access + routing tests for IT Admin."""
from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser, Profile
from roles.models import Role


class ItAdminDashboardAccessTests(TestCase):
    """[Classedge LMS] Access-control tests for the IT Admin landing dashboard."""

    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def test_it_admin_can_view_dashboard(self):
        """[Classedge LMS] IT Admin user gets the dashboard with counts in context."""
        user = CustomUser.objects.create_user(
            username="it1", email="it1@x.io", password="x",
        )
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()
        self.client.force_login(user)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("user_count", resp.context)
        self.assertIn("role_count", resp.context)
        self.assertIn("department_count", resp.context)
        self.assertIn("superuser_count", resp.context)

    def test_teacher_denied(self):
        """[Classedge LMS] Non-superuser (Teacher) must not see the IT Admin dashboard."""
        user = CustomUser.objects.create_user(
            username="t1", email="t1@x.io", password="x",
        )
        profile = Profile.objects.get(user=user)
        profile.role = self.teacher_role
        profile.save()
        self.client.force_login(user)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertIn(resp.status_code, (302, 403))

    def test_anonymous_redirected_to_login(self):
        """[Classedge LMS] Anonymous requests redirect to login."""
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertEqual(resp.status_code, 302)


class DashboardRoutingTests(TestCase):
    """[Classedge LMS] /dashboard/ routing: superusers bounced to /it-admin/; other roles unchanged."""

    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")
        self.teacher_role, _ = Role.objects.get_or_create(name="Teacher")

    def test_superuser_redirects_to_it_admin(self):
        """[Classedge LMS] Superusers hitting /dashboard/ get bounced to /it-admin/."""
        user = CustomUser.objects.create_user(
            username="su2", email="su2@x.io", password="x",
        )
        profile = Profile.objects.get(user=user)
        profile.role = self.it_admin_role
        profile.save()  # Signal sets is_superuser=True
        user.refresh_from_db()
        self.assertTrue(user.is_superuser, "Precondition: signal flipped is_superuser=True")
        self.client.force_login(user)
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("it_admin_dashboard"))

    def test_teacher_dashboard_unchanged(self):
        """[Classedge LMS] Teachers don't get bounced to /it-admin/."""
        user = CustomUser.objects.create_user(
            username="t2", email="t2@x.io", password="x",
        )
        profile = Profile.objects.get(user=user)
        profile.role = self.teacher_role
        profile.save()
        self.client.force_login(user)
        resp = self.client.get(reverse("dashboard"))
        # Teacher path may render directly (200) or redirect to a teacher-specific URL.
        # Either way, must NOT be the it_admin_dashboard URL.
        if resp.status_code == 302:
            self.assertNotEqual(resp.url, reverse("it_admin_dashboard"))
        else:
            self.assertEqual(resp.status_code, 200)


class ItAdminDashboardOperationsModeTests(TestCase):
    """[Classedge LMS] Operations Mode shell + KPI strip render for IT Admin."""

    def setUp(self):
        self.it_admin_role, _ = Role.objects.get_or_create(name="IT Admin")

    def test_renders_kpi_strip(self):
        """[Classedge LMS] IT Admin dashboard renders 5 KPIs and the gear glyph."""
        u = CustomUser.objects.create_user(username="su_op", email="su@x.io", password="x")
        p = Profile.objects.get(user=u)
        p.role = self.it_admin_role
        p.save()  # signal flips is_superuser=True
        u.refresh_from_db()
        self.client.force_login(u)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["kpis"]), 5)
        self.assertContains(resp, "⚙")  # IT Admin glyph

    def test_uses_operations_template(self):
        """[Classedge LMS] IT Admin dashboard extends the Operations Mode shell."""
        u = CustomUser.objects.create_user(username="su_t", email="sut@x.io", password="x")
        p = Profile.objects.get(user=u)
        p.role = self.it_admin_role
        p.save()
        u.refresh_from_db()
        self.client.force_login(u)
        resp = self.client.get(reverse("it_admin_dashboard"))
        self.assertTemplateUsed(resp, "operations/it_admin_dashboard.html")
        self.assertTemplateUsed(resp, "base_operation.html")
