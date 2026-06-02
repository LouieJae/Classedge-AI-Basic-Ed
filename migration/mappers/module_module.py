"""Module + StudentProgress mappers with file-download support.

This is the first mapper that actually pulls media bytes from the sim. The
sim's `Module.file` payload is the relative path inside its MEDIA_ROOT
(e.g. 'module/c419...uuid.pdf'); the new side downloads via
`OldLmsClient.fetch_file_bytes` and saves into its own MEDIA_ROOT under the
same relative subdir.
"""
from migration.mappers._files import download_media as _download_into_media_root
from migration.mappers.base import MapperResult, MissingFKError, register_mapper, require_fk
from migration.models import IDMap


@register_mapper("module", "Module")
def map_module(payload: dict) -> MapperResult:
    """Modules — content blocks attached to a course (subject). Has a required
    Subject FK and a nullable Term FK. The `file` FileField is downloaded from
    sim's MEDIA_ROOT via media-blob if present.
    """
    subject_old = payload.get("subject")
    if not subject_old:
        raise MissingFKError("subject", "Subject", "(none)", field_name="subject")

    relative_file = payload.get("file") or ""
    saved_path = _download_into_media_root(relative_file) if relative_file else None

    return MapperResult(
        fields={
            "file_name": payload.get("file_name", ""),
            "file": saved_path or "",
            "iframe_code": payload.get("iframe_code"),
            "url": payload.get("url"),
            "allow_download": payload.get("allow_download", False),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
            "description": payload.get("description"),
            "order": payload.get("order", 0),
            # New-side-only fields
            "central_source_id": None,
            "onedrive_item_id": None,
            "onedrive_embed_url": None,
            "subject_id": require_fk("subject", "Subject", subject_old, field_name="subject"),
            "term_id": IDMap.resolve("course", "Term", payload.get("term")) if payload.get("term") else None,
        },
    )


@register_mapper("module", "StudentProgress")
def map_student_progress(payload: dict) -> MapperResult:
    """Per student × module / activity progress. student required, others nullable."""
    student_old = payload.get("student")
    if not student_old:
        raise MissingFKError("accounts", "CustomUser", "(none)", field_name="student")
    return MapperResult(
        fields={
            "progress": payload.get("progress", 0),
            "completed": payload.get("completed", False),
            "first_accessed": payload.get("first_accessed"),
            "last_accessed": payload.get("last_accessed"),
            "time_spent": payload.get("time_spent", 0),
            "last_page": payload.get("last_page", 0),
            "student_id": require_fk("accounts", "CustomUser", student_old, field_name="student"),
            "module_id": IDMap.resolve("module", "Module", payload.get("module")) if payload.get("module") else None,
            "activity_id": IDMap.resolve("activity", "Activity", payload.get("activity")) if payload.get("activity") else None,
        },
    )
