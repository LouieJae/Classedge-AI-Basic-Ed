import logging
import os
import time
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from django.conf import settings

logger = logging.getLogger(__name__)

TENANT_ID = settings.MS_TENANT_ID
CLIENT_ID = settings.MS_CLIENT_ID

JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"

# Simple in-memory cache so we don’t fetch keys every request
_JWKS_CACHE = {"fetched_at": 0, "data": None}
_JWKS_TTL_SECONDS = 60 * 60  # 1 hour


def _mask(s: str, keep=6):
    if not s:
        return s
    if len(s) <= keep * 2:
        return s
    return f"{s[:keep]}...{s[-keep:]}"


def _get_jwks():
    global _JWKS_CACHE
    now = time.time()
    if not _JWKS_CACHE["data"] or now - _JWKS_CACHE["fetched_at"] > _JWKS_TTL_SECONDS:
        logger.debug("[O365] Fetching JWKS from Azure AD: %s", JWKS_URL)
        resp = requests.get(JWKS_URL, timeout=10)
        resp.raise_for_status()
        _JWKS_CACHE["data"] = resp.json()
        _JWKS_CACHE["fetched_at"] = now
        keys_count = len(_JWKS_CACHE['data'].get('keys', []))
        logger.debug("[O365] JWKS fetched, keys: %s", keys_count)
    else:
        age = int(now - _JWKS_CACHE['fetched_at'])
        logger.debug("[O365] Using cached JWKS (age %ss)", age)
    return _JWKS_CACHE["data"]


def validate_microsoft_token(token: str):
    """
    Validate Microsoft access token against Azure AD JWKS.
    Returns decoded payload if valid; raises on error.
    """
    logger.debug("[O365] validate_microsoft_token() called. Token (masked): %s", _mask(token))

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg")
    typ = header.get("typ")
    logger.debug("[O365] JWT header kid=%s alg=%s typ=%s", kid, alg, typ)

    if not kid:
        raise ValueError("Missing 'kid' in token header")

    jwks = _get_jwks()
    keys = jwks.get("keys", [])
    key = next((k for k in keys if k.get("kid") == kid), None)
    if not key:
        logger.warning(
            "[O365] No matching KID in JWKS. Available KIDs: %s",
            [k.get("kid") for k in keys],
        )
        raise ValueError("No matching 'kid' found in JWKS")

    public_key = RSAAlgorithm.from_jwk(key)

    logger.debug("[O365] Decoding token with audience=%s", CLIENT_ID)
    payload = jwt.decode(
        token,
        key=public_key,
        algorithms=["RS256"],
        audience="api://183431e3-ef34-43eb-8dbe-c4e4b7da7786",
        options={"verify_exp": True}
    )
    email = payload.get("preferred_username") or payload.get("upn")
    logger.info("[O365] Token valid for %s (tid=%s)", email, payload.get("tid"))

    return payload