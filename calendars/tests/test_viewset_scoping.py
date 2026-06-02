from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for
from calendars.models import Announcement, Event


class EventViewSetScopingTests(TestCase):
    def setUp(self):
        self.math = make_department(name="Math")
        self.sci = make_department(name="Sci")
        creator = CustomUser.objects.create_user(username="creator", email="c@x.io", password="x")
        Event.objects.create(
            title="Math Fair", start_date=date(2026, 6, 10),
            department=self.math, created_by=creator,
        )
        Event.objects.create(
            title="All Hands", start_date=date(2026, 6, 11),
            created_by=creator,
        )

    def _login(self, username, role, dept=None):
        u = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(u, role, department=dept)
        self.client.force_login(u)
        return u

    def _titles(self, resp):
        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        return {item["title"] for item in results}

    def test_sci_teacher_hidden_from_math_event(self):
        self._login("t", "teacher", dept=self.sci)
        resp = self.client.get(reverse("events-list"))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertNotIn("Math Fair", titles)
        self.assertIn("All Hands", titles)

    def test_admin_sees_all(self):
        self._login("adm", "admin")
        resp = self.client.get(reverse("events-list"))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertIn("Math Fair", titles)
        self.assertIn("All Hands", titles)


class AnnouncementViewSetScopingTests(TestCase):
    def setUp(self):
        self.math = make_department(name="Math")
        self.sci = make_department(name="Sci")
        creator = CustomUser.objects.create_user(username="creator", email="c@x.io", password="x")
        Announcement.objects.create(
            title="Math Update", description="x", date=date(2026, 6, 10),
            department=self.math, created_by=creator,
        )
        Announcement.objects.create(
            title="Institution Update", description="y", date=date(2026, 6, 11),
            created_by=creator,
        )

    def _login(self, username, role, dept=None):
        u = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(u, role, department=dept)
        self.client.force_login(u)
        return u

    def _titles(self, resp):
        data = resp.json()
        results = data.get("results", data) if isinstance(data, dict) else data
        return {item["title"] for item in results}

    def test_sci_teacher_hidden_from_math_announcement(self):
        self._login("t", "teacher", dept=self.sci)
        resp = self.client.get(reverse("announcement-list"))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertNotIn("Math Update", titles)
        self.assertIn("Institution Update", titles)

    def test_admin_sees_all(self):
        self._login("adm", "admin")
        resp = self.client.get(reverse("announcement-list"))
        self.assertEqual(resp.status_code, 200)
        titles = self._titles(resp)
        self.assertIn("Math Update", titles)
        self.assertIn("Institution Update", titles)
