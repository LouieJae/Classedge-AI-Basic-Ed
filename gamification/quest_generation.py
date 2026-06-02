"""[Classedge LMS] Background-thread quest generation job runner."""
import threading
from django.utils import timezone
from django.db import transaction
from gamification.ai_providers import get_provider
from gamification.lesson_text import extract_text
from gamification.quest_models import Quest, QuestGenerationJob
from gamification.quest_schema import validate_quest_set, QuestSchemaError
from gamification.quest_settings_models import OrganizationQuestSettings


def start_generation(module) -> QuestGenerationJob:
    """Create job + spawn worker thread. Returns job (status='queued')."""
    existing = QuestGenerationJob.objects.filter(module=module, status__in=["queued", "running"]).exists()
    if existing:
        raise RuntimeError("A generation job is already running for this module.")
    job = QuestGenerationJob.objects.create(module=module)
    t = threading.Thread(target=run_generation_job, args=(job.id,), daemon=True)
    t.start()
    return job


def run_generation_job(job_id: int) -> None:
    """Synchronous body of the worker thread (also directly callable in tests)."""
    job = QuestGenerationJob.objects.select_related("module__subject").get(pk=job_id)
    job.status = "running"
    job.save(update_fields=["status"])
    try:
        n = job.module.subject.quest_count_per_lesson
        text = extract_text(job.module.file)
        provider = get_provider()
        provider_name = OrganizationQuestSettings.load().ai_provider
        try:
            data = provider.generate(text, n)
            validate_quest_set(data, expected_n=n)
        except QuestSchemaError as first_err:
            data = provider.generate(
                text + f"\n\nPrevious output invalid: {first_err}. Return valid JSON only.",
                n,
            )
            validate_quest_set(data, expected_n=n)

        with transaction.atomic():
            Quest.objects.filter(module=job.module, status="draft").delete()
            for i, q in enumerate(data["quests"], start=1):
                Quest.objects.create(
                    module=job.module, order=i, kind=q["kind"], title=q["title"],
                    body=q["body"], payload=q["payload"], status="draft",
                    ai_provider=provider_name, source_chunk=q.get("source_chunk", ""),
                )
        job.status = "complete"
    except Exception as e:
        job.status = "failed"
        job.error = str(e)[:2000]
    finally:
        job.finished_at = timezone.now()
        job.save()
