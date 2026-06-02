import hashlib

import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction

from central_content.llm import call_curriculum_planner


@shared_task(bind=True, max_retries=3)
def parse_textbook_toc(self, textbook_id):
    from central_content.models import ParsedTextbook, ParsedChapter

    try:
        textbook = ParsedTextbook.objects.get(pk=textbook_id)
    except ParsedTextbook.DoesNotExist:
        return {"status": "error", "detail": "textbook_not_found"}

    file_bytes = textbook.original_file.read()
    textbook.file_hash = hashlib.sha256(file_bytes).hexdigest()
    textbook.status = ParsedTextbook.Status.PARSING_TOC
    textbook.save(update_fields=["file_hash", "status"])

    try:
        textbook.original_file.seek(0)
        resp = requests.post(
            f"{settings.MINERU_SERVICE_URL}/parse/toc",
            files={"file": (textbook.original_file.name, file_bytes, "application/pdf")},
            timeout=settings.MINERU_TOC_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ValueError(f"MinerU returned {resp.status_code}: {resp.text[:500]}")

        toc = resp.json()

        with transaction.atomic():
            textbook.toc_data = toc
            textbook.title = textbook.title or toc.get("title", "Untitled")
            textbook.status = ParsedTextbook.Status.TOC_READY
            textbook.error_message = ""
            textbook.save(update_fields=[
                "toc_data", "title", "status", "error_message",
            ])

            ParsedChapter.objects.filter(textbook=textbook).delete()
            for ch in toc.get("chapters", []):
                ParsedChapter.objects.create(
                    textbook=textbook,
                    chapter_number=ch["number"],
                    title=ch["title"],
                    start_page=ch["start_page"],
                    end_page=ch["end_page"],
                )

        return {"status": "success", "chapters": len(toc.get("chapters", []))}

    except requests.RequestException as exc:
        textbook.status = ParsedTextbook.Status.FAILED
        textbook.error_message = f"Connection error: {exc}"
        textbook.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    except Exception as exc:
        textbook.status = ParsedTextbook.Status.FAILED
        textbook.error_message = str(exc)[:2000]
        textbook.save(update_fields=["status", "error_message"])
        return {"status": "error", "detail": str(exc)[:500]}


@shared_task(bind=True, max_retries=3)
def parse_single_chapter(self, chapter_id):
    from central_content.models import ParsedChapter

    try:
        chapter = ParsedChapter.objects.select_related("textbook").get(pk=chapter_id)
    except ParsedChapter.DoesNotExist:
        return {"status": "error", "detail": "chapter_not_found"}

    chapter.status = ParsedChapter.Status.PARSING
    chapter.save(update_fields=["status"])

    try:
        file_bytes = chapter.textbook.original_file.read()
        chapter.textbook.original_file.seek(0)

        resp = requests.post(
            f"{settings.MINERU_SERVICE_URL}/parse/chapter",
            files={"file": ("textbook.pdf", file_bytes, "application/pdf")},
            data={
                "start_page": chapter.start_page,
                "end_page": chapter.end_page,
            },
            timeout=settings.MINERU_CHAPTER_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ValueError(f"MinerU returned {resp.status_code}: {resp.text[:500]}")

        chapter.parsed_data = resp.json()
        chapter.status = ParsedChapter.Status.COMPLETE
        chapter.error_message = ""
        chapter.save(update_fields=["parsed_data", "status", "error_message"])

        return {"status": "success", "chapter": chapter.chapter_number}

    except requests.RequestException as exc:
        chapter.status = ParsedChapter.Status.FAILED
        chapter.error_message = f"Connection error: {exc}"
        chapter.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

    except Exception as exc:
        chapter.status = ParsedChapter.Status.FAILED
        chapter.error_message = str(exc)[:2000]
        chapter.save(update_fields=["status", "error_message"])
        return {"status": "error", "detail": str(exc)[:500]}


@shared_task
def generate_curriculum_plan(textbook_id, binding_id, model_key, triggered_by_id):
    from central_content.models import (
        CentralStaff, CurriculumPlan, ParsedTextbook, SchoolSubjectBinding,
    )

    try:
        textbook = ParsedTextbook.objects.get(pk=textbook_id)
        binding = SchoolSubjectBinding.objects.select_related("target_school").get(pk=binding_id)
        triggered_by = CentralStaff.objects.get(pk=triggered_by_id)
    except (ParsedTextbook.DoesNotExist, SchoolSubjectBinding.DoesNotExist, CentralStaff.DoesNotExist) as exc:
        return {"status": "error", "detail": str(exc)}

    schedule_url = (
        f"{binding.target_school.base_url}/api/central/schedule/{binding.school_subject_id}/"
    )
    try:
        resp = requests.get(
            schedule_url,
            headers={"Authorization": f"Bearer {binding.target_school.api_token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return {"status": "error", "detail": f"Schedule fetch failed ({resp.status_code}): {resp.text[:500]}"}
        schedule_data = resp.json()
    except requests.RequestException as exc:
        return {"status": "error", "detail": f"Schedule fetch error: {exc}"}

    chapters = [
        {
            "number": ch.chapter_number,
            "title": ch.title,
            "start_page": ch.start_page,
            "end_page": ch.end_page,
        }
        for ch in textbook.chapters.all()
    ]

    session_count = schedule_data["session_count"]
    minutes_per_session = schedule_data["minutes_per_session"]

    plan_data = None
    for attempt in range(2):
        try:
            plan_data = call_curriculum_planner(
                chapters=chapters,
                session_count=session_count,
                minutes_per_session=minutes_per_session,
                model_key=model_key,
            )
        except (ValueError, Exception) as exc:
            if attempt == 1:
                return {"status": "error", "detail": f"LLM error: {exc}"}
            continue

        try:
            test_plan = CurriculumPlan(
                textbook=textbook,
                school_subject_id=binding.school_subject_id,
                session_count=session_count,
                minutes_per_session=minutes_per_session,
                model_key=model_key,
                plan_data=plan_data,
                generated_by=triggered_by,
            )
            test_plan._validate_plan_data()
            break
        except Exception:
            if attempt == 1:
                break
            continue

    if plan_data is None:
        return {"status": "error", "detail": "LLM failed to produce a plan"}

    plan = CurriculumPlan.objects.create(
        textbook=textbook,
        school_subject_id=binding.school_subject_id,
        session_count=session_count,
        minutes_per_session=minutes_per_session,
        model_key=model_key,
        plan_data=plan_data,
        generated_by=triggered_by,
    )

    return {"status": "success", "plan_id": plan.pk}


@shared_task
def bulk_generate_plans(central_subject_id, binding_id, model_key, triggered_by_id):
    from central_content.models import CentralSubject, ParsedTextbook

    try:
        subject = CentralSubject.objects.get(pk=central_subject_id)
    except CentralSubject.DoesNotExist:
        return {"status": "error", "detail": "subject_not_found"}

    textbooks = subject.textbooks.filter(status=ParsedTextbook.Status.TOC_READY)
    count = 0
    for tb in textbooks:
        generate_curriculum_plan.delay(tb.pk, binding_id, model_key, triggered_by_id)
        count += 1

    return {"status": "success", "dispatched": count}
