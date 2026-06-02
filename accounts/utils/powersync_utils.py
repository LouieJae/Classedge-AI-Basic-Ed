import os
import hashlib
import jwt
from datetime import datetime, timedelta
from typing import Optional
 
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
 
 
def _derive_kid_from_public_key(public_key_pem: str) -> str:
    """Generate a deterministic key ID from the RSA public key modulus."""
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"),
        backend=default_backend(),
    )
    public_numbers = public_key.public_numbers()
    modulus_bytes = public_numbers.n.to_bytes(
        (public_numbers.n.bit_length() + 7) // 8,
        byteorder="big",
    )
    return hashlib.sha256(modulus_bytes).hexdigest()[:16]
 
 
def generate_powersync_token(
    user_id: int,
    request=None,
    expires_in_minutes: int = 15,
    powersync_url: Optional[str] = None,
    issuer: Optional[str] = None,
) -> str:
    """Create a short-lived PowerSync JWT signed with RS256."""
 
    if not settings.RS256_PRIVATE_KEY or not settings.RS256_PUBLIC_KEY:
        raise ValueError("RS256 key pair is not configured in settings")
 
    audience = powersync_url or os.getenv("POWERSYNC_URL", "https://powersync.example.com")
 
    issuer_value = issuer or os.getenv("POWERSYNC_ISSUER")
    if not issuer_value:
        if request is not None:
            issuer_value = f"{request.scheme}://{request.get_host()}"
        else:
            issuer_value = getattr(settings, "SITE_URL", "http://localhost")
 
    kid = _derive_kid_from_public_key(settings.RS256_PUBLIC_KEY)
 
    payload = {
        "sub": user_id,
        "aud": audience,
        "iss": issuer_value,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=expires_in_minutes),
    }
 
    token = jwt.encode(
        payload,
        settings.RS256_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": kid},
    )
 
    return token