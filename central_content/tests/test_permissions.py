# central_content/tests/test_permissions.py
from django.http import HttpRequest, HttpResponse
from django.test import TestCase

from central_content.permissions import central_role_required, IsCentralStaff
from central_content.models import CentralStaff
from central_content.tests.factories import (
    make_editor, make_reviewer, make_publisher,
)


class RoleDecoratorTests(TestCase):
    def _request_for(self, user):
        req = HttpRequest()
        req.user = user
        return req

    def test_allows_matching_role(self):
        @central_role_required(CentralStaff.Role.PUBLISHER)
        def view(request):
            return HttpResponse("ok")

        resp = view(self._request_for(make_publisher()))
        self.assertEqual(resp.status_code, 200)

    def test_rejects_other_role(self):
        @central_role_required(CentralStaff.Role.PUBLISHER)
        def view(request):
            return HttpResponse("ok")

        resp = view(self._request_for(make_editor()))
        self.assertEqual(resp.status_code, 403)

    def test_rejects_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        @central_role_required(CentralStaff.Role.EDITOR)
        def view(request):
            return HttpResponse("ok")

        req = HttpRequest()
        req.user = AnonymousUser()
        resp = view(req)
        self.assertEqual(resp.status_code, 302)  # redirect to login

    def test_multiple_roles_allowed(self):
        @central_role_required(
            CentralStaff.Role.REVIEWER,
            CentralStaff.Role.PUBLISHER,
        )
        def view(request):
            return HttpResponse("ok")

        self.assertEqual(view(self._request_for(make_reviewer())).status_code, 200)
        self.assertEqual(view(self._request_for(make_publisher())).status_code, 200)
        self.assertEqual(view(self._request_for(make_editor())).status_code, 403)


class IsCentralStaffTests(TestCase):
    def test_rejects_non_central_staff(self):
        from django.contrib.auth.models import AnonymousUser
        req = HttpRequest()
        req.user = AnonymousUser()
        perm = IsCentralStaff()
        self.assertFalse(perm.has_permission(req, None))

    def test_accepts_central_staff(self):
        req = HttpRequest()
        req.user = make_editor()
        perm = IsCentralStaff()
        self.assertTrue(perm.has_permission(req, None))
