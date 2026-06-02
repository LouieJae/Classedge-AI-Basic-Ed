import json
from typing import Any

import requests
from django.db import transaction
from django.utils import timezone


PUSH_TIMEOUT_SECONDS = 60


def build_push_payload(central_subject) -> tuple[dict[str, Any], dict[str, Any]]:
    files: dict[str, Any] = {}

    modules = list(central_subject.modules.order_by("order", "pk"))
    activities = list(central_subject.activities.prefetch_related("related_modules"))

    module_payloads = []
    for i, m in enumerate(modules):
        entry = {
            "central_id": m.pk,
            "file_name": m.file_name,
            "description": m.description,
            "order": m.order,
            "url": m.url,
            "iframe_code": m.iframe_code,
        }
        if m.file:
            key = f"module_{i}_file"
            entry["file_part"] = key
            files[key] = m.file.open("rb")
        module_payloads.append(entry)

    activity_payloads = []
    for a in activities:
        activity_payloads.append({
            "central_id": a.pk,
            "activity_name": a.activity_name,
            "activity_instruction": a.activity_instruction,
            "activity_type": a.activity_type.name,
            "max_score": a.max_score,
            "time_duration": a.time_duration,
            "passing_score": a.passing_score,
            "passing_score_type": a.passing_score_type,
            "max_retake": a.max_retake,
            "retake_method": a.retake_method,
            "shuffle_questions": a.shuffle_questions,
            "is_graded": a.is_graded,
            "related_module_central_ids": [
                rm.pk for rm in a.related_modules.all()
            ],
        })

    payload: dict[str, Any] = {
        "central_id": central_subject.pk,
        "central_version": central_subject.version,
        "subject_name": central_subject.subject_name,
        "subject_descriptive_title": central_subject.subject_descriptive_title,
        "subject_short_name": central_subject.subject_short_name,
        "subject_description": central_subject.subject_description,
        "subject_code": central_subject.subject_code,
        "subject_type": central_subject.subject_type,
        "unit": central_subject.unit,
        "target_grade_level": central_subject.target_grade_level,
        "target_curriculum": central_subject.target_curriculum,
        "target_sdgs": [sdg.name for sdg in central_subject.target_sdgs.all()],
        "modules": module_payloads,
        "activities": activity_payloads,
    }

    if central_subject.subject_photo:
        payload["subject_photo_part"] = "subject_photo"
        files["subject_photo"] = central_subject.subject_photo.open("rb")

    return payload, files


def push_subject_to_school(binding, triggered_by):
    from central_content.models import PushJob

    payload, files = build_push_payload(binding.central_subject)
    payload["target_subject_id"] = binding.school_subject_id
    data = {"payload": json.dumps(payload)}
    files_for_requests = {k: (getattr(f, "name", k), f) for k, f in files.items()}

    url = binding.target_school.base_url.rstrip("/") + "/api/central/ingest/"
    headers = {"Authorization": f"Bearer {binding.target_school.api_token}"}

    http_status = None
    response_body = ""
    error_message = ""
    try:
        resp = requests.post(
            url, data=data, files=files_for_requests,
            headers=headers, timeout=PUSH_TIMEOUT_SECONDS,
        )
        http_status = resp.status_code
        response_body = (resp.text or "")[:10000]
    except requests.RequestException as e:
        error_message = str(e)[:10000]
    finally:
        for f in files.values():
            try:
                f.close()
            except Exception:
                pass

    with transaction.atomic():
        if http_status is not None and 200 <= http_status < 300:
            binding.pushed_version = binding.central_subject.version
            binding.last_pushed_at = timezone.now()
            binding.save(update_fields=["pushed_version", "last_pushed_at"])
            status = PushJob.Status.SUCCESS
        else:
            status = PushJob.Status.FAILED

        job = PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind=PushJob.Kind.PUSH,
            status=status,
            subject_version=binding.central_subject.version,
            http_status=http_status,
            response_body=response_body,
            error_message=error_message,
            finished_at=timezone.now(),
            triggered_by=triggered_by,
        )

    return job


def delete_subject_from_school(binding, triggered_by):
    from central_content.models import PushJob

    url = (
        binding.target_school.base_url.rstrip("/")
        + f"/api/central/ingest/{binding.central_subject_id}/"
    )
    headers = {"Authorization": f"Bearer {binding.target_school.api_token}"}

    http_status = None
    response_body = ""
    error_message = ""
    try:
        resp = requests.delete(url, headers=headers, timeout=PUSH_TIMEOUT_SECONDS)
        http_status = resp.status_code
        response_body = (resp.text or "")[:10000]
    except requests.RequestException as e:
        error_message = str(e)[:10000]

    success = http_status is not None and (
        200 <= http_status < 300 or http_status == 404
    )
    with transaction.atomic():
        job = PushJob.objects.create(
            central_subject=binding.central_subject,
            target_school=binding.target_school,
            kind=PushJob.Kind.DELETE,
            status=PushJob.Status.SUCCESS if success else PushJob.Status.FAILED,
            subject_version=binding.central_subject.version,
            http_status=http_status,
            response_body=response_body,
            error_message=error_message,
            finished_at=timezone.now(),
            triggered_by=triggered_by,
        )
    return job
