"""Project-wide HTTP helpers.

All classic (non-DRF) views should return responses via these helpers so that
error shape and key casing match what DRF endpoints emit. DRF views get the
same behavior automatically via the camel-case renderer and
drf-standardized-errors' exception handler.
"""
from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from django.http import HttpRequest, JsonResponse
from djangorestframework_camel_case.util import camelize, underscoreize


_ERROR_TYPE_BY_STATUS = {
    400: "validation_error",
    401: "client_error",
    403: "client_error",
    404: "client_error",
    405: "client_error",
    409: "client_error",
    415: "client_error",
    429: "client_error",
}


def camel_json_response(data: Any, status: int = 200, **kwargs) -> JsonResponse:
    """Return a JsonResponse whose keys are camelCased on the wire."""
    if isinstance(data, dict):
        return JsonResponse(camelize(data), status=status, **kwargs)
    if isinstance(data, list):
        return JsonResponse(camelize(data), status=status, safe=False, **kwargs)
    return JsonResponse(data, status=status, safe=False, **kwargs)


def standardized_error_response(
    *,
    code: str,
    detail: str,
    status: int,
    attr: str | None = None,
    type_: str | None = None,
    extra_errors: Iterable[Mapping[str, Any]] = (),
) -> JsonResponse:
    """Return a JsonResponse matching drf-standardized-errors' shape.

    {
      "type": "validation_error" | "client_error" | "server_error",
      "errors": [ { "code": "...", "detail": "...", "attr": "fieldOrNull" }, ... ]
    }
    """
    resolved_type = type_ or _ERROR_TYPE_BY_STATUS.get(
        status, "server_error" if status >= 500 else "client_error"
    )
    errors: list[dict[str, Any]] = [{"code": code, "detail": detail, "attr": attr}]
    errors.extend(dict(e) for e in extra_errors)
    return JsonResponse({"type": resolved_type, "errors": errors}, status=status)


def parse_camel_json(request: HttpRequest) -> dict:
    """Decode request.body as JSON and convert camelCase keys to snake_case.

    Classic views use this so Python code can keep reading snake_case keys
    even though clients send camelCase.
    """
    body = request.body or b"{}"
    return underscoreize(json.loads(body))
