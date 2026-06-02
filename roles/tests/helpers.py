"""[Classedge LMS] Shared test helpers for Phase 2 permission-gating tests."""
from django.contrib.auth import get_user_model

from accounts.models.account_models import Profile
from roles.migrations._m0004_grant_phase2_perms_helper import PHASE2_GRANTS
from roles.models import Role


User = get_user_model()


def make_user_with_role(username, role_name, *, grant_phase2=True):
    """[Classedge LMS] Create a user assigned to a named role.

    The Profile is auto-created by accounts.utils.signal_utils on user
    creation (defaulted to Student). We then update the profile to the
    requested role so the Phase 1 transition-aware is_superuser signal
    fires correctly.

    If grant_phase2 is True and PHASE2_GRANTS has an entry for role_name,
    the role receives those perms (mirroring what the data migration does
    in production). Roles outside PHASE2_GRANTS get no perms and should
    be denied by the perm-gated views.
    """
    role, _ = Role.objects.get_or_create(name=role_name)
    if grant_phase2 and role_name in PHASE2_GRANTS:
        # Use the migration's own grant function so test setup cannot
        # drift from production grants.
        from roles.migrations._m0004_grant_phase2_perms_helper import (
            grant_phase2_perms,
        )

        class _Shim:
            def get_model(self, app_label, model_name):
                from django.apps import apps
                return apps.get_model(app_label, model_name)

        grant_phase2_perms(_Shim(), None)

    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.invalid",
        password="Test@1234",
    )
    profile = Profile.objects.get(user=user)
    profile.role = role
    profile.save()
    user.refresh_from_db()  # pull is_superuser changes the signal may have made
    return user


def make_it_admin(username="phase2_it_admin"):
    """[Classedge LMS] Create an IT Admin (superuser) user — bypasses all perms."""
    role, _ = Role.objects.get_or_create(name="IT Admin")
    user = User.objects.create_superuser(
        username=username,
        email=f"{username}@example.invalid",
        password="Test@1234",
    )
    profile = Profile.objects.get(user=user)
    profile.role = role
    profile.save()
    user.refresh_from_db()
    return user
