from .base import MapperResult, register_mapper


UNUSABLE_PASSWORD_PREFIX = "!"  # Django convention: hashes starting with ! never match


@register_mapper("accounts", "CustomUser")
def map_customuser(payload: dict) -> MapperResult:
    """Map a sim CustomUser payload to the new-side CustomUser fields.

    Strategy:
    - Copy username/email/password hash verbatim (password stays a Django hash —
      not rehashed — so users can log in with their existing credentials).
    - If the sim row has a blank password (never-logged-in accounts), emit an
      unusable-password placeholder and set needs_password_setup=True so the
      user must reset on first login.
    - For the new fields that don't exist on sim, set safe defaults.
    """
    raw_password = payload.get("password") or ""
    if raw_password:
        password = raw_password
        needs_password_setup = False
    else:
        password = f"{UNUSABLE_PASSWORD_PREFIX}migrated-no-password"
        needs_password_setup = True

    return MapperResult(
        fields={
            "username": payload["username"],
            "password": password,
            "email": payload.get("email", "") or "",
            "first_name": payload.get("first_name", "") or "",
            "last_name": payload.get("last_name", "") or "",
            "is_active": payload.get("is_active", True),
            "is_staff": payload.get("is_staff", False),
            "is_superuser": payload.get("is_superuser", False),
            "date_joined": payload.get("date_joined"),
            "last_login": payload.get("last_login"),
            "legal_update_required": payload.get("legal_update_required", True),
            "accepted_privacy_version": payload.get("accepted_privacy_version", "0.0.0"),
            "accepted_eula_version": "0.0.0",
            "accepted_nda_version": "0.0.0",
            "needs_password_setup": needs_password_setup,
            "needs_onboarding": True,
        },
    )
