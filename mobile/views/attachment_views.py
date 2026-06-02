
from django.http import Http404
from mobile.models import Attachment
from mobile.serializers import AttachmentSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

class AttachmentViewSet(ModelViewSet):
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    search_fields = ['name']
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    lookup_field = 'file_uuid'

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        file_uuid = self.kwargs.get(self.lookup_field)

        obj = next(
            (a for a in queryset.filter(file__icontains=file_uuid) if a.file_uuid == file_uuid),
            None
        )
        if not obj:
            raise Http404("No Attachment matches the given query.")

        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=False, url_path='by-file/(?P<file_uuid>[^/.]+)')
    def get_by_file(self, request, file_uuid=None):
        attachment = next(
            (a for a in self.get_queryset().filter(file__icontains=file_uuid) if a.file_uuid == file_uuid),
            None
        )

        if not attachment:
            return Response({"detail": "Not found"}, status=404)

        serializer = self.get_serializer(attachment)
        return Response(serializer.data)