from rest_framework.generics import ListAPIView, RetrieveAPIView
from course.models import SubjectEnrollment, Semester, Term
from subject.models import Subject
from module.models import Module
from activity.models import Activity, StudentActivity
from mobile.serializers import LessonActivityListSerializer,LessonSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication
from django.db.models import Q
from django.db.models import OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from accounts.utils.custom_pagination_utils import CustomPagination


class LessonActivityListView(ListAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = LessonActivityListSerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        subject_id = self.kwargs.get('subject_id')  # Get subject_id from URL
        
        # Get current semester and term (existing code)
        today = timezone.now().date()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        if not current_semester:
            print(f"DEBUG: No current semester found for date {today}")
            return Activity.objects.none()

        current_term = Term.objects.filter(
            semester=current_semester,
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if not current_term:
            current_term = Term.objects.filter(semester=current_semester).first()
            print(f"DEBUG: No term in date range, using fallback term: {current_term}")

        if not current_term:
            print(f"DEBUG: No term found for semester {current_semester}")
            return Activity.objects.none()
        
        print(f"DEBUG: Using term: {current_term}, semester: {current_semester}")

        user = self.request.user
        role_name = (
            getattr(getattr(getattr(user, 'profile', None), 'role', None), 'name', '') or ''
        ).lower()

        # Base queryset filtered by subject only (not term)
        base = Activity.objects.filter(
            subject_id=subject_id
        ).select_related('activity_type', 'subject', 'term').prefetch_related('remedial_students')
        
        print(f"DEBUG: Base activities count (subject={subject_id}): {base.count()}")

        # Check for classroom_mode query parameter.
        # Accepts true/1/yes (case-insensitive) to return ONLY classroom-mode
        # activities, and false/0/no to return ONLY non-classroom ones.
        classroom_mode_param = self.request.query_params.get('classroom_mode')
        print(f"DEBUG: raw classroom_mode param = {classroom_mode_param!r}")
        if classroom_mode_param is not None:
            normalized = str(classroom_mode_param).strip().lower()
            if normalized in ('true', '1', 'yes'):
                base = base.filter(classroom_mode=False)
                print(f"DEBUG: After classroom_mode=True filter: {base.count()}")
            elif normalized in ('false', '0', 'no'):
                base = base.filter(classroom_mode=True)
                print(f"DEBUG: After classroom_mode=False filter: {base.count()}")

        # Role-based filtering
        print(f"DEBUG: User role: {role_name}")
        if role_name == 'teacher':
            # Teachers can only see activities for subjects they teach
            teachable_subjects = Subject.objects.filter(
                Q(assign_teacher=user) |
                Q(substitute_teacher=user, allow_substitute_teacher=True) |
                Q(collaborators=user)
            ).values_list('id', flat=True)
            
            qs = base.filter(subject_id__in=teachable_subjects)
            print(f"DEBUG: Teacher - teachable subjects: {list(teachable_subjects)}, final count: {qs.count()}")

        elif role_name == 'student':
            # Students can only see activities for subjects they're enrolled in
            enrolled_subjects = SubjectEnrollment.objects.filter(
                semester=current_semester,
                student=user,
                status='enrolled'
            ).values_list('subject_id', flat=True)
            
            qs = base.filter(subject_id__in=enrolled_subjects)
            print(f"DEBUG: Student - enrolled subjects: {list(enrolled_subjects)}, final count: {qs.count()}")
            
        else:
            # Other authenticated users can see all activities for the subject
            qs = base
            print(f"DEBUG: Other role - final count: {qs.count()}")

        # Add user-specific annotations
        if user.is_authenticated:
            sa = (StudentActivity.objects
                .filter(student=user, activity=OuterRef('pk'))
                .order_by('-start_time'))

            qs = qs.annotate(
                my_retake_count=Coalesce(
                    Subquery(sa.values('retake_count')[:1], output_field=IntegerField()),
                    Value(0),
                ),
                my_student_activity_id=Subquery(sa.values('local_id')[:1]),
            )
        
        return qs
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context



class LessonRetrieveView(RetrieveAPIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = LessonSerializer
    
    def get_object(self):
        lesson_id = self.kwargs.get('lesson_id')
        try:
            lesson_id = int(lesson_id)
            return Module.objects.get(id=lesson_id)
        except (ValueError, TypeError):
            raise NotFound("Invalid lesson ID format.")
        except Module.DoesNotExist:
            raise NotFound("Lesson not found.")
