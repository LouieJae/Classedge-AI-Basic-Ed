"""[Classedge LMS] Tests for CSV export."""
from django.http import StreamingHttpResponse
from django.test import TestCase
from django.urls import reverse

from gradebookcomponent.services.csv_export import build_gradebook_csv
from gradebookcomponent.tests.helpers import (
    make_user, make_subject, make_activity, make_submission,
)


class CSVExportTest(TestCase):
    """[Classedge LMS] Covers generator header/data rows and streaming view wiring."""

    def setUp(self):
        self.teacher = make_user("t@t.local", "Teacher")
        self.subject = make_subject(self.teacher, name="Algebra")
        self.activity = make_activity(self.subject, quiz_type_name="Essay", max_score=10)
        self.student = make_user("s@t.local", "Student")
        make_submission(self.student, self.activity, score=8)
        self.client.force_login(self.teacher)

    def test_generator_yields_header_row(self):
        rows = list(build_gradebook_csv(self.subject, self.subject.term))
        self.assertTrue(any("Student ID" in r for r in rows))
        self.assertTrue(any("Essay activity" in r for r in rows))

    def test_generator_yields_student_row(self):
        rows = list(build_gradebook_csv(self.subject, self.subject.term))
        joined = "".join(rows)
        self.assertIn(self.student.last_name or self.student.username, joined)
        self.assertIn("8", joined)  # raw score

    def test_view_returns_streaming_response(self):
        response = self.client.get(reverse("gradebook_subject_csv", args=[self.subject.id]))
        self.assertIsInstance(response, StreamingHttpResponse)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_view_other_teacher_denied(self):
        other = make_user("o@t.local", "Teacher")
        self.client.force_login(other)
        response = self.client.get(reverse("gradebook_subject_csv", args=[self.subject.id]))
        self.assertEqual(response.status_code, 403)
