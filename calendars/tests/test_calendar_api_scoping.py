from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for
from calendars.models import Event


CALENDAR_API_URL_NAME = "calendar_api"


class CalendarApiScopingTests(TestCase):
    def setUp(self):
        self.math = make_department(name="Math")
        self.sci = make_department(name="Sci")
        creator = CustomUser.objects.create_user(username="creator", email="c@x.io", password="x")
        self.math_evt = Event.objects.create(
            title="Math Fair", start_date=date(2026, 6, 10),
            department=self.math, created_by=creator,
        )
        self.global_evt = Event.objects.create(
            title="All Hands", start_date=date(2026, 6, 11),
            created_by=creator,
        )

    def _login(self, username, role, dept=None):
        u = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(u, role, department=dept)
        self.client.force_login(u)
        return u

    def _titles(self, resp):
        return {item["title"] for item in resp.json() if item.get("type") == "event"}

    def test_math_teacher_sees_math_and_global(self):
        self._login("t1", "teacher", dept=self.math)
        resp = self.client.get(reverse(CALENDAR_API_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertIn("Math Fair", titles)
        self.assertIn("All Hands", titles)

    def test_sci_teacher_hidden_from_math_event(self):
        self._login("t2", "teacher", dept=self.sci)
        resp = self.client.get(reverse(CALENDAR_API_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertNotIn("Math Fair", titles)
        self.assertIn("All Hands", titles)

    def test_admin_sees_all(self):
        self._login("adm", "admin")
        resp = self.client.get(reverse(CALENDAR_API_URL_NAME))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertIn("Math Fair", titles)
        self.assertIn("All Hands", titles)
