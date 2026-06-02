from dataclasses import dataclass, field
from typing import Callable

from migration.models import IDMap


@dataclass
class MapperResult:
    fields: dict
    fk_resolutions: list[tuple] = field(default_factory=list)
    m2m_resolutions: dict[str, list[tuple]] = field(default_factory=dict)
    # Fields applied via a post-save UPDATE statement (bypasses auto_now_add,
    # auto_now, and signals). Used for migrating values into fields Django would
    # otherwise overwrite — e.g. ScoreChangeLog.change_date, RetakeRecord.retake_time.
    post_save_updates: dict = field(default_factory=dict)
    # Optional target override: write the row to a different (app_label, model_name)
    # than the source. Used when the source model has no destination on the new side
    # — e.g. logs.UserActivityLog (dropped) archives into migration.LegacyAuditLog.
    # IDMap is still keyed by the SOURCE identifier so re-runs stay idempotent.
    target_app: str | None = None
    target_model: str | None = None
    # Natural-key lookup: if IDMap has no entry for this source row, the writer
    # uses these field=value pairs to find a pre-existing target row (e.g. one
    # created manually before migration) and adopts it instead of inserting a
    # duplicate. Seeds IDMap on adoption so subsequent runs stay idempotent.
    natural_key: dict | None = None
    # Field names to skip during full_clean(). Use for fields whose model
    # definition is stricter than the legacy data — e.g. TextField() without
    # blank=True on rows that arrive blank from the sim.
    clean_exclude: list[str] = field(default_factory=list)
    skip: bool = False
    skip_reason: str = ""


class MissingFKError(Exception):
    def __init__(self, target_app: str, target_model: str, old_pk: str, field_name: str = ""):
        self.target_app = target_app
        self.target_model = target_model
        self.old_pk = str(old_pk)
        self.field_name = field_name
        super().__init__(
            f"IDMap miss: {target_app}.{target_model} old_pk={old_pk}"
            + (f" (field {field_name})" if field_name else "")
        )


def require_fk(target_app: str, target_model: str, old_pk, *, field_name: str = "") -> str:
    new_pk = IDMap.resolve(target_app, target_model, old_pk)
    if new_pk is None:
        raise MissingFKError(target_app, target_model, old_pk, field_name=field_name)
    return new_pk


_REGISTRY: dict[tuple[str, str], Callable] = {}


def register_mapper(app_label: str, model_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[(app_label, model_name)] = fn
        return fn
    return decorator


def get_mapper(app_label: str, model_name: str) -> Callable:
    try:
        return _REGISTRY[(app_label, model_name)]
    except KeyError as e:
        raise KeyError(f"No mapper registered for {app_label}.{model_name}") from e


def all_mappers() -> dict[tuple[str, str], Callable]:
    return dict(_REGISTRY)
