"""Badge evaluators for non-student / non-teacher roles (Admin, Registrar,
Academic Director, Program Head, Coil Admin, Time Keeper).

These roles don't have an activity ledger like StudentActivity or
IPTransaction, so evaluators here lean on account-level signals already
present on the user model (login timestamps, onboarding flags, tenure).

The catalog is intentionally small — anything richer should be manually
awarded via admin until a staff event ledger exists.
"""
from datetime import timedelta

from django.utils import timezone

from gamification.models import BadgeDefinition, StudentBadge


STAFF_ROLE = "staff"

_NON_STAFF_ROLES = {"student", "teacher"}


def _is_staff_user(user):
    role = (getattr(user, "role_name", "") or "").lower()
    return bool(role) and role not in _NON_STAFF_ROLES


def evaluate_staff_badges(user):
    """Award any unearned staff badges whose criteria are satisfied."""
    if not _is_staff_user(user):
        return

    earned_ids = set(
        StudentBadge.objects.filter(student=user).values_list("badge_id", flat=True)
    )
    candidates = BadgeDefinition.objects.filter(
        is_active=True, target_role=STAFF_ROLE,
    ).exclude(pk__in=earned_ids)

    for badge in candidates:
        criteria = badge.criteria_json or {}
        evaluator = STAFF_EVALUATORS.get(criteria.get("type"))
        if evaluator and evaluator(user, criteria):
            StudentBadge.objects.create(student=user, badge=badge)


def _eval_first_sign_in(user, criteria):
    return user.last_login is not None


def _eval_onboarded(user, criteria):
    needs_onboarding = getattr(user, "needs_onboarding", False)
    needs_password = getattr(user, "needs_password_setup", False)
    return not needs_onboarding and not needs_password


def _eval_tenure_days(user, criteria):
    if not user.date_joined:
        return False
    threshold = criteria.get("threshold", 30)
    return (timezone.now() - user.date_joined) >= timedelta(days=threshold)


def _eval_profile_complete(user, criteria):
    return bool(
        (user.first_name or "").strip()
        and (user.last_name or "").strip()
        and (user.email or "").strip()
    )


def _eval_recently_active(user, criteria):
    if not user.last_login:
        return False
    window = criteria.get("within_days", 7)
    return (timezone.now() - user.last_login) <= timedelta(days=window)


def _eval_role_admin(user, criteria):
    role = (getattr(user, "role_name", "") or "").lower()
    return role == "admin" or getattr(user, "is_staff", False)


STAFF_EVALUATORS = {
    "first_sign_in": _eval_first_sign_in,
    "onboarded": _eval_onboarded,
    "tenure_days": _eval_tenure_days,
    "profile_complete": _eval_profile_complete,
    "recently_active": _eval_recently_active,
    "role_admin": _eval_role_admin,
}
