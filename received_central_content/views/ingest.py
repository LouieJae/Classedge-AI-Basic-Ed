import json

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from activity.models.activity_model import ActivityType
from received_central_content.auth import require_central_token
from received_central_content.models import ReceivedCentralSubject
from subject.models.sdg_models import SDG


def _err(code, error, **extra):
    payload = {"error": error}
    payload.update(extra)
    return JsonResponse(payload, status=code)


def _resolve_sdgs(names):
    if not names:
        return [], []
    rows = list(SDG.objects.filter(name__in=names))
    found = {r.name for r in rows}
    missing = [n for n in names if n not in found]
    return rows, missing


def _resolve_activity_types(names):
    unique = list(set(names))
    rows = list(ActivityType.objects.filter(name__in=unique))
    by_name = {r.name: r for r in rows}
    missing = [n for n in unique if n not in by_name]
    return by_name, missing


@csrf_exempt
@require_http_methods(["POST"])
@require_central_token
def ingest_subject(request):
    raw_payload = request.POST.get("payload")
    if not raw_payload:
        return _err(400, "missing_payload")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return _err(400, "invalid_json")

    central_id = payload.get("central_id")
    central_version = payload.get("central_version")
    target_subject_id = payload.get("target_subject_id")

    if central_id is None or central_version is None:
        return _err(400, "missing_required_fields")
    if target_subject_id is None:
        return _err(400, "missing_target_subject_id")

    from subject.models.subject_model import Subject
    try:
        target_subject = Subject.objects.get(pk=target_subject_id)
    except Subject.DoesNotExist:
        return _err(404, "target_subject_not_found")

    sdg_rows, missing_sdgs = _resolve_sdgs(payload.get("target_sdgs") or [])
    if missing_sdgs:
        return _err(422, "unresolved_sdgs", names=missing_sdgs)

    activity_type_names = [
        a["activity_type"] for a in payload.get("activities") or []
    ]
    at_by_name, missing_ats = _resolve_activity_types(activity_type_names)
    if missing_ats:
        return _err(422, "unresolved_activity_types", names=missing_ats)

    try:
        with transaction.atomic():
            from activity.models.activity_model import Activity as NativeActivity
            from module.models.module import Module as NativeModule

            received_subject, _created = ReceivedCentralSubject.objects.update_or_create(
                central_id=central_id,
                defaults={
                    "central_version": central_version,
                    "subject_name": payload.get("subject_name", ""),
                    "subject_descriptive_title": payload.get("subject_descriptive_title", ""),
                    "subject_short_name": payload.get("subject_short_name", ""),
                    "subject_description": payload.get("subject_description", ""),
                    "subject_code": payload.get("subject_code", ""),
                    "subject_type": payload.get("subject_type", ""),
                    "unit": payload.get("unit", 3),
                    "target_grade_level": payload.get("target_grade_level", ""),
                    "target_curriculum": payload.get("target_curriculum", ""),
                },
            )
            received_subject.target_sdgs.set(sdg_rows)

            subject_photo_part = payload.get("subject_photo_part")
            if subject_photo_part:
                f = request.FILES.get(subject_photo_part)
                if not f:
                    raise ValueError("missing_file_part:subject_photo")
                received_subject.subject_photo.save(f.name, f, save=True)

            NativeActivity.objects.filter(
                subject=target_subject,
                central_source_id=central_id,
            ).delete()
            NativeModule.objects.filter(
                subject=target_subject,
                central_source_id=central_id,
            ).delete()

            module_payloads = payload.get("modules") or []
            native_module_by_central_id = {}
            for m in module_payloads:
                mod = NativeModule(
                    subject=target_subject,
                    file_name=m.get("file_name", ""),
                    description=m.get("description", ""),
                    url=m.get("url", ""),
                    iframe_code=m.get("iframe_code", ""),
                    order=m.get("order", 0),
                    central_source_id=central_id,
                )
                mod.save()
                file_part = m.get("file_part")
                if file_part:
                    f = request.FILES.get(file_part)
                    if not f:
                        raise ValueError(f"missing_file_part:{file_part}")
                    mod.file.save(f.name, f, save=True)
                native_module_by_central_id[m["central_id"]] = mod

            activity_payloads = payload.get("activities") or []
            for a in activity_payloads:
                act = NativeActivity(
                    subject=target_subject,
                    activity_name=a.get("activity_name", ""),
                    activity_instruction=a.get("activity_instruction", ""),
                    activity_type=at_by_name[a["activity_type"]],
                    max_score=a.get("max_score", 100),
                    time_duration=a.get("time_duration", 0),
                    passing_score=a.get("passing_score", 0),
                    passing_score_type=a.get("passing_score_type", "percentage"),
                    max_retake=a.get("max_retake", 0),
                    retake_method=a.get("retake_method", "highest"),
                    shuffle_questions=a.get("shuffle_questions", False),
                    is_graded=a.get("is_graded", True),
                    central_source_id=central_id,
                )
                act.save()
                related_ids = a.get("related_module_central_ids") or []
                unknown = [cid for cid in related_ids if cid not in native_module_by_central_id]
                if unknown:
                    raise ValueError(f"unresolved_related_modules:{unknown}")
                act.additional_modules.set(
                    [native_module_by_central_id[cid] for cid in related_ids]
                )

    except ValueError as e:
        message = str(e)
        if message.startswith("unresolved_related_modules:"):
            return _err(422, "unresolved_related_modules", detail=message)
        if message.startswith("missing_file_part:"):
            return _err(400, "missing_file_part", detail=message.split(":", 1)[1])
        return _err(500, "server_error", detail=message)

    return JsonResponse(
        {
            "received_subject_id": received_subject.pk,
            "central_version": received_subject.central_version,
            "received_at": timezone.now().isoformat(),
        },
        status=200,
    )


@csrf_exempt
@require_http_methods(["DELETE"])
@require_central_token
def delete_subject(request, central_id: int):
    from activity.models.activity_model import Activity as NativeActivity
    from module.models.module import Module as NativeModule

    try:
        subject = ReceivedCentralSubject.objects.get(central_id=central_id)
    except ReceivedCentralSubject.DoesNotExist:
        return _err(404, "not_found")

    NativeActivity.objects.filter(central_source_id=central_id).delete()
    NativeModule.objects.filter(central_source_id=central_id).delete()
    subject.delete()

    return JsonResponse({}, status=204)
