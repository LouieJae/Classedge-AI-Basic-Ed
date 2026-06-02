from celery import shared_task
from django.db import transaction

from ai_content.llm import call_school_content_generator
from ai_content.pdf_extract import extract_text_from_pdf


@shared_task
def generate_school_content(request_id):
    from activity.models.activity_model import Activity, ActivityType
    from module.models.module import Module
    from ai_content.models import GenerationRequest

    try:
        req = GenerationRequest.objects.select_related(
            "subject", "term", "requested_by",
        ).get(pk=request_id)
    except GenerationRequest.DoesNotExist:
        return {"status": "error", "detail": "request_not_found"}

    req.status = GenerationRequest.Status.RUNNING
    req.save(update_fields=["status", "updated_at"])

    if req.reference_file and not req.reference_text:
        req.reference_text = extract_text_from_pdf(req.reference_file)
        req.save(update_fields=["reference_text", "updated_at"])

    try:
        result = call_school_content_generator(
            topic=req.topic,
            objectives=req.objectives,
            content_type=req.content_type,
            reference_text=req.reference_text,
            model_key=req.model_key,
        )
    except (ValueError, Exception) as exc:
        req.status = GenerationRequest.Status.FAILED
        req.error_message = str(exc)[:2000]
        req.save(update_fields=["status", "error_message", "updated_at"])
        return {"status": "error", "detail": str(exc)[:500]}

    module = None
    activity = None

    with transaction.atomic():
        if req.content_type in ("module", "both"):
            module = Module.objects.create(
                file_name=req.topic,
                description=result["lesson_description"],
                subject=req.subject,
                term=req.term,
            )

        if req.content_type in ("quiz", "both"):
            quiz_type = ActivityType.objects.filter(name="Quiz").first()
            if not quiz_type:
                req.status = GenerationRequest.Status.FAILED
                req.error_message = "ActivityType 'Quiz' not found"
                req.save(update_fields=["status", "error_message", "updated_at"])
                return {"status": "error", "detail": "quiz_type_not_found"}

            activity = Activity.objects.create(
                activity_name=f"{req.topic} Quiz",
                activity_instruction=result["quiz_questions"],
                activity_type=quiz_type,
                subject=req.subject,
                term=req.term,
                max_score=100,
                time_duration=30,
                passing_score=75,
                passing_score_type="percentage",
                max_retake=1,
                retake_method="highest",
                shuffle_questions=True,
                is_graded=True,
            )

            if module:
                activity.additional_modules.add(module)

    req.generated_module_id = module.pk if module else None
    req.generated_activity_id = activity.pk if activity else None
    req.status = GenerationRequest.Status.COMPLETE
    req.save(update_fields=[
        "generated_module_id", "generated_activity_id", "status", "updated_at",
    ])

    return {"status": "success", "request_id": req.pk}
