from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from activity.models import Activity
from mobile.serializers.activity_details import ActivityDetailsSerializer, PendingStudentActivitySerializer, ActivitySerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from activity.models import StudentActivity
from activity.models import RetakeRecord
from django.utils import timezone
from django.http import Http404
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

class ActivityViewSet(ModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    search_fields = ['name']
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    
    def list(self, request, *args, **kwargs):
        print(f"ActivityViewSet.list() called by user: {request.user}")
        return super().list(request, *args, **kwargs)


class PendingStudentActivitiesViewSet(ModelViewSet):
    """ViewSet for fetching pending student activities.
    
    Endpoints:
    - GET /api/activities/pending/ - Returns paginated results
    - GET /api/activities/pending/all/ - Returns all results without pagination
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PendingStudentActivitySerializer
    http_method_names = ['get']
    filter_backends = []
    filterset_class = []

    def get_queryset(self):
        """Fetch all pending activities for the authenticated student user."""
        user = self.request.user
        profile = getattr(user, 'profile', None)
        role = getattr(profile, 'role', None)
        role_name = getattr(role, 'name', '').lower()

        # Only students can see pending activities
        if role_name != 'student':
            return StudentActivity.objects.none()

        queryset = (
            StudentActivity.objects
            .filter(student=user, retake_count=0)
            .select_related('activity__activity_type', 'activity__subject')
            .order_by('-activity__start_time')
        )
        
        # Filter by subject_id if provided
        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            queryset = queryset.filter(activity__subject_id=subject_id)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """List pending activities with pagination."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='all')
    def all(self, request):
        """Return all pending activities without pagination."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActivityDetailsView(generics.RetrieveAPIView):
    serializer_class = ActivityDetailsSerializer
    permission_classes = [IsAuthenticated]  # optional
    lookup_field = "local_id"
    lookup_url_kwarg = "id"
    queryset = Activity.objects.all().order_by('-start_time')



class ActivityTimerView(APIView):
    """
    Get remaining time for a student's activity
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, activity_id):
        student = request.user
        
        try:
            student_activity = StudentActivity.objects.get(
                student=student,
                activity_id=activity_id
            )
            
            # Use StudentActivity as primary source for timing
            started_at = student_activity.started_at
            will_end_at = student_activity.will_end_at
            
            # Calculate time remaining
            time_remaining_seconds = None
            time_expired = False
            
            if will_end_at:
                time_remaining = will_end_at - timezone.now()
                time_remaining_seconds = int(time_remaining.total_seconds())
                time_expired = time_remaining_seconds <= 0
                time_remaining_seconds = max(0, time_remaining_seconds)

                if time_expired and student_activity.status != "submitted" and student_activity.status != "expired":
                    student_activity.status = "expired"
                    student_activity.save(update_fields=['status'])

                    # Also mark the current retake record as expired, if it exists
                    current_attempt = student_activity.retake_count + 1
                    RetakeRecord.objects.filter(
                        student_activity=student_activity,
                        retake_number=current_attempt,
                    ).update(status='expired')
            
            return Response({
                'activity_id': activity_id,
                'retake_count': student_activity.retake_count,
                'started_at': started_at,
                'will_end_at': will_end_at,
                'time_remaining_seconds': time_remaining_seconds,
                'time_expired': time_expired,
                'has_time_limit': will_end_at is not None
            })
            
        except StudentActivity.DoesNotExist:
            return Response({
                'error': 'No activity record found for this student',
                'activity_id': activity_id
            }, status=status.HTTP_404_NOT_FOUND)