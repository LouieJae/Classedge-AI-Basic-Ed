import io
from django.test import TestCase
from gamification.lesson_text import extract_text, UnsupportedFileType, EmptyContent


class LessonTextTests(TestCase):
    def test_txt_passthrough(self):
        f = io.BytesIO(b"Hello world. " * 30)
        f.name = "x.txt"
        self.assertIn("Hello world", extract_text(f))

    def test_unsupported_raises(self):
        f = io.BytesIO(b"xx"); f.name = "x.exe"
        with self.assertRaises(UnsupportedFileType):
            extract_text(f)

    def test_empty_raises(self):
        f = io.BytesIO(b"a"); f.name = "x.txt"
        with self.assertRaises(EmptyContent):
            extract_text(f)
