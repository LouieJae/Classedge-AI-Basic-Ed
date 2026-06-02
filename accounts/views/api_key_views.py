from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from accounts.models import APIKey
from accounts.serializers.api_key_serializers import APIKeySerializer
from accounts.utils import CustomPagination
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render

class HasSubjectAddRolePermission(BasePermission):
    """Allow only users with the 'subject.add_role' Django permission."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm("subject.add_role")


class APIKeyViewSet(ModelViewSet):
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer
    pagination_class = CustomPagination
    permission_classes = [IsAuthenticated, HasSubjectAddRolePermission]

    def get_queryset(self):
        # Only show keys owned by the logged-in user
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Auto-assign the logged-in user as owner
        serializer.save(owner=self.request.user)

@login_required
@permission_required('subject.add_role', raise_exception=True)
def api_key_management(request):
    return render(request, 'accounts/api_page/api_key_list.html')