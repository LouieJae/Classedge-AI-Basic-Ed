from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from activity.models import ActivityType, Rubrics
from activity.serializers import ActivityTypeSerializer, RubricsSerializer
from rest_framework.permissions import DjangoModelPermissions

class ActivityTypeViewSet(ModelViewSet):
    queryset = ActivityType.objects.all()
    serializer_class = ActivityTypeSerializer
    filter_backends = [SearchFilter]
    search_fields = ['name']
    permission_classes = [IsAuthenticated , DjangoModelPermissions]



class RubricsViewSet(ModelViewSet):
    serializer_class = RubricsSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    
    def get_queryset(self):
        """
        Filter rubrics by subject_id if provided in query parameters.
        Usage: /api/rubrics/?subject_id=123
        """
        queryset = Rubrics.objects.all()
        subject_id = self.request.query_params.get('subject_id', None)
        
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        return queryset.select_related('subject')
