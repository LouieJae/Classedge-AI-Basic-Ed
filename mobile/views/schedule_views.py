from course.models import Semester, SubjectEnrollment
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from accounts.utils import CustomPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from subject.models import Schedule
from subject.serializers import ScheduleDataSerializer
from mobile.serializers import CurrentNextScheduleSerializer

class CurrentNextScheduleAPI(APIView):
    """
    Unified API endpoint for getting current and next schedules.
    Supports both teachers and students.
    
    Query Parameters:
        - mode: 'current' or 'next' (optional)
        - page: page number (for pagination when no mode is specified)
        - page_size: number of items per page (default: 10, max: 100)
    
    Examples:
        GET /api/class_schedule/  (returns all schedules with pagination)
        GET /api/class_schedule/?page=2&page_size=20
        GET /api/class_schedule/?mode=current
        GET /api/class_schedule/?mode=next
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    
    def get(self, request):
        schedule_type = request.query_params.get('mode', '').lower()
        
        # Get current semester
        today = timezone.localdate()
        current_semester = Semester.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if not current_semester:
            return Response(
                {
                    'message': 'No active semester found',
                    'schedules': [] if not schedule_type else None
                },
                status=status.HTTP_200_OK
            )
        
        # Get user role
        user = request.user
        role_name = (
            getattr(getattr(getattr(user, 'profile', None), 'role', None), 'name', '') or ''
        ).lower()
        
        # Get schedules based on user role
        base_schedules = Schedule.objects.filter(
            semester=current_semester,
            subject__is_coil=False,
            subject__is_hali=False
        )
        
        if role_name == 'teacher':
            # Filter schedules where user is the active teacher
            schedules = base_schedules.filter(
                Q(subject__assign_teacher=user) |
                Q(subject__substitute_teacher=user, subject__allow_substitute_teacher=True) |
                Q(subject__collaborators=user)
            ).distinct()
        elif role_name == 'student':
            # Filter schedules for enrolled subjects
            enrolled_subject_ids = SubjectEnrollment.objects.filter(
                semester=current_semester,
                student=user,
                status='enrolled'
            ).values_list('subject_id', flat=True)
            
            schedules = base_schedules.filter(subject_id__in=enrolled_subject_ids)
        else:
            # For other roles, return no schedules
            return Response(
                {
                    'message': 'No schedule found',
                    'schedules': [] if not schedule_type else None
                },
                status=status.HTTP_200_OK
            )
        
        # If no mode parameter, return all schedules with pagination
        if not schedule_type:
            schedules = schedules.select_related(
                'subject', 'subject__assign_teacher', 'subject__substitute_teacher'
            ).prefetch_related('subject__collaborators')
            
            # Apply pagination
            paginator = self.pagination_class()
            paginated_schedules = paginator.paginate_queryset(schedules, request)
            
            serializer = ScheduleDataSerializer(
                paginated_schedules,
                many=True,
                context={'request': request}
            )
            
            return paginator.get_paginated_response(serializer.data)
        
        # Validate the mode parameter if provided
        if schedule_type not in ['current', 'next']:
            return Response(
                {
                    'message': 'Invalid filter. Use mode=current or mode=next',
                    'status': 400
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get current time
        now = timezone.localtime()
        current_weekday = now.strftime('%a')
        current_time = now.time()
        
        if schedule_type == 'current':
            # Find current schedule (user is currently in class)
            current_schedule = schedules.filter(
                days_of_week__contains=current_weekday,
                schedule_start_time__lte=current_time,
                schedule_end_time__gte=current_time
            ).first()
            
            if current_schedule:
                # Calculate next occurrence
                next_occurrence = self._calculate_next_occurrence(current_schedule, now)
                serializer = CurrentNextScheduleSerializer(
                    current_schedule,
                    context={'request': request, 'next_occurrence': next_occurrence}
                )
                data = serializer.data
                data['next_occurrence'] = next_occurrence.strftime('%Y-%m-%d') if next_occurrence else None
                
                return Response(
                    {
                        'message': 'Current schedule found',
                        'schedule': data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'message': 'No current schedule',
                        'schedule': None
                    },
                    status=status.HTTP_200_OK
                )
        
        elif schedule_type == 'next':
            # Find next upcoming schedule
            # First, check for classes later today
            next_schedule = schedules.filter(
                days_of_week__contains=current_weekday,
                schedule_start_time__gt=current_time
            ).order_by('schedule_start_time').first()
            
            if not next_schedule:
                # If no classes today, find the next class on upcoming days
                next_schedule = self._find_next_schedule_across_days(schedules, now)
            
            if next_schedule:
                # Calculate next occurrence
                next_occurrence = self._calculate_next_occurrence(next_schedule, now)
                serializer = CurrentNextScheduleSerializer(
                    next_schedule,
                    context={'request': request, 'next_occurrence': next_occurrence}
                )
                data = serializer.data
                data['next_occurrence'] = next_occurrence.strftime('%Y-%m-%d') if next_occurrence else None
                
                return Response(
                    {
                        'message': 'Next schedule found',
                        'schedule': data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        'message': 'No upcoming schedule',
                        'schedule': None
                    },
                    status=status.HTTP_200_OK
                )
    
    def _calculate_next_occurrence(self, schedule, from_datetime):
        """
        Calculate the next occurrence date for a given schedule.
        """
        day_mapping = {
            'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3,
            'Fri': 4, 'Sat': 5, 'Sun': 6
        }
        
        current_date = from_datetime.date()
        current_weekday = current_date.weekday()
        current_time = from_datetime.time()
        
        # Get schedule days as weekday numbers
        schedule_weekdays = sorted([day_mapping[day] for day in schedule.days_of_week])
        
        # Check if schedule occurs today and hasn't started yet
        if current_weekday in schedule_weekdays and current_time < schedule.schedule_start_time:
            return current_date
        
        # Find next occurrence
        for i in range(1, 8):
            next_date = current_date + timedelta(days=i)
            if next_date.weekday() in schedule_weekdays:
                return next_date
        
        return None
    
    def _find_next_schedule_across_days(self, schedules, from_datetime):
        """
        Find the next schedule across all days of the week.
        """
        day_mapping = {
            'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3,
            'Fri': 4, 'Sat': 5, 'Sun': 6
        }
        
        current_date = from_datetime.date()
        current_weekday = current_date.weekday()
        
        # Check each day for the next 7 days
        for days_ahead in range(1, 8):
            check_date = current_date + timedelta(days=days_ahead)
            check_weekday_num = check_date.weekday()
            check_weekday_abbr = list(day_mapping.keys())[check_weekday_num]
            
            # Find schedules for this day
            day_schedules = schedules.filter(
                days_of_week__contains=check_weekday_abbr
            ).order_by('schedule_start_time')
            
            if day_schedules.exists():
                return day_schedules.first()
        
        return None
