"""[Classedge LMS] Microsoft Graph helpers — app-only flow.

The LMS authenticates to Microsoft Graph using the Azure app's client
credentials (no per-user OAuth dance) and writes uploaded Office files to a
single tenant-owned service account's OneDrive. The file's anonymous embed
link is returned so the LMS can render the PowerPoint / Word / Excel Online
viewer inside the materials page.

Required Azure permissions (Application, admin-consented):
    - Files.ReadWrite.All

Required settings:
    - MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET
    - ONEDRIVE_SERVICE_ACCOUNT_UPN  (e.g. "lms-files@holychild.edu.ph")
    - ONEDRIVE_UPLOAD_FOLDER        (default "ClassEdge")

Failures return None — callers fall back to the locally-stored file.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024  # 4MB per Graph docs
_TOKEN_CACHE_KEY = "onedrive_app_token"
_TOKEN_LOCK = threading.Lock()


def _token_endpoint() -> str:
    tenant = getattr(settings, "MS_TENANT_ID", None) or "common"
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


def _fetch_app_token() -> Optional[str]:
    """Acquire an app-only access token via client-credentials. Cached for
    ~55 minutes (tokens expire at 60). Thread-safe to avoid stampedes."""
    cached = cache.get(_TOKEN_CACHE_KEY)
    if cached:
        return cached

    with _TOKEN_LOCK:
        cached = cache.get(_TOKEN_CACHE_KEY)
        if cached:
            return cached

        resp = requests.post(
            _token_endpoint(),
            data={
                "client_id": settings.MS_CLIENT_ID,
                "client_secret": settings.MS_CLIENT_SECRET,
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=15,
        )
        if not resp.ok:
            logger.warning("OneDrive: client_credentials failed %s — %s",
                           resp.status_code, resp.text[:200])
            print(f"[OneDrive] token call FAILED status={resp.status_code} body={resp.text[:400]}")
            return None

        data = resp.json()
        token = data.get("access_token")
        print(f"[OneDrive] token call ok, access_token present={bool(token)}")
        expires_in = int(data.get("expires_in", 3600))
        if token:
            cache.set(_TOKEN_CACHE_KEY, token, timeout=max(60, expires_in - 300))
        return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _drive_root_path(path: str) -> str:
    """Build the Graph URL for an item under the service-account user's drive."""
    upn = getattr(settings, "ONEDRIVE_SERVICE_ACCOUNT_UPN", "").strip()
    if not upn:
        return ""
    return f"{GRAPH_BASE}/users/{upn}/drive/root:{path}"


def _drive_item_url(item_id: str) -> str:
    upn = getattr(settings, "ONEDRIVE_SERVICE_ACCOUNT_UPN", "").strip()
    return f"{GRAPH_BASE}/users/{upn}/drive/items/{item_id}"


