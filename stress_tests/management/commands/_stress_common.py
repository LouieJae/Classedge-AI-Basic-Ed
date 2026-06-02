"""Shared constants for stress_tests management commands.

Markers used to tag every dummy object so teardown can find them safely.
"""

STRESS_EMAIL_DOMAIN = "stresstest.local"
STRESS_NAME_PREFIX = "[STRESS]"
STRESS_PASSWORD = "stresstest123"

# Roles we'll guarantee at least one seeded user for. IT Admin is intentionally
# excluded — accounts/signals.py auto-promotes IT Admin profiles to superuser.
SEEDED_ROLE_NAMES = [
    "Student",
    "Teacher",
    "Admin",
    "Program Head",
    "Dean",
    "Registrar",
    "Academic Director",
    "Parent",
    "Time Keeper",
    "Coil Admin",
]


def is_stress_email(email: str) -> bool:
    return bool(email) and email.endswith(f"@{STRESS_EMAIL_DOMAIN}")


def is_stress_name(name: str) -> bool:
    return bool(name) and name.startswith(STRESS_NAME_PREFIX)
