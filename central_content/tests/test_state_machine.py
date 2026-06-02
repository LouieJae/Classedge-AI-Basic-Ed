# central_content/tests/test_state_machine.py
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from central_content.models import (
    AuditLogEntry,
    CentralModule,
    CentralSubject,
)
from central_content.state_machine import (
    IllegalTransition,
    UnresolvedChildren,
    submit_for_review,
    approve,
    request_changes,
    reopen,
)
from central_content.tests.factories import (
    make_editor,
    make_reviewer,
    make_publisher,
    make_subject,
    make_module,
)


class SubjectStateMachineTests(TestCase):
    def test_submit_sets_in_review_and_logs(self):
        editor = make_editor()
        subj = make_subject(created_by=editor)
        submit_for_review(subj, actor=editor)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "in_review")
        self.assertEqual(subj.submitted_by, editor)
        ct = ContentType.objects.get_for_model(CentralSubject)
        entry = AuditLogEntry.objects.get(content_type=ct, object_id=subj.id)
        self.assertEqual((entry.from_state, entry.to_state), ("draft", "in_review"))

    def test_cannot_submit_non_draft(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        with self.assertRaises(IllegalTransition):
            submit_for_review(subj, actor=reviewer)

    def test_approve_requires_all_children_approved(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        make_module(central_subject=subj, state=CentralModule.State.DRAFT)
        with self.assertRaises(UnresolvedChildren):
            approve(subj, actor=reviewer)

    def test_approve_succeeds_when_children_approved(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        make_module(central_subject=subj, state=CentralModule.State.APPROVED)
        approve(subj, actor=reviewer)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "approved")
        self.assertEqual(subj.reviewed_by, reviewer)

    def test_request_changes_returns_to_draft_with_notes(self):
        reviewer = make_reviewer()
        subj = make_subject(state=CentralSubject.State.IN_REVIEW)
        request_changes(subj, actor=reviewer, notes="fix typos")
        subj.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.review_notes, "fix typos")

    def test_reopen_bumps_version_and_reverts_children(self):
        publisher = make_publisher()
        subj = make_subject(state=CentralSubject.State.APPROVED)
        child = make_module(central_subject=subj, state=CentralModule.State.APPROVED)
        original_version = subj.version
        reopen(subj, actor=publisher)
        subj.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.version, original_version + 1)
        self.assertEqual(child.state, "draft")

    def test_illegal_reopen_by_editor(self):
        editor = make_editor()
        subj = make_subject(state=CentralSubject.State.APPROVED)
        with self.assertRaises(IllegalTransition):
            reopen(subj, actor=editor)


class ModuleStateMachineTests(TestCase):
    def test_module_submit_approve_cycle(self):
        editor = make_editor()
        reviewer = make_reviewer()
        m = make_module(created_by=editor)
        submit_for_review(m, actor=editor)
        m.refresh_from_db()
        self.assertEqual(m.state, "in_review")
        approve(m, actor=reviewer)
        m.refresh_from_db()
        self.assertEqual(m.state, "approved")
        self.assertEqual(m.reviewed_by, reviewer)
