from datetime import date
from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from course.models import Semester, SubjectEnrollment
from subject.models import Subject, Schedule
from subject.serializers import SubjectSerializer, ScheduleDataSerializer
    

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class SubjectViewSet(ModelViewSet):
    serializer_class = SubjectSerializer
    filter_backends = [SearchFilter]
    search_fields = ['subject_name', 'subject_short_name', 'assign_teacher', 'room_number']
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        today = date.today()
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()

        user = self.request.user
        queryset = Subject.objects.all()

        if current_semester:
            subject_ids = SubjectEnrollment.objects.filter(
                semester=current_semester
            ).values_list('subject_id', flat=True).distinct()
            queryset = queryset.filter(id__in=subject_ids)

        if user.is_authenticated and hasattr(user, 'profile') and user.is_teacher:
            queryset = queryset.filter(
                assign_teacher=user
            ) | queryset.filter(
                substitute_teacher=user, allow_substitute_teacher=True
            ) | queryset.filter(
                collaborators=user
            )
            queryset = queryset.distinct()

        return queryset


class Schedule_Data(ModelViewSet):
    serializer_class = ScheduleDataSerializer
    permission_classes = [IsAuthenticated]
    queryset = Schedule.objects.all()

