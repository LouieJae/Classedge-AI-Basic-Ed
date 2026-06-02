from django.db import models
from django.core.validators import RegexValidator

# Hex color validator: accepts "#" + 3 or 6 hex digits, case-insensitive.
HEX_COLOR_RE = r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"


class SchoolName(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255)
    # Tenant brand color. Drives --brand-primary across the entire app
    # via the school_context processor and the master layout's runtime
    # injection. Forest (#1b4332) is the design-system default.
    brand_color = models.CharField(
        max_length=7,
        default="#1b4332",
        validators=[RegexValidator(HEX_COLOR_RE, "Enter a valid hex color (#RRGGBB or #RGB).")],
        help_text="Hex code (#RRGGBB). Drives the brand-primary token across every page.",
    )