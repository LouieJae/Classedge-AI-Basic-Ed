# central_content/tests/test_textbook_tasks.py
from unittest.mock import MagicMock, patch

import requests
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from central_content.models import ParsedTextbook, ParsedChapter
from central_content.tasks import parse_textbook_toc, parse_single_chapter
from central_content.tests.factories import make_editor, make_subject


def _fake_pdf():
    return SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf")


_MOCK_TOC = {
    "title": "Algebra Textbook",
    "total_pages": 100,
    "chapters": [
        {"number": 1, "title": "Real Numbers", "start_page": 1, "end_page": 30},
        {"number": 2, "title": "Expressions", "start_page": 31, "end_page": 60},
        {"number": 3, "title": "Equations", "start_page": 61, "end_page": 100},
    ],
}

_TASK_SETTINGS = dict(
    MINERU_SERVICE_URL="http://fake:8765",
    MINERU_TOC_TIMEOUT=10,
    MINERU_CHAPTER_TIMEOUT=10,
)


@override_settings(**_TASK_SETTINGS)
class ParseTextbookTocTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Test Book",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
        )

    @patch("central_content.tasks.requests.post")
    def test_success_creates_chapters(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _MOCK_TOC
        mock_post.return_value = mock_resp

        result = parse_textbook_toc(self.textbook.pk)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["chapters"], 3)
        self.assertEqual(ParsedChapter.objects.filter(textbook=self.textbook).count(), 3)
        self.textbook.refresh_from_db()
        self.assertEqual(self.textbook.status, ParsedTextbook.Status.TOC_READY)

    @patch("central_content.tasks.requests.post")
    def test_failure_sets_status(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        result = parse_textbook_toc(self.textbook.pk)

        self.assertEqual(result["status"], "error")
        self.textbook.refresh_from_db()
        self.assertEqual(self.textbook.status, ParsedTextbook.Status.FAILED)

    @patch("central_content.tasks.requests.post")
    def test_connection_error_retries(self, mock_post):
        mock_post.side_effect = requests.ConnectionError("refused")

        with self.assertRaises(requests.ConnectionError):
            parse_textbook_toc(self.textbook.pk)

        self.textbook.refresh_from_db()
        self.assertEqual(self.textbook.status, ParsedTextbook.Status.FAILED)

    def test_nonexistent_textbook(self):
        result = parse_textbook_toc(999999)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["detail"], "textbook_not_found")

    @patch("central_content.tasks.requests.post")
    def test_reparsing_replaces_chapters(self, mock_post):
        # Pre-create old chapters
        ParsedChapter.objects.create(
            textbook=self.textbook, chapter_number=99, title="Old",
            start_page=1, end_page=5,
        )
        self.assertEqual(ParsedChapter.objects.filter(textbook=self.textbook).count(), 1)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _MOCK_TOC
        mock_post.return_value = mock_resp

        parse_textbook_toc(self.textbook.pk)

        chapters = list(
            ParsedChapter.objects.filter(textbook=self.textbook)
            .values_list("chapter_number", flat=True)
        )
        self.assertEqual(sorted(chapters), [1, 2, 3])
        self.assertNotIn(99, chapters)


@override_settings(**_TASK_SETTINGS)
class ParseSingleChapterTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Chapter Task Book",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
        )
        self.chapter = ParsedChapter.objects.create(
            textbook=self.textbook,
            chapter_number=1,
            title="Real Numbers",
            start_page=1,
            end_page=30,
        )

    @patch("central_content.tasks.requests.post")
    def test_chapter_parse_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": "parsed markdown"}
        mock_post.return_value = mock_resp

        result = parse_single_chapter(self.chapter.pk)

        self.assertEqual(result["status"], "success")
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, ParsedChapter.Status.COMPLETE)
        self.assertEqual(self.chapter.parsed_data, {"content": "parsed markdown"})

    @patch("central_content.tasks.requests.post")
    def test_chapter_parse_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Server Error"
        mock_post.return_value = mock_resp

        result = parse_single_chapter(self.chapter.pk)

        self.assertEqual(result["status"], "error")
        self.chapter.refresh_from_db()
        self.assertEqual(self.chapter.status, ParsedChapter.Status.FAILED)

    def test_nonexistent_chapter(self):
        result = parse_single_chapter(999999)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["detail"], "chapter_not_found")
