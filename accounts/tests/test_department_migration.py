from django.test import TestCase

from accounts.models.department_models import Department
from course.models.semester_model import Semester


class SeedGeneralDepartmentTests(TestCase):
    """Post-migrate state: the fixture runs the data migration automatically."""

    def test_general_department_exists_exactly_once(self):
        self.assertEqual(Department.objects.filter(name="General").count(), 1)

    def test_no_orphan_semesters(self):
        self.assertEqual(Semester.objects.filter(department__isnull=True).count(), 0)
