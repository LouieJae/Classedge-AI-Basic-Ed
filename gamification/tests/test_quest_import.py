import json
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from module.models.module import Module
from subject.models import Subject
from gamification.quest_models import Quest
from gamification.quest_import import import_quests, ImportError as QuestImportError


CSV_OK = (
    'kind,title,body,payload_json,counts_toward_grade\n'
    'quiz,"Q1","b","{""options"":[""a"",""b"",""c"",""d""],""correct_index"":0}",true\n'
    'task,"T1","do it","{""rubric"":""r"",""self_check"":true}",false\n'
)


class ImportTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(subject_name="S")
        self.module = Module.objects.create(file_name="L", subject=self.subject)

    def test_csv_happy_path(self):
        f = SimpleUploadedFile("q.csv", CSV_OK.encode("utf-8"))
        n = import_quests(self.module, f)
        self.assertEqual(n, 2)
        self.assertEqual(Quest.objects.filter(module=self.module).count(), 2)
        self.assertFalse(Quest.objects.get(title="T1").counts_toward_grade)

    def test_json_happy_path(self):
        items = [{"kind": "quiz", "title": "JQ", "body": "b",
                  "payload": {"options": ["a", "b", "c", "d"], "correct_index": 0}}]
        f = SimpleUploadedFile("q.json", json.dumps(items).encode("utf-8"))
        n = import_quests(self.module, f)
        self.assertEqual(n, 1)

    def test_malformed_rejects_all(self):
        bad = CSV_OK + 'quiz,"badrow","b","NOT-JSON",true\n'
        f = SimpleUploadedFile("q.csv", bad.encode("utf-8"))
        with self.assertRaises(QuestImportError):
            import_quests(self.module, f)
        self.assertEqual(Quest.objects.filter(module=self.module).count(), 0)

    def test_oversize_rejected(self):
        big = SimpleUploadedFile("q.csv", b"x" * (2 * 1024 * 1024))
        with self.assertRaises(QuestImportError):
            import_quests(self.module, big)
