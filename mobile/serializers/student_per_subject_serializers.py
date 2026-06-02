from rest_framework import serializers
from accounts.models import CustomUser
from django.conf import settings

class StudentPerSubjectSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    student_photo = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ("id", "name", "student_photo")    

    def get_name(self, obj):
        first = getattr(obj, "first_name", "") or ""
        last = getattr(obj, "last_name", "") or ""
        full = f"{last}, {first}".strip()

        return full if full else getattr(obj, "username", str(obj.id))
    
    def _absolute(self, path: str) -> str:
        if not path:
            return None
        req = self.context.get("request")
        if req:
            return req.build_absolute_uri(path)
        base = getattr(settings, "BASE_URL", "").rstrip("/")
        return f"{base}{path}" if base else path

    def get_student_photo(self, obj):
        try:
            photo = getattr(getattr(obj, "profile", None), "student_photo", None)
            if photo:
                return self._absolute(photo.url)
            return None
        except Exception:
            return None
