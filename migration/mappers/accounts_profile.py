import secrets

from migration.mappers._files import download_media
from migration.mappers.base import MapperResult, register_mapper
from migration.models import IDMap


def _new_share_token() -> str:
    """Random URL-safe token, same shape as the new-side default."""
    return secrets.token_urlsafe(32)[:43]


@register_mapper("accounts", "Profile")
def map_profile(payload: dict) -> MapperResult:
    """Profile is OneToOne with CustomUser. 4 nullable FKs soft-resolved.

    New-side-only fields:
      - share_token: generated fresh (URL-safe, 43 chars). Each migrated
        profile gets a unique sharing token — old shareable links from sim
        won't carry over, by design (security: rotates on migration).
      - share_enabled: defaults False (must be re-enabled by the user).

    Profile auto-creation: accounts/utils/signal_utils.py fires on CustomUser
    post_save and creates a default Profile with role=Student. The Profile
    mapper must adopt that signal-created row (via natural_key on user_id)
    and overwrite the role with the source's actual role — otherwise every
    migrated user ends up as Student regardless of their real role.
    """
    user_new_id = IDMap.resolve("accounts", "CustomUser", payload.get("user")) if payload.get("user") else None
    return MapperResult(
        fields={
            "status": payload.get("status"),
            "student_status": payload.get("student_status"),
            "first_name": payload.get("first_name"),
            "last_name": payload.get("last_name"),
            "date_of_birth": payload.get("date_of_birth"),
            "gender": payload.get("gender"),
            "nationality": payload.get("nationality"),
            "address": payload.get("address"),
            "phone_number": payload.get("phone_number"),
            "id_number": payload.get("id_number"),
            "grade_year_level": payload.get("grade_year_level"),
            "is_coil_user": payload.get("is_coil_user", False),
            "student_photo": download_media(payload.get("student_photo")) or "",
            # New-side-only — safe defaults
            "share_token": _new_share_token(),
            "share_enabled": False,
            # FKs
            "user_id": user_new_id,
            "role_id": IDMap.resolve("roles", "Role", payload.get("role")) if payload.get("role") else None,
            "course_id": IDMap.resolve("accounts", "Course", payload.get("course")) if payload.get("course") else None,
            "department_fields_id": IDMap.resolve("accounts", "Department", payload.get("department_fields")) if payload.get("department_fields") else None,
        },
        natural_key={"user_id": user_new_id} if user_new_id else None,
    )
