from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from received_central_content.auth import require_central_token


@override_settings(CENTRAL_INGEST_TOKEN="correct-token-value")
class RequireCentralTokenTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        @require_central_token
        def view(request):
            return HttpResponse("ok")

        self.view = view

    def test_missing_header_returns_401(self):
        req = self.factory.get("/api/central/subjects/")
        resp = self.view(req)
        self.assertEqual(resp.status_code, 401)

    def test_wrong_token_returns_401(self):
        req = self.factory.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer wrong",
        )
        resp = self.view(req)
        self.assertEqual(resp.status_code, 401)

    def test_correct_token_returns_200(self):
        req = self.factory.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer correct-token-value",
        )
        resp = self.view(req)
        self.assertEqual(resp.status_code, 200)

    @override_settings(CENTRAL_INGEST_TOKEN="")
    def test_empty_server_token_always_401(self):
        req = self.factory.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer ",
        )
        resp = self.view(req)
        self.assertEqual(resp.status_code, 401)
