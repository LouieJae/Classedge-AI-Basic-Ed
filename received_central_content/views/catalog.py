from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from received_central_content.auth import require_central_token
from subject.models.subject_model import Subject


@require_http_methods(["GET"])
@require_central_token
def list_subjects(request):
    rows = Subject.objects.order_by("subject_name").values(
        "id", "subject_name", "subject_code",
    )
    return JsonResponse(list(rows), safe=False)
