import hashlib
import json
import os
from pathlib import Path

CACHE_DIR = Path(os.environ.get("MINERU_CACHE_DIR", "/tmp/mineru_cache"))


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _cache_path(sha: str, suffix: str) -> Path:
    return CACHE_DIR / f"{sha}_{suffix}.json"


def get_cached(sha: str, suffix: str) -> dict | None:
    path = _cache_path(sha, suffix)
    if path.exists():
        return json.loads(path.read_text())
    return None


def put_cache(sha: str, suffix: str, data: dict) -> None:
    _ensure_cache_dir()
    path = _cache_path(sha, suffix)
    path.write_text(json.dumps(data, ensure_ascii=False))
