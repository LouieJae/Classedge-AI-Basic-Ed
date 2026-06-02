"""Shared media-file download helper for mappers.

Pulls bytes from the sim's MEDIA_ROOT via the token-authed media-blob endpoint
and saves them under the new side's MEDIA_ROOT preserving the relative path.
Returns the relative path string (suitable for assigning to a FileField), or
None when the source path is empty / the sim has no such file.

Idempotent: re-runs short-circuit if a non-empty file already exists locally.
"""
from pathlib import Path

from django.conf import settings

from migration.client.http import OldLmsClient


def _files_enabled() -> bool:
    """Master switch for media-blob downloads during migration. Set
    MIGRATION_DOWNLOAD_FILES=false in env to skip every file download — row
    data still migrates, FileFields stay empty, and the job finishes in
    minutes instead of hours. Re-run with the flag on to backfill files."""
    return getattr(settings, "MIGRATION_DOWNLOAD_FILES", True)


_client_cache: OldLmsClient | None = None


def _client() -> OldLmsClient:
    global _client_cache
    if _client_cache is None:
        _client_cache = OldLmsClient()
    return _client_cache


def download_media(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    if not _files_enabled():
        return None
    media_root = Path(settings.MEDIA_ROOT)
    target = media_root / relative_path

    if target.is_file() and target.stat().st_size > 0:
        return relative_path

    target.parent.mkdir(parents=True, exist_ok=True)
    blob = _client().fetch_file_bytes(relative_path)
    if blob is None:
        return None

    tmp = target.with_suffix(target.suffix + ".partial")
    tmp.write_bytes(blob)
    tmp.replace(target)
    return relative_path
