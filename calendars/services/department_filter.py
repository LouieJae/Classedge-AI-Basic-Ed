from accounts.models.account_models import Profile


def visible_department_ids(user):
    """[Classedge LMS] Return the set of Department IDs a user should see scoped calendar items for.

    Returns None to mean "no filter, see everything" (superusers + admins).
    Returns an (empty) set otherwise.
    """
    if user.is_superuser:
        return None
    profile = Profile.objects.select_related("role").filter(user=user).first()
    role = profile.role if profile else None
    if role and role.name and role.name.lower() == "admin":
        return None
    ids = set()
    if profile and profile.department_fields_id:
        ids.add(profile.department_fields_id)
    # `headed_departments` is a reverse relation that exists for program-head
    # users but is absent on standard CustomUser instances. The dashboard
    # context processor already guards with hasattr (see
    # accounts/context_processors.py:31); mirror that here so calendar API
    # calls don't 500 for teachers/registrars/etc.
    headed = getattr(user, "headed_departments", None)
    if headed is not None:
        try:
            ids.update(headed.values_list("id", flat=True))
        except Exception:
            pass
    return ids
