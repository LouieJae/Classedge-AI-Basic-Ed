"""[Classedge LMS] Tests for subject access authorization."""
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from gradebookcomponent.services.access import authorize_subject_access
from gradebookcomponent.tests.helpers import make_user, make_subject


class AuthorizeSubjectAccessTest(TestCase):
    """[Classedge LMS] Verifies owner/collaborator/other-teacher access rules."""

    def test_owner_allowed(self):
        """[Classedge LMS] The assigned teacher is always permitted."""
        teacher = make_user("owner@t.local", "Teacher")
        subject = make_subject(teacher)
        authorize_subject_access(teacher, subject)  # should not raise

    def test_collaborator_allowed(self):
        """[Classedge LMS] A teacher added as collaborator is permitted."""
        owner = make_user("owner@t.local", "Teacher")
        collab = make_user("collab@t.local", "Teacher")
        subject = make_subject(owner)
        subject.collaborators.add(collab)
        authorize_subject_access(collab, subject)  # should not raise

    def test_other_teacher_denied(self):
        """[Classedge LMS] A teacher with no relation to the subject is denied."""
        owner = make_user("owner@t.local", "Teacher")
        other = make_user("other@t.local", "Teacher")
        subject = make_subject(owner)
        with self.assertRaises(PermissionDenied):
            authorize_subject_access(other, subject)
