from rest_framework.generics import CreateAPIView
from activity.models import ActivityQuestion, StudentQuestion
from mobile.serializers import StudentQuestionSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.shortcuts import get_object_or_404

class StudentQuestionCreateView(CreateAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = StudentQuestionSerializer
    
    def get_queryset(self):
        question_id = self.kwargs.get('question_id')
        return StudentQuestion.objects.filter(activity_question_id=question_id)
    
    def perform_create(self, serializer):
        question_id = self.kwargs.get('question_id')
        student_answer = self.request.data.get('student_answer')
        
        # Validate question exists
        activity_question = get_object_or_404(ActivityQuestion, id=question_id)
        
        serializer.save(
            student=self.request.user,
            activity_question=activity_question,
            activity=activity_question.activity,
            student_answer=student_answer
        )
        