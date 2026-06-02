# central_content/state_machine.py
"""State machine transitions for central content records.

Each transition is a function taking the record and the acting CentralStaff.
Success mutates the record (in DB) and writes one AuditLogEntry.
Failures raise IllegalTransition or UnresolvedChildren — no partial writes.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from central_content.models import (
    AuditLogEntry,
    CentralActivity,
    CentralModule,
    CentralStaff,
    CentralSubject,
)


class IllegalTransition(Exception):
    """Raised when a transition is not allowed for the current state or role."""


class UnresolvedChildren(Exception):
    """Raised when approving a subject that still has non-approved children."""

    def __init__(self, subject, blocking):
        self.subject = subject
        self.blocking = list(blocking)
        names = ", ".join(str(b) for b in self.blocking[:5])
        super().__init__(
            f"Cannot approve {subject}: {len(self.blocking)} child(ren) "
            f"still draft or in_review ({names}...)"
        )


_DRAFT = "draft"
_IN_REVIEW = "in_review"
_APPROVED = "approved"

_SUBMIT_ROLES = {CentralStaff.Role.EDITOR, CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER}
_REVIEW_ROLES = {CentralStaff.Role.REVIEWER, CentralStaff.Role.PUBLISHER}
_REOPEN_ROLES = {CentralStaff.Role.PUBLISHER}


def _log(record, actor, from_state, to_state, notes=""):
    AuditLogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(type(record)),
        object_id=record.id,
        from_state=from_state,
        to_state=to_state,
        actor=actor,
        notes=notes,
    )


def _require_role(actor, allowed, action):
    if actor.role not in allowed:
        raise IllegalTransition(
            f"Role '{actor.role}' cannot perform action '{action}'"
        )


def _require_state(record, allowed, action):
    if record.state not in allowed:
        raise IllegalTransition(
            f"Cannot {action} from state '{record.state}'"
        )


@transaction.atomic
def submit_for_review(record, actor):
    _require_role(actor, _SUBMIT_ROLES, "submit")
    _require_state(record, {_DRAFT}, "submit")
    record.state = _IN_REVIEW
    if isinstance(record, CentralSubject):
        record.submitted_by = actor
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _DRAFT, _IN_REVIEW)


@transaction.atomic
def approve(record, actor):
    _require_role(actor, _REVIEW_ROLES, "approve")
    _require_state(record, {_IN_REVIEW}, "approve")

    if isinstance(record, CentralSubject):
        blocking = list(record.modules.exclude(state=_APPROVED)) + \
                   list(record.activities.exclude(state=_APPROVED))
        if blocking:
            raise UnresolvedChildren(record, blocking)

    record.state = _APPROVED
    record.reviewed_by = actor
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _IN_REVIEW, _APPROVED)


@transaction.atomic
def request_changes(record, actor, notes=""):
    _require_role(actor, _REVIEW_ROLES, "request_changes")
    _require_state(record, {_IN_REVIEW}, "request_changes")
    record.state = _DRAFT
    record.reviewed_by = actor
    record.review_notes = notes
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _IN_REVIEW, _DRAFT, notes=notes)


@transaction.atomic
def reopen(record, actor):
    _require_role(actor, _REOPEN_ROLES, "reopen")
    _require_state(record, {_APPROVED}, "reopen")
    record.state = _DRAFT
    if isinstance(record, CentralSubject):
        record.version += 1
        record.modules.update(state=_DRAFT)
        record.activities.update(state=_DRAFT)
    record.save(update_fields=_save_fields(record))
    _log(record, actor, _APPROVED, _DRAFT)


def _save_fields(record):
    """Return the minimal update_fields for a transition save."""
    fields = ["state", "updated_at"]
    if isinstance(record, CentralSubject):
        fields += ["submitted_by", "reviewed_by", "review_notes", "version"]
    elif isinstance(record, (CentralModule, CentralActivity)):
        fields += ["reviewed_by", "review_notes"]
    return fields
