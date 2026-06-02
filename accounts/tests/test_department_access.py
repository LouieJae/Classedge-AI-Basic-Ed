from django.core.exceptions import PermissionDenied
from django.test import TestCase

from accounts.models.account_models import CustomUser
from accounts.services.department_access import authorize_department_head
from accounts.tests.helpers import make_department, make_profile_for


class AuthorizeDepartmentHeadTests(TestCase):
    def setUp(self):
        self.dept = make_department(name="Math")
        self.head = CustomUser.objects.create_user(
            username="head", email="head@test.io", password="x",
        )
        self.dept.head = self.head
        self.dept.save()
        make_profile_for(self.head, "teacher")

    def test_superuser_allowed(self):
        su = CustomUser.objects.create_superuser(
            username="su", email="su@test.io", password="x",
        )
        authorize_department_head(su, self.dept)  # no raise

    def test_admin_allowed(self):
        admin = CustomUser.objects.create_user(
            username="adm", email="adm@test.io", password="x",
        )
        make_profile_for(admin, "admin")
        authorize_department_head(admin, self.dept)

    def test_head_allowed(self):
        authorize_department_head(self.head, self.dept)

    def test_random_teacher_denied(self):
        other = CustomUser.objects.create_user(
            username="t2", email="t2@test.io", password="x",
        )
        make_profile_for(other, "teacher")
        with self.assertRaises(PermissionDenied):
            authorize_department_head(other, self.dept)
