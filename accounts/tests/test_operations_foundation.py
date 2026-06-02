"""[Classedge LMS] Foundation tests for the Operations Mode dashboard templates."""
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class OperationsDashboardTemplateTests(SimpleTestCase):
    """[Classedge LMS] Verify base_operation.html renders all required zones."""

    def _ctx(self, **overrides):
        base = {
            "role_tag": "Test Role",
            "role_glyph": "▲",
            "nav_items": [{"url": "#", "label": "Dashboard", "active": True}],
            "scope_tags": [{"label": "Term", "value": "AY 2026"}],
            "quick_actions": [{"url": "#", "label": "Action", "primary": True}],
            "greeting_question": "What needs me today?",
            "kpis": [
                {"label": "Open Items", "value": "12", "delta": "+2", "tone": "warn"},
            ],
            "ctx_left": {"title": "Calendar", "items": []},
            "ctx_right": {"title": "Runway", "items": []},
            "request": type("R", (), {"user": type("U", (), {"first_name": "Tester", "username": "tester", "is_authenticated": True, "get_full_name": lambda self: "Tester User", "id": 1})()})(),
            "time_of_day": "morning",
            "admin_actions": [],
            "admin_action_columns": ["When", "Who", "Action"],
        }
        base.update(overrides)
        return base

    def test_renders_greeting_with_first_name(self):
        html = render_to_string("operations/it_admin_dashboard.html", self._ctx())
        self.assertIn("Good morning, Tester", html)
        self.assertIn("What needs me today?", html)

    def test_renders_scope_tags(self):
        html = render_to_string("operations/it_admin_dashboard.html", self._ctx())
        self.assertIn("Term", html)
        self.assertIn("AY 2026", html)

    def test_renders_kpi_strip(self):
        html = render_to_string("operations/it_admin_dashboard.html", self._ctx())
        self.assertIn("Open Items", html)
        self.assertIn("12", html)
        self.assertIn("kpi warn", html)

    def test_renders_quick_actions(self):
        html = render_to_string("operations/it_admin_dashboard.html", self._ctx())
        self.assertIn("Action", html)


class OperationsDashboardMixinSelfCheck(SimpleTestCase):
    """[Classedge LMS] Cheap self-check: importing the mixin must not error."""

    def test_mixin_importable(self):
        from accounts.tests.operations_dashboard_mixin import OperationsDashboardTestMixin
        self.assertTrue(hasattr(OperationsDashboardTestMixin, "assert_renders_for_role"))