def upload_and_embed(user, file_obj, *, filename: str) -> Optional[dict]:
    """Upload `file_obj` to the configured service account's OneDrive under
    settings.ONEDRIVE_UPLOAD_FOLDER and return
    ``{"item_id": str, "embed_url": str, "web_url": str}`` on success.
    The `user` argument is accepted for signature symmetry but unused — this
    flow is app-only.

    Returns None on any failure so callers can fall back to the local file."""
    print(f"[OneDrive] upload_and_embed: ENABLED={getattr(settings, 'ONEDRIVE_UPLOAD_ENABLED', False)}")
    if not getattr(settings, "ONEDRIVE_UPLOAD_ENABLED", False):
        print("[OneDrive] disabled via settings — aborting")
        return None
    upn = getattr(settings, "ONEDRIVE_SERVICE_ACCOUNT_UPN", "").strip()
    print(f"[OneDrive] UPN={upn!r}")
    if not upn:
        logger.info("OneDrive: ONEDRIVE_SERVICE_ACCOUNT_UPN not set — skipping upload")
        print("[OneDrive] no UPN set — aborting")
        return None

    print("[OneDrive] fetching app token via client_credentials...")
    token = _fetch_app_token()
    print(f"[OneDrive] token acquired: {bool(token)} (len={len(token) if token else 0})")
    if not token:
        return None

    folder = getattr(settings, "ONEDRIVE_UPLOAD_FOLDER", "ClassEdge").strip("/")
    safe_name = os.path.basename(filename)
    path = f"/{folder}/{safe_name}" if folder else f"/{safe_name}"

    file_obj.seek(0)
    payload = file_obj.read()

    print(f"[OneDrive] uploading {len(payload)} bytes to path={path}")
    if len(payload) <= SIMPLE_UPLOAD_LIMIT:
        url = f"{_drive_root_path(path)}:/content"
        print(f"[OneDrive] PUT {url}")
        resp = requests.put(
            url,
            headers={**_auth(token), "Content-Type": "application/octet-stream"},
            data=payload,
            timeout=60,
        )
        print(f"[OneDrive] PUT status={resp.status_code}")
    else:
        session_url = f"{_drive_root_path(path)}:/createUploadSession"
        session_resp = requests.post(
            session_url,
            headers={**_auth(token), "Content-Type": "application/json"},
            json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
            timeout=30,
        )
        if not session_resp.ok:
            logger.warning("OneDrive: createUploadSession failed %s — %s",
                           session_resp.status_code, session_resp.text[:200])
            return None
        upload_url = session_resp.json().get("uploadUrl")
        if not upload_url:
            return None
        total = len(payload)
        resp = requests.put(
            upload_url,
            headers={
                "Content-Length": str(total),
                "Content-Range": f"bytes 0-{total - 1}/{total}",
            },
            data=payload,
            timeout=300,
        )

    if not resp.ok:
        logger.warning("OneDrive: upload failed %s — %s", resp.status_code, resp.text[:200])
        print(f"[OneDrive] upload FAILED status={resp.status_code} body={resp.text[:400]}")
        return None

    item = resp.json()
    item_id = item.get("id")
    print(f"[OneDrive] uploaded successfully, item_id={item_id}")
    if not item_id:
        print("[OneDrive] response missing 'id' — aborting")
        return None

    # Microsoft Graph on OneDrive for Business doesn't allow type=embed via
    # app-only flow ("Requested sharingLink type is not yet available"). The
    # supported path is type=view, then append `?action=embedview` to the
    # share URL to get an inline-renderable iframe src. Try anonymous first,
    # fall back to organization scope if the tenant blocks "Anyone" sharing.
    def _create_link(scope):
        return requests.post(
            f"{_drive_item_url(item_id)}/createLink",
            headers={**_auth(token), "Content-Type": "application/json"},
            json={"type": "view", "scope": scope},
            timeout=30,
        )

    print(f"[OneDrive] requesting view link for item {item_id} (scope=anonymous)")
    embed_resp = _create_link("anonymous")
    print(f"[OneDrive] createLink status={embed_resp.status_code}")
    if not embed_resp.ok:
        print(f"[OneDrive] anonymous failed body={embed_resp.text[:300]} — retrying scope=organization")
        embed_resp = _create_link("organization")
        print(f"[OneDrive] createLink (org) status={embed_resp.status_code}")

    if not embed_resp.ok:
        logger.warning("OneDrive: createLink failed %s — %s",
                       embed_resp.status_code, embed_resp.text[:200])
        print(f"[OneDrive] createLink FAILED body={embed_resp.text[:400]}")
        return None

    link = embed_resp.json().get("link", {})
    share_url = link.get("webUrl")
    print(f"[OneDrive] share_url={share_url}")
    if not share_url:
        return None

    sep = "&" if "?" in share_url else "?"
    embed_url = f"{share_url}{sep}action=embedview"
    print(f"[OneDrive] embed_url={embed_url}")

    return {
        "item_id": item_id,
        "embed_url": embed_url,
        "web_url": item.get("webUrl") or embed_url,
    }


def delete_item(user, item_id: str) -> bool:
    """Best-effort delete of a OneDrive item previously created by the LMS."""
    if not item_id or not getattr(settings, "ONEDRIVE_UPLOAD_ENABLED", False):
        return False
    token = _fetch_app_token()
    if not token:
        return False
    resp = requests.delete(_drive_item_url(item_id), headers=_auth(token), timeout=15)
    return resp.ok
