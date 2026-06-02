# central_content/tests/test_textbook_models.py
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from central_content.models import ParsedTextbook, ParsedChapter
from central_content.tests.factories import make_editor, make_subject


def _fake_pdf():
    return SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf")


class ParsedTextbookModelTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.subject = make_subject(created_by=self.editor)

    def test_create_textbook(self):
        tb = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Algebra 101",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
        )
        self.assertEqual(tb.status, ParsedTextbook.Status.UPLOADING)
        self.assertEqual(tb.central_subject, self.subject)
        self.assertEqual(tb.title, "Algebra 101")
        self.assertEqual(tb.file_hash, "")
        self.assertIsNone(tb.toc_data)
        self.assertEqual(tb.error_message, "")

    def test_multiple_textbooks_per_subject(self):
        for i in range(3):
            ParsedTextbook.objects.create(
                central_subject=self.subject,
                title=f"Book {i}",
                original_file=_fake_pdf(),
                uploaded_by=self.editor,
            )
        self.assertEqual(self.subject.textbooks.count(), 3)

    def test_cascade_delete(self):
        tb = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Cascade Book",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
        )
        ParsedChapter.objects.create(
            textbook=tb, chapter_number=1, title="Ch1",
            start_page=1, end_page=10,
        )
        ParsedChapter.objects.create(
            textbook=tb, chapter_number=2, title="Ch2",
            start_page=11, end_page=20,
        )
        self.assertEqual(ParsedChapter.objects.count(), 2)
        tb.delete()
        self.assertEqual(ParsedChapter.objects.count(), 0)


class ParsedChapterModelTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = ParsedTextbook.objects.create(
            central_subject=self.subject,
            title="Chapter Test Book",
            original_file=_fake_pdf(),
            uploaded_by=self.editor,
        )

    def test_create_chapter(self):
        ch = ParsedChapter.objects.create(
            textbook=self.textbook,
            chapter_number=1,
            title="Real Numbers",
            start_page=1,
            end_page=30,
        )
        self.assertEqual(ch.status, ParsedChapter.Status.PENDING)
        self.assertIsNone(ch.parsed_data)
        self.assertEqual(ch.error_message, "")

    def test_chapters_ordered_by_number(self):
        for num in [3, 1, 2]:
            ParsedChapter.objects.create(
                textbook=self.textbook,
                chapter_number=num,
                title=f"Chapter {num}",
                start_page=num * 10,
                end_page=num * 10 + 9,
            )
        chapters = list(self.textbook.chapters.all())
        self.assertEqual([c.chapter_number for c in chapters], [1, 2, 3])

    def test_status_transitions(self):
        ch = ParsedChapter.objects.create(
            textbook=self.textbook,
            chapter_number=1,
            title="Transitions",
            start_page=1,
            end_page=10,
        )
        self.assertEqual(ch.status, ParsedChapter.Status.PENDING)

        ch.status = ParsedChapter.Status.PARSING
        ch.save(update_fields=["status"])
        ch.refresh_from_db()
        self.assertEqual(ch.status, ParsedChapter.Status.PARSING)

        ch.status = ParsedChapter.Status.COMPLETE
        ch.save(update_fields=["status"])
        ch.refresh_from_db()
        self.assertEqual(ch.status, ParsedChapter.Status.COMPLETE)
