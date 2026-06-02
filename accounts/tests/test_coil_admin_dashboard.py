"""[Classedge LMS] Coil Admin Operations Mode dashboard tests."""
from django.test import TestCase
from django.urls import reverse

from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin
from coil.models import CoilPartnerSchool


class CoilAdminDashboardTests(OperationsDashboardTestMixin, TestCase):
    """[Classedge LMS] Access + content tests for the Coil Admin dashboard."""

    url_name = "coil_admin_dashboard"
    role = "Coil Admin"
    glyph = "⊕"
    kpi_count = 5

    def test_renders_for_coil_admin(self):
        """[Classedge LMS] Coil Admin owner gets 200 with the expected KPI count."""
        self.assert_renders_for_role()

    def test_403_for_other_roles(self):
        """[Classedge LMS] Non-Coil-Admin (Teacher) is denied (302/403)."""
        self.assert_403_for_other_roles()

    def test_glyph_renders_in_html(self):
        """[Classedge LMS] The role glyph appears in the rendered sidebar tag."""
        self.assert_glyph_renders()

    def test_pending_partners_first_in_table(self):
        """[Classedge LMS] Pending Acceptance rows must appear before Partner rows."""
        CoilPartnerSchool.objects.create(school_name="A", school_domain="a.edu", status="Partner")
        CoilPartnerSchool.objects.create(school_name="B", school_domain="b.edu", status="Pending Acceptance")
        user = self.make_user_with_role(self.role, "ca1")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        partners = resp.context["partner_rows"]
        statuses = [row["cells"][1] for row in partners]
        self.assertLess(statuses.index("Pending Acceptance"), statuses.index("Partner"))

    def test_collaborative_classes_panel_is_stub(self):
        """[Classedge LMS] Collaborative-classes panel renders both the section title and the documented stub copy."""
        user = self.make_user_with_role(self.role, "ca2")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        self.assertContains(resp, "Collaborative Classes")
        self.assertContains(resp, "Coming soon")
