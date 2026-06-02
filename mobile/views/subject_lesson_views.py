
from rest_framework.generics import ListAPIView
from course.models import SubjectEnrollment, Semester, Term
from subject.models import Subject
from module.models import Module
from mobile.serializers import SubjectLessonSerializer, StudentNameSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.db.models import Q
from django.utils import timezone
from accounts.models import CustomUser
from accounts.utils import CustomPagination


class SubjectLessonListView(ListAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SubjectLessonSerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        subject_id = self.kwargs.get('subject_id')
        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        
        if not current_semester:
            return Module.objects.none()
        
        current_term = Term.objects.filter(
            semester=current_semester,
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if not current_term:
            current_term = Term.objects.filter(
                semester=current_semester
            ).first()

        if not current_term:
            return Module.objects.none()

        user = self.request.user
        role_name = (
            getattr(getattr(getattr(user, 'profile', None), 'role', None), 'name', '') or ''
        ).lower()

        # Base queryset
        base = Module.objects.filter(
            subject_id=subject_id,
        ).select_related('subject')

        # Role-based filtering
        if role_name == 'teacher':
            # Teachers can see lessons for subjects they teach
            teachable_subjects = Subject.objects.filter(
                Q(assign_teacher=user) |
                Q(substitute_teacher=user, allow_substitute_teacher=True) |
                Q(collaborators=user)
            ).values_list('id', flat=True)
            
            qs = base.filter(subject_id__in=teachable_subjects)

        elif role_name == 'student':
            # Students can see lessons for subjects they're enrolled in
            enrolled_subjects = SubjectEnrollment.objects.filter(
                semester=current_semester,
                student=user,
                status='enrolled'
            ).values_list('subject_id', flat=True)
            
            qs = base.filter(subject_id__in=enrolled_subjects)
            
        else:
            # Other authenticated users can see all lessons for the subject
            qs = base

        # Apply additional filters for all users
        return qs.filter(
            Q(display_lesson_for_selected_users__isnull=True) | 
            Q(display_lesson_for_selected_users=user) |
            Q(subject__assign_teacher=user)
        ).order_by('-start_date')
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class StudentsBySubjectView(ListAPIView):
    serializer_class = StudentNameSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        subject_id = self.kwargs["subject_id"]

        qs = CustomUser.objects.filter(
            subjectenrollment__subject_id=subject_id
        )

        status = self.request.GET.get("status", "enrolled")
        if status:
            qs = qs.filter(subjectenrollment__status=status)

        sem_id = self.request.GET.get("semester_id")
        if sem_id:
            qs = qs.filter(subjectenrollment__semester_id=sem_id)

        cvg = self.request.GET.get("can_view_grade")
        if cvg is not None:
            truthy = {"1","true","yes","on","True","TRUE"}
            qs = qs.filter(subjectenrollment__can_view_grade=(cvg in truthy))

        qs = qs.order_by("last_name", "first_name").distinct()
        return qs
