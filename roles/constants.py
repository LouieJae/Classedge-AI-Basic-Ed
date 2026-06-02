"""[Classedge LMS] Module-level constants for the roles app."""

# Roles whose users appear in the department-head dropdown on
# the department-settings page. Program Head covers colleges today;
# Principal is listed proactively so the filter picks it up as soon
# as IT Admin creates the Principal role row.
DEPARTMENT_HEAD_ROLE_NAMES: tuple[str, ...] = ("Program Head", "Principal")
