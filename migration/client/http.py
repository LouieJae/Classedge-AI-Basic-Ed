import time

import requests
from django.conf import settings

from .exceptions import AuthError, PermanentError, ThrottledError, TransientError


class OldLmsClient:
    def __init__(self, base_url: str | None = None, token: str | None = None,
                 timeout: int | None = None, max_retries: int | None = None,
                 backoff_base: float = 1.0):
        if base_url is None or token is None:
            db_base, db_token = self._load_db_overrides()
            base_url = base_url or db_base or settings.MIGRATION_OLD_LMS_BASE_URL
            token = token or db_token or settings.MIGRATION_OLD_LMS_TOKEN
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout if timeout is not None else settings.MIGRATION_HTTP_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.MIGRATION_MAX_RETRIES
        self.backoff_base = backoff_base
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Token {self.token}"

    @staticmethod
    def _load_db_overrides() -> tuple[str, str]:
        """Best-effort load of DB overrides. Returns ("", "") if unavailable
        (e.g. during migrations or before the table exists)."""
        try:
            from migration.models import MigrationSettings
            row = MigrationSettings.objects.filter(pk=1).first()
            if row is None:
                return ("", "")
            return (row.base_url or "", row.token or "")
        except Exception:
            return ("", "")

    def health(self) -> dict:
        return self._get("/api/migration/health/")

    def fetch_page(self, app: str, model: str, cursor: str | None = None, limit: int = 500) -> dict:
        # Sim routes use lowercase model names (Django's default DRF URL
        # registration). Our DEPENDENCY_ORDER stores the canonical class
        # name (e.g. "Module"), so we lowercase here at the request boundary.
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._get(f"/api/migration/{app}/{model.lower()}/", params=params)

    def fetch_by_pk(self, app: str, model: str, old_pk) -> dict:
        return self._get(f"/api/migration/{app}/{model.lower()}/{old_pk}/")

    def fetch_file_bytes(self, relative_path: str) -> bytes | None:
        """Download a media file from the sim's MEDIA_ROOT via the token-authed
        blob endpoint. Returns the raw bytes, or None on 404 / missing path.

        Retries on 429 (honoring Retry-After) and 5xx with exponential backoff,
        matching `_get`. 4xx other than 404/401/403/429 is permanent.
        """
        if not relative_path:
            return None
        url = f"{self.base_url}/api/migration/media-blob/"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params={"path": relative_path}, timeout=self.timeout * 2)
            except requests.RequestException as exc:
                last_exc = exc
                self._sleep(attempt)
                continue
            status = resp.status_code
            if 200 <= status < 300:
                return resp.content
            if status == 404:
                return None
            if status in (401, 403):
                raise AuthError(f"{status} on media-blob")
            if status == 429:
                retry_after = float(resp.headers.get("Retry-After", "1") or 1)
                last_exc = ThrottledError("429 on media-blob", retry_after=retry_after)
                time.sleep(max(retry_after, self.backoff_base * (2 ** attempt)))
                continue
            if 400 <= status < 500:
                raise PermanentError(f"{status} on media-blob")
            # 5xx — retry
            last_exc = TransientError(f"{status} on media-blob")
            self._sleep(attempt)
        # Exhausted retries — return None so the FileField is left empty rather
        # than poisoning the whole row. The error capture log will show the 429s.
        return None

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_exc = exc
                self._sleep(attempt)
                continue
            status = resp.status_code
            if 200 <= status < 300:
                return resp.json()
            if status in (401, 403):
                raise AuthError(f"{status} from old LMS")
            if status == 429:
                retry_after = float(resp.headers.get("Retry-After", "1") or 1)
                raise ThrottledError("429 from old LMS", retry_after=retry_after)
            if 400 <= status < 500:
                raise PermanentError(f"{status} {resp.text[:200]}")
            # 5xx — retry
            last_exc = TransientError(f"{status} {resp.text[:200]}")
            self._sleep(attempt)
        raise TransientError(f"Exhausted retries: {last_exc}") from last_exc

    def _sleep(self, attempt: int) -> None:
        time.sleep(self.backoff_base * (2 ** attempt))
