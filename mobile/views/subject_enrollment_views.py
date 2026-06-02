from rest_framework.generics import ListAPIView, RetrieveAPIView
from course.models import SubjectEnrollment, Semester
from mobile.serializers import SubjectEnrollmentSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.utils import timezone


class SubjectEnrollmentListView(ListAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SubjectEnrollmentSerializer
    
    def get_queryset(self):
        return SubjectEnrollment.objects.filter(student=self.request.user)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

class SubjectEnrollmentRetrieveView(RetrieveAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SubjectEnrollmentSerializer
    
    def get_object(self):
        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        if not current_semester:
            return SubjectEnrollment.objects.none()
    
        return SubjectEnrollment.objects.get(student=self.request.user, semester=current_semester)
