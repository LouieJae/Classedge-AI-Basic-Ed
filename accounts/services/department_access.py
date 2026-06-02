from django.core.exceptions import PermissionDenied

from accounts.models.account_models import Profile


def authorize_department_head(user, department):
    """[Classedge LMS] Allow superusers or admins to act on a department.

    Department.head was removed from the model, so head-based access no
    longer applies — the function name is preserved to keep callers stable.
    """
    if user.is_superuser:
        return
    try:
        profile = Profile.objects.select_related("role").get(user=user)
        role_name = profile.role_name
    except Profile.DoesNotExist:
        role_name = ""
    if role_name == "admin":
        return
    raise PermissionDenied("Not authorized for this department.")
