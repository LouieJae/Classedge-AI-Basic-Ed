from rest_framework.generics import ListAPIView
from activity.models import ActivityQuestion
from mobile.serializers import ActivityQuestionListSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from activity.models import RetakeRecord, RetakeRecordDetail, StudentActivity


class ActivityQuestionListView(ListAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityQuestionListSerializer
    
    def get_queryset(self):
        activity_id = self.kwargs.get('activity_id')
        return ActivityQuestion.objects.filter(activity_id=activity_id)
    
    def list(self, request, *args, **kwargs):
        from datetime import timedelta
        
        activity_id = self.kwargs.get('activity_id')
        user = request.user
        
        started_at = None
        will_end_at = None
        
        try:
            student_activity = StudentActivity.objects.get(
                student=user,
                activity_id=activity_id
            )
            activity = student_activity.activity

            # Set started_at and will_end_at on first view of this attempt
            # Use StudentActivity as primary, sync to RetakeRecord
            if student_activity.started_at is None:
                student_activity.started_at = timezone.now()
                
                # Calculate will_end_at based on activity time_duration (in minutes)
                if activity.time_duration and activity.time_duration > 0:
                    student_activity.will_end_at = student_activity.started_at + timedelta(minutes=activity.time_duration)
                
                student_activity.status = "ongoing"
                student_activity.save(update_fields=['started_at', 'will_end_at', 'status'])
                
        except StudentActivity.DoesNotExist:
            pass
        
        # Get the normal response
        response = super().list(request, *args, **kwargs)
        
        # Add timing information to response for frontend
        response.data = {
            'questions': response.data,

        }
        
        return response


class ActivityAutosaveView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, activity_id):
        """Autosave multiple answers for an activity without submitting.

        Expects the same "answers" structure as ActivityBatchSubmitView, e.g.:
        {
            "answers": {
                "48": {"value": "1"},
                "47": {"value": "1"}
            }
        }
        """
        student = request.user
        answers = request.data.get('answers', {})

        if not isinstance(answers, dict):
            raise ValidationError({"answers": "Invalid answers payload."})

        questions = ActivityQuestion.objects.filter(activity_id=activity_id)
        if not questions.exists():
            return Response({'activity_id': activity_id, 'saved_answers': 0}, status=status.HTTP_200_OK)

        activity = questions.first().activity
        student_activity, _ = StudentActivity.objects.get_or_create(
            student=student, activity=activity,
            defaults={'subject': activity.subject},
        )
        attempt_number = max(1, student_activity.retake_count or 1)
        retake_record, _ = RetakeRecord.objects.update_or_create(
            student_activity=student_activity,
            retake_number=attempt_number,
            defaults={
                'student': student,
                'activity': activity,
                'status': 'in_progress',
            },
        )

        now = timezone.now()
        saved_count = 0
        for question in questions:
            question_id = str(question.id)
            raw_answer = answers.get(question_id, None)
            if raw_answer is None:
                continue

            student_answer = raw_answer
            if isinstance(student_answer, dict):
                student_answer = student_answer.get('value', '')

            RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={
                    'student_answer': student_answer,
                    'submission_time': now,
                },
            )
            saved_count += 1

        return Response({
            'activity_id': activity_id,
            'saved_answers': saved_count,
        }, status=status.HTTP_200_OK)