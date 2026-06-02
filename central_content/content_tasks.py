from celery import shared_task
from django.db import transaction

from central_content.llm import call_content_generator
from central_content.tasks import parse_single_chapter


_MAX_CHAPTER_TEXT_LENGTH = 4000


def _extract_chapter_text(parsed_data):
    if not parsed_data:
        return ""
    if isinstance(parsed_data, dict):
        return str(parsed_data.get("text", ""))[:_MAX_CHAPTER_TEXT_LENGTH]
    return str(parsed_data)[:_MAX_CHAPTER_TEXT_LENGTH]


@shared_task
def generate_week_content(job_id, week_index):
    from activity.models.activity_model import ActivityType
    from central_content.models import (
        CentralActivity, CentralModule, ContentGenerationJob, ParsedChapter,
    )

    job = ContentGenerationJob.objects.select_related(
        "curriculum_plan__textbook__central_subject",
        "triggered_by",
    ).get(pk=job_id)

    plan = job.curriculum_plan
    textbook = plan.textbook
    subject = textbook.central_subject
    week_entry = plan.plan_data[week_index]
    week_num = week_entry["week"]
    week_title = week_entry.get("title", f"Week {week_num}")
    week_desc = week_entry.get("description", "")

    chapter_texts = []
    for ch_num in week_entry["chapters"]:
        try:
            chapter = textbook.chapters.get(chapter_number=ch_num)
        except ParsedChapter.DoesNotExist:
            _mark_week_failed(job, week_index, f"Chapter {ch_num} not found")
            return

        if chapter.parsed_data is None and chapter.status == ParsedChapter.Status.PENDING:
            parse_single_chapter.apply(args=[chapter.pk])
            chapter.refresh_from_db()

        if chapter.parsed_data is None:
            _mark_week_failed(
                job, week_index,
                f"Chapter {ch_num} parse failed (status: {chapter.status})",
            )
            return

        chapter_texts.append({
            "number": chapter.chapter_number,
            "title": chapter.title,
            "text": _extract_chapter_text(chapter.parsed_data),
        })

    try:
        result = call_content_generator(
            chapter_texts=chapter_texts,
            week_title=week_title,
            week_description=week_desc,
            session_count=plan.session_count,
            minutes_per_session=plan.minutes_per_session,
            model_key=job.model_key,
        )
    except (ValueError, Exception) as exc:
        _mark_week_failed(job, week_index, f"LLM error: {exc}")
        return

    quiz_type = ActivityType.objects.filter(name="Quiz").first()
    if not quiz_type:
        _mark_week_failed(job, week_index, "ActivityType 'Quiz' not found")
        return

    with transaction.atomic():
        module = CentralModule.objects.create(
            central_subject=subject,
            file_name=f"Week {week_num}: {week_title}",
            description=result["lesson_description"],
            order=week_num,
            state=CentralModule.State.DRAFT,
            created_by=job.triggered_by,
        )
        activity = CentralActivity.objects.create(
            central_subject=subject,
            activity_name=f"Week {week_num} Quiz: {week_title}",
            activity_instruction=result["quiz_questions"],
            activity_type=quiz_type,
            max_score=100,
            time_duration=30,
            passing_score=75,
            passing_score_type=CentralActivity.PassingScoreType.PERCENTAGE,
            max_retake=1,
            retake_method=CentralActivity.RetakeMethod.HIGHEST,
            shuffle_questions=True,
            is_graded=True,
            state=CentralActivity.State.DRAFT,
            created_by=job.triggered_by,
        )
        activity.related_modules.add(module)

    job.refresh_from_db()
    job.week_results[week_index] = {
        "week": week_num,
        "status": "done",
        "module_id": module.pk,
        "activity_id": activity.pk,
    }
    job.completed_weeks += 1
    job.save(update_fields=["week_results", "completed_weeks", "updated_at"])


def _mark_week_failed(job, week_index, error_msg):
    job.refresh_from_db()
    week_num = job.curriculum_plan.plan_data[week_index]["week"]
    job.week_results[week_index] = {
        "week": week_num,
        "status": "failed",
        "error": error_msg,
    }
    job.failed_weeks += 1
    job.save(update_fields=["week_results", "failed_weeks", "updated_at"])


@shared_task
def run_content_generation(job_id):
    from central_content.models import ContentGenerationJob

    job = ContentGenerationJob.objects.get(pk=job_id)
    job.status = ContentGenerationJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])

    for week_index in range(job.total_weeks):
        generate_week_content(job_id, week_index)

    job.refresh_from_db()
    if job.failed_weeks == job.total_weeks:
        job.status = ContentGenerationJob.Status.FAILED
    else:
        job.status = ContentGenerationJob.Status.COMPLETE
    job.save(update_fields=["status", "updated_at"])
