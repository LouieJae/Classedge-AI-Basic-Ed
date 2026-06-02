"""[Classedge LMS] Shared mixin for Operations Mode dashboard tests."""
import uuid

from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_profile_for


class OperationsDashboardTestMixin:
    """[Classedge LMS] Reusable assertions for any Operations Mode dashboard view.

    Subclass requirements:
        url_name: str        — Django URL name for the dashboard view
        role: str            — exact Role.name (case-sensitive) that owns this dashboard
        glyph: str           — single-character role glyph that must appear in HTML
        kpi_count: int       — number of KPI cards expected in the strip
    """

    url_name = None
    role = None
    glyph = None
    kpi_count = None

    def make_user_with_role(self, role_name, username=None):
        """[Classedge LMS] Create an active user assigned to the given role and return it."""
        if username is None:
            username = f"u-{uuid.uuid4().hex[:8]}"
        user = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(user, role_name)
        return user

    def assert_renders_for_role(self):
        """[Classedge LMS] GET as the role owner returns 200 with KPIs in context."""
        user = self.make_user_with_role(self.role)
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        self.assertEqual(resp.status_code, 200, f"{self.role} should reach its dashboard")
        self.assertIn("kpis", resp.context)
        self.assertEqual(len(resp.context["kpis"]), self.kpi_count)
        return resp

    def assert_403_for_other_roles(self):
        """[Classedge LMS] GET as a Teacher (or other unrelated role) is denied (302/403)."""
        user = self.make_user_with_role("Teacher")
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        self.assertIn(resp.status_code, (302, 403), f"non-{self.role} must not reach the {self.role} dashboard")

    def assert_glyph_renders(self):
        """[Classedge LMS] The role glyph appears in the rendered HTML (sidebar role tag)."""
        resp = self.assert_renders_for_role()
        self.assertContains(resp, self.glyph)
