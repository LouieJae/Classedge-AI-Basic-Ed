import json
import os

from rest_framework import serializers

from activity.models import (
    RetakeRecord,
    RetakeRecordDetail,
    StudentActivity,
    Activity,
    ActivityQuestion,
)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_UPLOAD_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".pdf", ".txt", ".csv",
}
ALLOWED_UPLOAD_MIMETYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp",
    "application/pdf", "text/plain", "text/csv",
}


def _validate_uploaded_file(f):
    if f is None:
        return f
    size = getattr(f, "size", None)
    if size is not None and size > MAX_UPLOAD_BYTES:
        raise serializers.ValidationError(
            f"File too large ({size} bytes). Max allowed is {MAX_UPLOAD_BYTES} bytes (10 MB)."
        )
    name = getattr(f, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    ctype = (getattr(f, "content_type", "") or "").lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS or (
        ctype and ctype not in ALLOWED_UPLOAD_MIMETYPES
    ):
        raise serializers.ValidationError(
            f"Unsupported file type (ext={ext!r}, content_type={ctype!r}). "
            f"Allowed: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}."
        )
    return f


def _coerce_question_order(value):
    """Recursively json.loads a string until it's a list (or give up)."""
    seen = 0
    while isinstance(value, str) and seen < 5:
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return value
        seen += 1
    return value


def _platform_from_context(context):
    request = context.get("request") if context else None
    if request is None:
        return ""
    return (request.headers.get("X-Platform", "") or "").strip().lower()


def _maybe_drop_local_id(validated_data, context):
    """Honor a client-supplied local_id only when X-Platform: mobile.
    Other callers (web, missing header, spoofed value) get the server cuid.
    """
    incoming = validated_data.get("local_id")
    if _platform_from_context(context) != "mobile" or not incoming:
        validated_data.pop("local_id", None)


class RetakeRecordDetailSerializer(serializers.ModelSerializer):
    local_id = serializers.CharField(required=False, allow_blank=True, max_length=36)
    retake_record_id = serializers.PrimaryKeyRelatedField(
        source="retake_record", queryset=RetakeRecord.objects.all(), write_only=True
    )
    activity_question_id = serializers.PrimaryKeyRelatedField(
        source="activity_question",
        queryset=ActivityQuestion.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = RetakeRecordDetail
        fields = [
            "local_id",
            "retake_record_id",
            "activity_question_id",
            "student_answer",
            "score",
            "uploaded_file",
        ]

    def validate_uploaded_file(self, value):
        return _validate_uploaded_file(value)

    def create(self, validated_data):
        _maybe_drop_local_id(validated_data, self.context)
        return super().create(validated_data)

    def to_internal_value(self, data):
        if data.get("uploaded_file") in ("", None):
            try:
                data = data.copy()
            except Exception:
                data = dict(data)
            data.pop("uploaded_file", None)
        return super().to_internal_value(data)


class RetakeRecordSerializer(serializers.ModelSerializer):
    student_activity_id = serializers.PrimaryKeyRelatedField(
        source="student_activity",
        queryset=StudentActivity.objects.all(),
        write_only=True,
    )
    activity_id = serializers.PrimaryKeyRelatedField(
        source="activity", queryset=Activity.objects.all(), write_only=True
    )
    local_id = serializers.CharField(required=False, allow_blank=True, max_length=36)

    class Meta:
        model = RetakeRecord
        fields = [
            "student_activity_id",
            "student",
            "retake_number",
            "score",
            "duration",
            "status",
            "started_at",
            "will_end_at",
            "local_id",
            "activity_id",
            "question_order",
            "last_index",
            "last_heartbeat_at",
            "total_elapsed_seconds",
        ]

    def create(self, validated_data):
        _maybe_drop_local_id(validated_data, self.context)
        return super().create(validated_data)

    def to_internal_value(self, data):
        if "question_order" in data:
            coerced = _coerce_question_order(data.get("question_order"))
            try:
                data = data.copy()
            except Exception:
                data = dict(data)
            data["question_order"] = coerced
        return super().to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["question_order"] = _coerce_question_order(rep.get("question_order"))
        return rep
