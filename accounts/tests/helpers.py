from accounts.models.department_models import Department
from accounts.models.account_models import CustomUser, Profile
from course.models.semester_model import Semester
from roles.models import Role


def make_department(name="Math", **_ignored):
    """[Classedge LMS] Create a Department for tests.

    The ``head`` and ``cadence`` kwargs were removed from the Department
    model; ``**_ignored`` keeps existing test signatures working without
    needing a sweeping refactor.
    """
    return Department.objects.create(name=name)


def make_semester(department, name="First Semester", start=None, end=None):
    """[Classedge LMS] Create a Semester owned by a department.

    NOTE: Requires Semester.department (added in Task 3 / migration
    course/00NN_semester_department). Calling before that migration
    is applied will raise TypeError.
    """
    from datetime import date
    return Semester.objects.create(
        semester_name=name,
        start_date=start or date(2026, 6, 1),
        end_date=end or date(2026, 10, 31),
        department=department,
    )


def make_profile_for(user, role_name, department=None):
    """[Classedge LMS] Attach a Profile + Role (+ optional department_fields) to a user."""
    role, _ = Role.objects.get_or_create(name=role_name)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.role = role
    profile.department_fields = department
    profile.save()
    return profile
