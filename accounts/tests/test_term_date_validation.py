from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.tests.helpers import make_department, make_semester
from course.models.term_model import Term


class TermCleanTests(TestCase):
    def setUp(self):
        self.dept = make_department()
        self.sem = make_semester(
            self.dept,
            name="First Semester",
            start=date(2026, 6, 1),
            end=date(2026, 10, 31),
        )

    def _term(self, start, end):
        return Term(
            term_name="Prelim",
            semester=self.sem,
            start_date=start,
            end_date=end,
        )

    def test_in_range_passes(self):
        self._term(date(2026, 6, 15), date(2026, 7, 15)).full_clean()

    def test_start_before_semester_start_rejects(self):
        with self.assertRaisesMessage(ValidationError, "earlier than the semester's start date"):
            self._term(date(2026, 5, 31), date(2026, 7, 15)).full_clean()

    def test_end_after_semester_end_rejects(self):
        with self.assertRaisesMessage(ValidationError, "later than the semester's end date"):
            self._term(date(2026, 6, 15), date(2026, 11, 15)).full_clean()

    def test_end_before_start_rejects(self):
        with self.assertRaisesMessage(ValidationError, "earlier than its start date"):
            self._term(date(2026, 7, 15), date(2026, 7, 1)).full_clean()

    def test_missing_dates_ok(self):
        self._term(None, None).full_clean()
