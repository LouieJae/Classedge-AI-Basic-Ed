from rest_framework.generics import RetrieveAPIView
from activity.models import RetakeRecord
from mobile.serializers import RetakeRecordSerializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from rest_framework.response import Response
from django.http import Http404
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.generics import CreateAPIView
from activity.models import StudentActivity
from activity.models import Activity
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404


class RetakeView(CreateAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RetakeRecordSerializers

    def get_queryset(self):
        activity_id = self.kwargs.get('activity_id')
        user = self.request.user
        return RetakeRecord.objects.filter(
            student_activity__activity_id=activity_id,
            student_activity__student=user,
        )

    def perform_create(self, serializer):
        """Create a new attempt (RetakeRecord) for this student and activity.

        - Ensures there is a StudentActivity for (student, activity)
        - Uses StudentActivity.retake_count to determine the next retake_number
        - Sets started_at / will_end_at based on Activity.time_duration
        """
        activity_id = self.kwargs.get('activity_id')
        user = self.request.user

        # Get the activity or 404
        activity = get_object_or_404(Activity, pk=activity_id)

        # Get or create the StudentActivity for this student + activity
        student_activity, _ = StudentActivity.objects.get_or_create(
            student=user,
            activity=activity,
            defaults={
                'term': activity.term,
                'subject': activity.subject,
            },
        )

        # Next attempt number is previous completed attempts + 1
        retake_number = student_activity.retake_count + 1

        # Compute timing for this attempt
        started_at = timezone.now()
        will_end_at = None
        if activity.time_duration and activity.time_duration > 0:
            will_end_at = started_at + timedelta(minutes=activity.time_duration)

        # Update StudentActivity timing/status for this attempt
        student_activity.started_at = started_at
        student_activity.will_end_at = will_end_at
        student_activity.status = "ongoing"
        student_activity.save(update_fields=["started_at", "will_end_at", "status"])

        # Create the RetakeRecord for this attempt
        serializer.save(
            student_activity=student_activity,
            student=user,
            retake_number=retake_number,
            score=0,
            status="ongoing",
            started_at=started_at,
            will_end_at=will_end_at,
            duration=activity.time_duration if activity.time_duration else 0,
        )

   
class RetrieveAttempt(RetrieveAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = RetakeRecordSerializers
    lookup_field = "local_id"
    lookup_url_kwarg = "attempt_id"

    def get_queryset(self):
        """Limit attempts to those belonging to the authenticated student."""
        user = self.request.user
        return RetakeRecord.objects.filter(student_activity__student=user)