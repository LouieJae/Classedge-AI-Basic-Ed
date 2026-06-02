from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from central_content.models import ContentGenerationJob, CurriculumPlan
from central_content.tests.factories import (
    make_editor, make_publisher, make_subject, make_textbook,
    make_curriculum_plan,
)


class ContentGenerationJobModelTests(TestCase):
    def setUp(self):
        self.editor = make_editor()
        self.publisher = make_publisher()
        self.subject = make_subject(created_by=self.editor)
        self.textbook = make_textbook(
            central_subject=self.subject,
            uploaded_by=self.editor,
            num_chapters=5,
        )
        self.plan = make_curriculum_plan(
            textbook=self.textbook,
            generated_by=self.publisher,
        )

    def test_create_job(self):
        job = ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=[
                {"week": 1, "status": "pending"},
                {"week": 2, "status": "pending"},
            ],
            triggered_by=self.publisher,
        )
        self.assertEqual(job.status, ContentGenerationJob.Status.PENDING)
        self.assertEqual(job.completed_weeks, 0)
        self.assertEqual(job.failed_weeks, 0)
        self.assertEqual(job.total_weeks, 2)
        self.assertEqual(len(job.week_results), 2)

    def test_cascade_delete_with_plan(self):
        ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=[],
            triggered_by=self.publisher,
        )
        self.assertEqual(ContentGenerationJob.objects.count(), 1)
        self.plan.delete()
        self.assertEqual(ContentGenerationJob.objects.count(), 0)

    def test_multiple_jobs_per_plan(self):
        for key in ["haiku", "sonnet"]:
            ContentGenerationJob.objects.create(
                curriculum_plan=self.plan,
                model_key=key,
                total_weeks=2,
                week_results=[],
                triggered_by=self.publisher,
            )
        self.assertEqual(self.plan.generation_jobs.count(), 2)

    def test_week_results_stores_and_retrieves(self):
        results = [
            {"week": 1, "status": "done", "module_id": 10, "activity_id": 20},
            {"week": 2, "status": "failed", "error": "parse failed"},
        ]
        job = ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=results,
            triggered_by=self.publisher,
        )
        job.refresh_from_db()
        self.assertEqual(job.week_results[0]["module_id"], 10)
        self.assertEqual(job.week_results[1]["error"], "parse failed")

    def test_status_choices(self):
        job = ContentGenerationJob.objects.create(
            curriculum_plan=self.plan,
            model_key="haiku",
            total_weeks=2,
            week_results=[],
            triggered_by=self.publisher,
        )
        for status_val in ["pending", "running", "complete", "failed"]:
            job.status = status_val
            job.save(update_fields=["status"])
            job.refresh_from_db()
            self.assertEqual(job.status, status_val)
