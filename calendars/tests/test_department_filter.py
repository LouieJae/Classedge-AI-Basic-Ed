from django.test import TestCase

from accounts.models.account_models import CustomUser
from accounts.tests.helpers import make_department, make_profile_for
from calendars.services.department_filter import visible_department_ids


class VisibleDepartmentIdsTests(TestCase):
    def setUp(self):
        self.math = make_department(name="Math")
        self.sci = make_department(name="Sci")

    def _user(self, username, role, dept=None):
        u = CustomUser.objects.create_user(username=username, email=f"{username}@x.io", password="x")
        make_profile_for(u, role, department=dept)
        return u

    def test_superuser_sees_all(self):
        su = CustomUser.objects.create_superuser(username="su", email="su@x.io", password="x")
        make_profile_for(su, "admin")
        self.assertIsNone(visible_department_ids(su))

    def test_admin_sees_all(self):
        admin = self._user("adm", "admin")
        self.assertIsNone(visible_department_ids(admin))

    def test_teacher_in_math(self):
        t = self._user("t", "teacher", dept=self.math)
        self.assertEqual(visible_department_ids(t), {self.math.id})

    def test_head_of_math_without_profile_dept(self):
        u = self._user("h", "teacher")
        self.math.head = u
        self.math.save()
        self.assertEqual(visible_department_ids(u), {self.math.id})

    def test_head_and_member_of_different_depts(self):
        u = self._user("u", "teacher", dept=self.sci)
        self.math.head = u
        self.math.save()
        self.assertEqual(visible_department_ids(u), {self.math.id, self.sci.id})

    def test_user_without_any_dept(self):
        u = self._user("nobody", "teacher")
        self.assertEqual(visible_department_ids(u), set())
