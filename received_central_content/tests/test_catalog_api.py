from django.test import TestCase, override_settings, Client

from received_central_content.tests.test_native_ingest import _create_subject


@override_settings(CENTRAL_INGEST_TOKEN="t" * 40, ROOT_URLCONF="lms.urls", ALLOWED_HOSTS=["*"])
class CatalogAPITests(TestCase):
    def setUp(self):
        _create_subject(subject_name="Math 101", subject_code="MATH101")
        _create_subject(subject_name="Geometry", subject_code="MATH201")
        self.client = Client()

    def test_no_token_returns_401(self):
        resp = self.client.get("/api/central/subjects/")
        self.assertEqual(resp.status_code, 401)

    def test_wrong_token_returns_401(self):
        resp = self.client.get(
            "/api/central/subjects/", HTTP_AUTHORIZATION="Bearer wrong",
        )
        self.assertEqual(resp.status_code, 401)

    def test_list_subjects(self):
        resp = self.client.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        names = {row["subject_name"] for row in data}
        self.assertEqual(names, {"Math 101", "Geometry"})
        self.assertIn("id", data[0])
        self.assertIn("subject_code", data[0])

    def test_ordered_by_name(self):
        resp = self.client.get(
            "/api/central/subjects/",
            HTTP_AUTHORIZATION="Bearer " + "t" * 40,
        )
        names = [row["subject_name"] for row in resp.json()]
        self.assertEqual(names, sorted(names))
