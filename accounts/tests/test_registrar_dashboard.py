"""[Classedge LMS] Registrar Operations Mode dashboard tests."""
from django.test import TestCase
from django.urls import reverse

from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin


class RegistrarDashboardTests(OperationsDashboardTestMixin, TestCase):
    """[Classedge LMS] Access + content tests for the Registrar dashboard."""

    url_name = "registrar_dashboard"
    role = "Registrar"
    glyph = "⎙"
    kpi_count = 5

    def test_renders_for_registrar(self):
        """[Classedge LMS] Registrar owner gets 200 with the expected KPI count."""
        self.assert_renders_for_role()

    def test_403_for_other_roles(self):
        """[Classedge LMS] Non-Registrar (Teacher) is denied (302/403)."""
        self.assert_403_for_other_roles()

    def test_glyph_renders_in_html(self):
        """[Classedge LMS] The role glyph appears in the rendered sidebar tag."""
        self.assert_glyph_renders()

    def test_aging_queue_sorted_oldest_first(self):
        """[Classedge LMS] When rows are present, the queue exposes them oldest-first with flag at >7d."""
        from unittest.mock import patch
        fake_rows = [
            {"cells": [1, "u_old", "10d"], "age_days": 10, "flagged": True},
            {"cells": [2, "u_mid", "3d"], "age_days": 3, "flagged": False},
            {"cells": [3, "u_new", "0d"], "age_days": 0, "flagged": False},
        ]
        user = self.make_user_with_role(self.role)
        self.client.force_login(user)
        with patch("accounts.views.registrar._aging_queue_rows", return_value=fake_rows):
            resp = self.client.get(reverse(self.url_name))
        rows = resp.context["aging_rows"]
        self.assertEqual(len(rows), 3)
        ages = [row["age_days"] for row in rows]
        self.assertEqual(ages, [10, 3, 0])
        self.assertTrue(rows[0]["flagged"])
        self.assertFalse(rows[2]["flagged"])
