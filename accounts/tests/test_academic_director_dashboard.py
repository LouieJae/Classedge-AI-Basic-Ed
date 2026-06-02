"""[Classedge LMS] Academic Director Operations Mode dashboard tests."""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin


class AcademicDirectorDashboardTests(OperationsDashboardTestMixin, TestCase):
    """[Classedge LMS] Access + content tests for the Academic Director dashboard."""

    url_name = "academic_director_dashboard"
    role = "Academic Director"
    glyph = "▲"
    kpi_count = 4

    def test_renders_for_academic_director(self):
        """[Classedge LMS] Academic Director owner gets 200 with the expected KPI count."""
        self.assert_renders_for_role()

    def test_403_for_other_roles(self):
        """[Classedge LMS] Non-Academic-Director (Teacher) is denied (302/403)."""
        self.assert_403_for_other_roles()

    def test_glyph_renders_in_html(self):
        """[Classedge LMS] The role glyph appears in the rendered sidebar tag."""
        self.assert_glyph_renders()

    def test_pending_decisions_oldest_first(self):
        """[Classedge LMS] Pending decisions context propagates patched rows in given order with all fields preserved."""
        fake_rows = [
            {"cells": ["SyllabusPlan #14", "Apr 1", "26d"], "age_days": 26, "flagged": True},
            {"cells": ["Content Reqs #7", "Apr 15", "12d"], "age_days": 12, "flagged": False},
            {"cells": ["Escalation #3", "Apr 25", "2d"], "age_days": 2, "flagged": False},
        ]
        user = self.make_user_with_role(self.role)
        self.client.force_login(user)
        with patch("accounts.views.academic_director._pending_decision_rows", return_value=fake_rows):
            resp = self.client.get(reverse(self.url_name))
        rows = resp.context["pending_decision_rows"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["age_days"] for r in rows], [26, 12, 2])
        self.assertEqual(rows[0]["cells"][0], "SyllabusPlan #14")
        self.assertTrue(rows[0]["flagged"])
        self.assertFalse(rows[2]["flagged"])

    def test_no_student_names_in_primary_panel(self):
        """[Classedge LMS] Per spec anti-pattern: heatmap rows are categorical (program), not per-student."""
        user = self.make_user_with_role(self.role)
        self.client.force_login(user)
        resp = self.client.get(reverse(self.url_name))
        for row in resp.context["heatmap_rows"]:
            self.assertIn("program", row, f"row missing 'program' key: {row}")
            row_blob = str(row).lower()
            self.assertNotIn("student", row_blob)
            self.assertNotIn("user", row_blob)
            self.assertNotIn("email", row_blob)
            self.assertNotIn("@", row_blob)
