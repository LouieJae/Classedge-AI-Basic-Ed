import re
from django.contrib.auth import get_user_model

User = get_user_model()


def _split_viewers(s: str):
    """
    Expect 'email1|email2|username3' (pipe-separated).
    Be generous: also accept ',' and ';' as separators.
    Returns list[User].
    """
    if not s:
        return []
    raw = [p.strip() for p in re.split(r"[|,;]", s) if p.strip()]
    users = []
    for token in raw:
        u = (
            User.objects.filter(email__iexact=token).first()
            or User.objects.filter(username__iexact=token).first()
        )
        if u:
            users.append(u)
    return users
