# central_content/tests/test_views_subjects.py
from django.test import TestCase, override_settings

from central_content.models import CentralSubject
from central_content.tests.factories import (
    make_editor, make_reviewer, make_publisher,
    make_subject, make_module, make_activity,
)

_SAFE_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

_OVERRIDES = dict(
    ROOT_URLCONF="central_content.urls",
    AUTHENTICATION_BACKENDS=["central_content.auth_backends.CentralStaffAuthBackend"],
    TEMPLATES=_SAFE_TEMPLATES,
)


@override_settings(**_OVERRIDES)
class SubjectListViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.client.post("/login", {"email": "ed@example.com", "password": "pw"})

    def test_list_requires_login(self):
        self.client.post("/logout")
        resp = self.client.get("/subjects/")
        self.assertEqual(resp.status_code, 302)

    def test_list_shows_subjects(self):
        make_subject(subject_name="Grade 7 Math", created_by=self.editor)
        make_subject(subject_name="Grade 8 Science", created_by=self.editor)
        resp = self.client.get("/subjects/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Grade 7 Math")
        self.assertContains(resp, "Grade 8 Science")

    def test_list_filter_by_state(self):
        make_subject(subject_name="A", created_by=self.editor,
                     state=CentralSubject.State.DRAFT)
        make_subject(subject_name="B", created_by=self.editor,
                     state=CentralSubject.State.APPROVED)
        resp = self.client.get("/subjects/?state=approved")
        self.assertContains(resp, "B")
        self.assertNotContains(resp, ">A<")


@override_settings(**_OVERRIDES)
class SubjectDetailViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.client.post("/login", {"email": "ed@example.com", "password": "pw"})

    def test_detail_shows_children(self):
        subj = make_subject(subject_name="X", created_by=self.editor)
        make_module(central_subject=subj, created_by=self.editor,
                    file_name="Lesson One")
        make_activity(central_subject=subj, created_by=self.editor,
                      activity_name="Quiz One")
        resp = self.client.get(f"/subjects/{subj.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "X")
        self.assertContains(resp, "Lesson One")
        self.assertContains(resp, "Quiz One")

    def test_detail_404(self):
        resp = self.client.get("/subjects/99999/")
        self.assertEqual(resp.status_code, 404)


@override_settings(**_OVERRIDES)
class SubjectCreateEditTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.client.post("/login", {"email": "ed@example.com", "password": "pw"})

    def test_create_form_renders(self):
        resp = self.client.get("/subjects/new")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Subject name")

    def test_create_submits(self):
        resp = self.client.post("/subjects/new", {
            "subject_name": "New Subject",
            "target_grade_level": "Grade 7",
            "target_curriculum": "K-12",
            "subject_description": "desc",
            "unit": "3",
        })
        self.assertEqual(resp.status_code, 302)
        s = CentralSubject.objects.get(subject_name="New Subject")
        self.assertEqual(s.state, "draft")
        self.assertEqual(s.created_by, self.editor)

    def test_edit_blocked_when_not_draft(self):
        subj = make_subject(state=CentralSubject.State.APPROVED,
                            created_by=self.editor)
        resp = self.client.get(f"/subjects/{subj.id}/edit")
        self.assertEqual(resp.status_code, 400)

    def test_edit_persists(self):
        subj = make_subject(subject_name="Old", created_by=self.editor)
        self.client.post(f"/subjects/{subj.id}/edit", {
            "subject_name": "New",
            "target_grade_level": subj.target_grade_level,
            "target_curriculum": subj.target_curriculum,
            "subject_description": "d",
            "unit": "3",
        })
        subj.refresh_from_db()
        self.assertEqual(subj.subject_name, "New")


@override_settings(**_OVERRIDES)
class SubjectTransitionViewTests(TestCase):
    def setUp(self):
        self.editor = make_editor(email="ed@example.com", password="pw")
        self.reviewer = make_reviewer(email="rev@example.com", password="pw")
        self.publisher = make_publisher(email="pub@example.com", password="pw")

    def _login(self, email):
        self.client.post("/login", {"email": email, "password": "pw"})

    def test_submit_moves_to_in_review(self):
        self._login("ed@example.com")
        subj = make_subject(created_by=self.editor)
        resp = self.client.post(f"/subjects/{subj.id}/submit")
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "in_review")

    def test_approve_by_editor_forbidden(self):
        self._login("ed@example.com")
        subj = make_subject(state=CentralSubject.State.IN_REVIEW,
                            created_by=self.editor)
        resp = self.client.post(f"/subjects/{subj.id}/approve")
        self.assertEqual(resp.status_code, 403)

    def test_approve_by_reviewer(self):
        self._login("rev@example.com")
        subj = make_subject(state=CentralSubject.State.IN_REVIEW,
                            created_by=self.editor)
        resp = self.client.post(f"/subjects/{subj.id}/approve")
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "approved")

    def test_request_changes_by_reviewer(self):
        self._login("rev@example.com")
        subj = make_subject(state=CentralSubject.State.IN_REVIEW,
                            created_by=self.editor)
        resp = self.client.post(
            f"/subjects/{subj.id}/request-changes",
            {"notes": "please fix"},
        )
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.review_notes, "please fix")

    def test_reopen_publisher_only(self):
        subj = make_subject(state=CentralSubject.State.APPROVED,
                            created_by=self.editor)
        self._login("rev@example.com")
        resp = self.client.post(f"/subjects/{subj.id}/reopen")
        self.assertEqual(resp.status_code, 403)

        self._login("pub@example.com")
        resp = self.client.post(f"/subjects/{subj.id}/reopen")
        self.assertEqual(resp.status_code, 302)
        subj.refresh_from_db()
        self.assertEqual(subj.state, "draft")
        self.assertEqual(subj.version, 2)
