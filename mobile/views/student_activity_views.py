from rest_framework.generics import ListAPIView
from activity.models import (
    Activity,
    ActivityQuestion,
    RetakeRecord,
    RetakeRecordDetail,
    StudentActivity,
)
from activity.services.auto_grader import (
    recompute_retake_record_score,
    recompute_student_activity_total,
)
from mobile.serializers import StudentActivitySerializer, StudentActivitySerializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework import status
from django.utils import timezone
import re
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class StudentActivityListView(ListAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = StudentActivitySerializer
    
    def get_queryset(self):
        return StudentActivity.objects.filter(student=self.request.user)
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ActivityStudentViewSet(ModelViewSet):
    queryset = StudentActivity.objects.all()
    serializer_class = StudentActivitySerializers
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['name']
    authentication_classes = [JWTAuthentication, SessionAuthentication]

    def create(self, request, *args, **kwargs):
        print(f"[ActivityStudentViewSet] CREATE request by user: {request.user} | data: {request.data}")
        response = super().create(request, *args, **kwargs)
        print(f"[ActivityStudentViewSet] CREATE response status: {response.status_code} | data: {response.data}")
        return response

    def update(self, request, *args, **kwargs):
        print(f"[ActivityStudentViewSet] UPDATE request by user: {request.user} | pk: {kwargs.get('pk')} | data: {request.data}")
        response = super().update(request, *args, **kwargs)
        print(f"[ActivityStudentViewSet] UPDATE response status: {response.status_code} | data: {response.data}")
        return response

    def list(self, request, *args, **kwargs):
        print(f"[ActivityStudentViewSet] LIST request by user: {request.user} | params: {request.query_params}")
        response = super().list(request, *args, **kwargs)
        print(f"[ActivityStudentViewSet] LIST response status: {response.status_code} | count: {len(response.data)}")
        return response

    def retrieve(self, request, *args, **kwargs):
        print(f"[ActivityStudentViewSet] RETRIEVE request by user: {request.user} | pk: {kwargs.get('pk')}")
        response = super().retrieve(request, *args, **kwargs)
        print(f"[ActivityStudentViewSet] RETRIEVE response status: {response.status_code}")
        return response

    def destroy(self, request, *args, **kwargs):
        print(f"[ActivityStudentViewSet] DELETE request by user: {request.user} | pk: {kwargs.get('pk')}")
        response = super().destroy(request, *args, **kwargs)
        print(f"[ActivityStudentViewSet] DELETE response status: {response.status_code}")
        return response
    

class ActivityBatchSubmitView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, activity_id):
        """Submit all answers for an activity at once"""
        student = request.user
        answers = request.data.get('answers', {})
        
        if not answers:
            raise ValidationError({"answers": "No answers provided."})

        # Get the activity
        activity = Activity.objects.filter(pk=activity_id).first()
        if not activity:
            raise NotFound("Activity not found.")

        # Get all questions for this activity
        questions = ActivityQuestion.objects.filter(activity_id=activity_id)
      
        student_activity, _ = StudentActivity.objects.get_or_create(
            student=student,
            activity_id=activity_id,
            defaults={'subject': activity.subject},
        )
        student_activity.retake_count = (student_activity.retake_count or 0) + 1
        current_attempt = student_activity.retake_count

        retake_record, _ = RetakeRecord.objects.update_or_create(
            student_activity=student_activity,
            retake_number=current_attempt,
            defaults={
                'student': student,
                'activity': activity,
                'status': 'submitted',
            },
        )

        results = []
        max_possible_score = 0
        now = timezone.now()

        for question in questions:
            question_id = str(question.id)
            student_answer = answers.get(question_id, '')
            if isinstance(student_answer, dict):
                student_answer = student_answer.get('value', '')

            max_possible_score += question.score or 0

            if not student_answer:
                continue

            is_correct = self._check_answer(student_answer, question.correct_answer, question.quiz_type.name, question)
            score = question.score if is_correct else 0

            RetakeRecordDetail.objects.update_or_create(
                retake_record=retake_record,
                student=student,
                activity_question=question,
                defaults={
                    'student_answer': student_answer,
                    'score': score,
                    'submission_time': now,
                },
            )

            results.append({
                'question_id': question.id,
                'question_text': question.question_text,
                'student_answer': student_answer,
                'is_correct': is_correct,
                'score': score,
                'max_score': question.score,
            })

        recompute_retake_record_score(retake_record)
        recompute_student_activity_total(student_activity)

        student_activity.started_at = None
        student_activity.will_end_at = None
        student_activity.status = "submitted"
        student_activity.is_submitted = True
        student_activity.save(update_fields=['started_at', 'will_end_at', 'status', 'is_submitted', 'retake_count'])

        student_activity.refresh_from_db(fields=['total_score'])
        total_score = student_activity.total_score or 0

        return Response({
            'activity_id': activity_id,
            'total_score': total_score,
            'max_possible_score': max_possible_score,
            'percentage': (total_score / max_possible_score * 100) if max_possible_score > 0 else 0,
            'questions': results
        })


    def _check_answer(self, student_answer, correct_answer, quiz_type, question):
        """Check if student answer is correct"""
        if not student_answer or not correct_answer:
            return False
            
        # Normalize text for comparison
        def normalize(text):
            return re.sub(r'\W+', '', str(text).lower())
        
        if quiz_type == 'Multiple Choice':
            # Handle both index and text comparisons
            try:
                # If correct_answer is an index (0, 1, 2...)
                correct_index = int(correct_answer)
                # Get the actual choice text
                choices = self.get_question_choices(question)
                if correct_index < len(choices):
                    correct_text = choices[correct_index]['choice_text']
                    return normalize(student_answer) == normalize(correct_text)
            except (ValueError, IndexError):
                # If correct_answer is actual text
                return normalize(student_answer) == normalize(correct_answer)
        elif quiz_type == 'Matching Type':
            # Add matching type validation logic here
            return False  # Placeholder
        else:
            return normalize(student_answer) == normalize(correct_answer)
    
    def get_question_choices(self, question):
        """Get choices for a question"""
        if not question.quiz_type or question.quiz_type.name != 'Multiple Choice':
            return []
        
        choices = question.choices.all()
        return [{'id': choice.id, 'choice_text': choice.choice_text} for choice in choices]
