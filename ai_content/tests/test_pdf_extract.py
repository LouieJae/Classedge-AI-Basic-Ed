import io

import fitz
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ai_content.pdf_extract import extract_text_from_pdf


def _make_test_pdf(text="Hello, this is test content for extraction."):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return SimpleUploadedFile("test.pdf", pdf_bytes, content_type="application/pdf")


class ExtractTextFromPdfTests(TestCase):
    def test_extracts_text_from_valid_pdf(self):
        pdf_file = _make_test_pdf("Hello, this is a test.")
        result = extract_text_from_pdf(pdf_file)
        self.assertIn("Hello", result)
        self.assertIn("test", result)

    def test_returns_empty_string_for_invalid_file(self):
        bad_file = SimpleUploadedFile("bad.pdf", b"not a pdf", content_type="application/pdf")
        result = extract_text_from_pdf(bad_file)
        self.assertEqual(result, "")

    def test_truncates_long_text(self):
        long_text = "A" * 10000
        pdf_file = _make_test_pdf(long_text)
        result = extract_text_from_pdf(pdf_file)
        self.assertLessEqual(len(result), 8000)

    def test_returns_empty_string_for_none(self):
        result = extract_text_from_pdf(None)
        self.assertEqual(result, "")
