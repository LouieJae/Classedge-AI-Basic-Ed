import json
from datetime import date, time

from django.db import connection
from django.test import TestCase, override_settings, Client

from course.models.semester_model import Semester
from course.models.term_model import Term
from received_central_content.tests.test_native_ingest import _create_subject


def _auth():
    return {"HTTP_AUTHORIZATION": "Bearer " + "t" * 40}


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class ScheduleAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.subject = _create_subject(subject_name="Math 101", subject_code="MATH101")

        self.semester = Semester.objects.create(
            semester_name="First Semester",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 12, 15),
        )
        self.term = Term.objects.create(
            term_name="Prelim",
            semester=self.semester,
            start_date=date(2026, 8, 15),
            end_date=date(2026, 10, 15),
        )

        from subject.models.schedule_model import Schedule
        Schedule.objects.create(
            subject_id=self.subject.id,
            schedule_start_time=time(8, 0),
            schedule_end_time=time(9, 30),
            days_of_week=["Mon", "Wed", "Fri"],
            semester=self.semester,
        )

    def test_no_token_returns_401(self):
        resp = self.client.get(f"/api/central/schedule/{self.subject.id}/")
        self.assertEqual(resp.status_code, 401)

    def test_unknown_subject_returns_404(self):
        resp = self.client.get("/api/central/schedule/99999/", **_auth())
        self.assertEqual(resp.status_code, 404)

    def test_subject_with_no_term_returns_400(self):
        no_term_subj = _create_subject(subject_name="No Term", subject_code="NT101")
        from subject.models.schedule_model import Schedule
        sem_no_term = Semester.objects.create(
            semester_name="Second Semester",
            start_date=date(2027, 1, 1),
            end_date=date(2027, 5, 31),
        )
        Schedule.objects.create(
            subject_id=no_term_subj.id,
            schedule_start_time=time(10, 0),
            schedule_end_time=time(11, 0),
            days_of_week=["Tue"],
            semester=sem_no_term,
        )
        resp = self.client.get(f"/api/central/schedule/{no_term_subj.id}/", **_auth())
        self.assertEqual(resp.status_code, 400)

    def test_schedule_returns_correct_data(self):
        resp = self.client.get(f"/api/central/schedule/{self.subject.id}/", **_auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["subject_id"], self.subject.id)
        self.assertEqual(data["subject_name"], "Math 101")
        self.assertIn("term", data)
        self.assertEqual(data["term"]["name"], "Prelim")
        self.assertEqual(data["term"]["start_date"], "2026-08-15")
        self.assertEqual(data["term"]["end_date"], "2026-10-15")
        self.assertIn("sessions", data)
        self.assertGreater(len(data["sessions"]), 0)
        self.assertIn("session_count", data)
        self.assertEqual(data["session_count"], len(data["sessions"]))
        self.assertEqual(data["minutes_per_session"], 90)
        first_session = data["sessions"][0]
        self.assertIn("date", first_session)
        self.assertIn("start_time", first_session)
        self.assertIn("end_time", first_session)
        self.assertIn("minutes", first_session)
