from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from ide.judge0_client import submit_code, Judge0Error, LANGUAGE_IDS


@override_settings(JUDGE0_API_URL="http://judge0-test:2358", JUDGE0_API_KEY="test-key")
class Judge0ClientTests(TestCase):

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_success(self, mock_post):
        """Mock 200 response with status.id=3, verify stdout returned."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "stdout": "hello\n",
            "stderr": None,
            "status": {"id": 3, "description": "Accepted"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = submit_code('print("hello")', "python")

        self.assertEqual(result["stdout"], "hello\n")
        self.assertEqual(result["status"]["id"], 3)
        mock_post.assert_called_once()

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_with_stdin(self, mock_post):
        """Verify stdin is passed in the payload."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "stdout": "42\n",
            "stderr": None,
            "status": {"id": 3, "description": "Accepted"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        submit_code("x = input()", "python", stdin="42")

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1]["json"]
        self.assertEqual(payload["stdin"], "42")

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_timeout(self, mock_post):
        """Mock status.id=5 (Time Limit Exceeded), verify returned."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "stdout": None,
            "stderr": None,
            "status": {"id": 5, "description": "Time Limit Exceeded"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = submit_code("while True: pass", "python")

        self.assertEqual(result["status"]["id"], 5)
        self.assertEqual(result["status"]["description"], "Time Limit Exceeded")

    @patch("ide.judge0_client.requests.post")
    def test_submit_code_http_error(self, mock_post):
        """Mock raise_for_status raising exception, verify Judge0Error raised."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")
        mock_post.return_value = mock_resp

        with self.assertRaises(Judge0Error) as ctx:
            submit_code('print("hello")', "python")

        self.assertIn("Judge0 request failed", str(ctx.exception))

    def test_language_ids_mapping(self):
        """Verify python=71, javascript=63."""
        self.assertEqual(LANGUAGE_IDS["python"], 71)
        self.assertEqual(LANGUAGE_IDS["javascript"], 63)
