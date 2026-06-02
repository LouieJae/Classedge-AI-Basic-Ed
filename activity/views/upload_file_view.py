import io
import uuid

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from activity.models import Activity, get_upload_path

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
_MAX_DIMENSION = 800   # px — longest edge
_JPEG_QUALITY = 80     # 0-95


def _compress_image(uploaded_file):
    """
    Resize and re-encode an uploaded image as JPEG.
    Returns (ContentFile, '.jpg') on success, or (original_file, original_ext) if
    the file is not a recognised image type or Pillow fails for any reason.
    """
    content_type = getattr(uploaded_file, "content_type", "")
    if content_type not in _IMAGE_TYPES:
        import os
        return uploaded_file, os.path.splitext(uploaded_file.name)[1]

    try:
        from PIL import Image, ImageOps
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)   # honour EXIF rotation
        img = img.convert("RGB")             # ensure JPEG-compatible mode

        # Downscale only — never upscale
        if img.width > _MAX_DIMENSION or img.height > _MAX_DIMENSION:
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
        buf.seek(0)
        return ContentFile(buf.read()), ".jpg"
    except Exception:
        # Fall back to saving the original if anything goes wrong
        uploaded_file.seek(0)
        import os
        return uploaded_file, os.path.splitext(uploaded_file.name)[1]


@method_decorator(login_required, name="dispatch")
class UploadQuestionFileView(View):
    def post(self, request, activity_id):
        get_object_or_404(Activity, pk=activity_id)
        uploaded = request.FILES.get("file")
        if not uploaded:
            return JsonResponse({"ok": False, "error": "No file provided."}, status=400)

        content_type = getattr(uploaded, "content_type", "")
        if content_type in _IMAGE_TYPES:
            file_data, ext = _compress_image(uploaded)
            file_path = default_storage.save(
                f"uploadDocuments/{uuid.uuid4()}{ext}", file_data
            )
        else:
            file_path = default_storage.save(get_upload_path(None, uploaded.name), uploaded)

        return JsonResponse({"ok": True, "path": file_path})
