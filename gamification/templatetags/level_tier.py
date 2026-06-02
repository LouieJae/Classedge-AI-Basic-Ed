from django import template

register = template.Library()


@register.filter(name='level_tier')
def level_tier(level):
    """Return tier slug for a level integer.

    Bands: 1 none, 2-9 bronze, 10-19 silver, 20-29 gold, 30-49 platinum, 50+ diamond.
    Falsy/None defaults to none (level 1 and below show no tier color).
    """
    try:
        n = int(level or 0)
    except (TypeError, ValueError):
        return 'none'
    if n >= 50:
        return 'diamond'
    if n >= 30:
        return 'platinum'
    if n >= 20:
        return 'gold'
    if n >= 10:
        return 'silver'
    if n >= 2:
        return 'bronze'
    return 'none'
