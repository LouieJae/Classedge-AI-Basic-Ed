import re
import traceback as tb_module
from pathlib import Path
from typing import Any

from django.conf import settings

from migration.models import MigrationErrorRecord, MigrationJob, MigrationRunLog


_SECRET_KEY_RE = re.compile(r"(password|token|secret|api[_-]?key)", re.IGNORECASE)
_BASE_DIR = Path(settings.BASE_DIR).resolve()


def _is_project_frame(filename: str) -> bool:
    try:
        path = Path(filename).resolve()
    except (OSError, RuntimeError):
        return False
    try:
        path.relative_to(_BASE_DIR)
    except ValueError:
        return False
    parts = path.parts
    # Exclude vendored packages even when inside BASE_DIR
    for excluded in ("site-packages", ".venv", "env"):
        if excluded in parts:
            return False
    return True


def _innermost_project_frame(tb: tb_module.TracebackException):
    frames = list(tb.stack)
    for frame in reversed(frames):
        if _is_project_frame(frame.filename):
            return frame
    return frames[-1] if frames else None


def _redact(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if _SECRET_KEY_RE.search(str(k)):
            out[k] = "***"
        else:
            out[k] = v
    return out


def capture(
    *,
    job: MigrationJob,
    category: str,
    exc: BaseException,
    payload: dict | None = None,
    field: str = "",
    expected: str = "",
    actual: str = "",
    old_pk: str = "",
    batch_cursor: str = "",
    batch_index: int | None = None,
    run_log: MigrationRunLog | None = None,
) -> MigrationErrorRecord:
    tb = tb_module.TracebackException.from_exception(exc)
    frame = _innermost_project_frame(tb)
    return MigrationErrorRecord.objects.create(
        job=job,
        run_log=run_log,
        category=category,
        message=str(exc)[:500],
        field=field[:120],
        expected=expected[:500],
        actual=actual[:500],
        old_pk=str(old_pk)[:64],
        batch_cursor=str(batch_cursor)[:128],
        batch_index=batch_index,
        source_file=(frame.filename if frame else "")[:255],
        source_line=(frame.lineno if frame else None),
        source_function=(frame.name if frame else "")[:120],
        traceback=("".join(tb.format()))[:20000],
        old_app=job.app_label,
        old_model=job.model_name,
        payload_excerpt=_redact(payload or {}),
    )
