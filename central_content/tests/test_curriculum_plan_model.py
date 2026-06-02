from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from central_content.models import ParsedTextbook, ParsedChapter, CurriculumPlan
from central_content.tests.factories import make_editor, make_publisher, make_subject


def _fake_pdf():
    return SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf")


def _setup_textbook_with_chapters(editor, subject, num_chapters=5):
    tb = ParsedTextbook.objects.create(
        central_subject=subject,
        title="Algebra 101",
        original_file=_fake_pdf(),
        uploaded_by=editor,
        status=ParsedTextbook.Status.TOC_READY,
    )
    for i in range(1, num_chapters + 1):
        ParsedChapter.objects.create(
            textbook=tb,
            chapter_number=i,
            title=f"Chapter {i}",
            start_page=i * 10,
            end_page=i * 10 + 9,
        )
    return tb


class CurriculumPlanModelTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = _setup_textbook_with_chapters(self.editor, self.subject, num_chapters=5)

    def test_create_valid_plan(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2], "title": "Foundations", "description": "Intro"},
                {"week": 2, "chapters": [3], "title": "Middle", "description": "Core"},
                {"week": 3, "chapters": [4, 5], "title": "Advanced", "description": "End"},
            ],
            status=CurriculumPlan.Status.DRAFT,
            generated_by=self.publisher,
        )
        plan.full_clean()
        plan.save()
        self.assertEqual(plan.status, CurriculumPlan.Status.DRAFT)
        self.assertEqual(plan.textbook, self.textbook)
        self.assertEqual(len(plan.plan_data), 3)

    def test_multiple_plans_per_textbook(self):
        for model_key in ["haiku", "sonnet"]:
            CurriculumPlan.objects.create(
                textbook=self.textbook,
                school_subject_id=42,
                session_count=30,
                minutes_per_session=90,
                model_key=model_key,
                plan_data=[
                    {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                    {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
                ],
                generated_by=self.publisher,
            )
        self.assertEqual(self.textbook.plans.count(), 2)

    def test_validation_rejects_duplicate_chapters(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
                {"week": 2, "chapters": [2, 3, 4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("duplicate", str(ctx.exception).lower())

    def test_validation_rejects_missing_chapters(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("missing", str(ctx.exception).lower())

    def test_validation_rejects_nonexistent_chapters(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5, 99], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("not exist", str(ctx.exception).lower())

    def test_validation_rejects_nonsequential_weeks(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 3, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("sequential", str(ctx.exception).lower())

    def test_validation_rejects_empty_week(self):
        plan = CurriculumPlan(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3, 4, 5], "title": "A", "description": ""},
                {"week": 2, "chapters": [], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        with self.assertRaises(ValidationError) as ctx:
            plan.full_clean()
        self.assertIn("at least one chapter", str(ctx.exception).lower())

    def test_status_draft_to_approved(self):
        plan = CurriculumPlan.objects.create(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        plan.status = CurriculumPlan.Status.APPROVED
        plan.save(update_fields=["status"])
        plan.refresh_from_db()
        self.assertEqual(plan.status, CurriculumPlan.Status.APPROVED)

    def test_status_draft_to_rejected(self):
        plan = CurriculumPlan.objects.create(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        plan.status = CurriculumPlan.Status.REJECTED
        plan.save(update_fields=["status"])
        plan.refresh_from_db()
        self.assertEqual(plan.status, CurriculumPlan.Status.REJECTED)

    def test_cascade_delete_with_textbook(self):
        CurriculumPlan.objects.create(
            textbook=self.textbook,
            school_subject_id=42,
            session_count=30,
            minutes_per_session=90,
            model_key="haiku",
            plan_data=[
                {"week": 1, "chapters": [1, 2, 3], "title": "A", "description": ""},
                {"week": 2, "chapters": [4, 5], "title": "B", "description": ""},
            ],
            generated_by=self.publisher,
        )
        self.assertEqual(CurriculumPlan.objects.count(), 1)
        self.textbook.delete()
        self.assertEqual(CurriculumPlan.objects.count(), 0)
