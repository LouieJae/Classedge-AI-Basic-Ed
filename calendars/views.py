from django.db.models import Q
from django.shortcuts import render
from django.core.cache import cache
from activity.models import Activity,  StudentActivity
from django.http import JsonResponse

from lms.http import camel_json_response

from accounts.utils.fetch_facebook_data import fetch_facebook_posts

from calendars.services.department_filter import visible_department_ids
from activity.models import RetakeRecordDetail
from django.contrib.auth.decorators import login_required
from .serializers import *
from rest_framework.decorators import api_view, authentication_classes
from .models import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from datetime import date
from django.shortcuts import render, get_object_or_404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import SessionAuthentication 
from accounts.utils import CustomPagination
from rest_framework.pagination import PageNumberPagination
from django.core.mail import send_mail
from django.conf import settings
from logs.views import _send_onesignal_notification

def _user_subject_ids_for_current_sem(user):
    """Subject IDs the user is connected to in the active semester.

    Connection = teacher (assign / substitute / collaborator) OR active
    enrolled student. Used to scope subject-level announcements both on
    /campus/news/ (read) and in the teacher CRUD page (write).
    """
    if not getattr(user, 'is_authenticated', False):
        return []
    try:
        from subject.models.subject_model import Subject
        from course.models.semester_model import Semester
        from course.models.subject_enrollment_model import SubjectEnrollment
    except Exception:
        return []

    sem = Semester.objects.filter(end_semester=False).order_by('-start_date').first()

    # Teaching connection (works whether or not there's an active semester).
    teaching = Subject.objects.filter(
        Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user)
    ).values_list('id', flat=True)

    enrolled = []
    if sem is not None:
        enrolled = SubjectEnrollment.objects.filter(
            student=user, semester=sem, is_active_semester=True, status='enrolled',
        ).values_list('subject_id', flat=True)

    return list({*teaching, *enrolled})


@login_required
def calendars(request):
    user_role = (request.user.role_name or None)
    user = request.user

    # [Classedge LMS] Capability flags, sourced from Django auth permissions
    # rather than role names — so any role (registrar, time keeper, dean,
    # custom) can be granted event/announcement/holiday management by an
    # admin without code changes.
    def _can_manage(app_label, model):
        return any(
            user.has_perm(f"{app_label}.{action}_{model}")
            for action in ("add", "change", "delete")
        )

    can_manage_events        = _can_manage("calendars", "event")
    can_manage_announcements = _can_manage("calendars", "announcement")
    can_manage_holidays      = _can_manage("calendars", "holiday")

    return render(request, 'calendar/calendar.html', {
        'user_role': user_role,
        'can_manage_events': can_manage_events,
        'can_manage_announcements': can_manage_announcements,
        'can_manage_holidays': can_manage_holidays,
    })

@api_view(['GET', 'POST', 'PUT'])
def holiday_api(request):
    if request.method == 'GET':
        holiday_id = request.query_params.get('id') 
        if holiday_id:
            try:
                holiday = Holiday.objects.get(id=holiday_id)
                serializer = HolidaySerializer(holiday)
                return Response(serializer.data)
            except Holiday.DoesNotExist:
                return Response({'error': 'Holiday not found'}, status=status.HTTP_404_NOT_FOUND)

        holidays = Holiday.objects.all()
        serializer = HolidaySerializer(holidays, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = HolidaySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'PUT':
        holiday_id = request.data.get('id')
        if not holiday_id:
            return Response({'error': 'Holiday ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            holiday = Holiday.objects.get(id=holiday_id)
        except Holiday.DoesNotExist:
            return Response({'error': 'Holiday not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = HolidaySerializer(holiday, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

@login_required
def activity_api(request):
    user = request.user
    events = []

    if user.is_student:
        student_activities = StudentActivity.objects.filter(student=user)
        answered_activity_ids = RetakeRecordDetail.objects.filter(student=user).values_list('activity_question__activity_id', flat=True).distinct()
        for student_activity in student_activities:
            activity = student_activity.activity
            event = {
                'id': activity.id,
                'title': activity.activity_name,
                'start': activity.start_time.isoformat() if activity.start_time else '',
                'end': activity.end_time.isoformat() if activity.end_time else '',
                'allDay': activity.start_time is None or activity.end_time is None,
                'answered': activity.id in answered_activity_ids, 
            }
            events.append(event)

    elif user.is_teacher:
        teacher_activities = Activity.objects.filter(subject__assign_teacher=user)
        for activity in teacher_activities:
            event = {
                'id': activity.id,
                'title': activity.activity_name,
                'start': activity.start_time.isoformat() if activity.start_time else '',
                'end': activity.end_time.isoformat() if activity.end_time else '',
                'allDay': activity.start_time is None or activity.end_time is None,
            }
            events.append(event)

    return camel_json_response(events)


@api_view(['GET', 'POST', 'PUT'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
def calendar_api(request):
    try:
        if request.method == 'GET':
            # Fetch activities
            user = request.user
            activities = []
            if user.is_student:
                student_activities = StudentActivity.objects.filter(student=user)
                answered_activity_ids = RetakeRecordDetail.objects.filter(student=user).values_list(
                    'activity_question__activity_id', flat=False
                ).distinct()
                for student_activity in student_activities:
                    activity = student_activity.activity
                    activities.append({
                        'id': activity.id,
                        'title': activity.activity_name,
                        'start': activity.start_time.isoformat() if activity.start_time else '',
                        'end': activity.end_time.isoformat() if activity.end_time else '',
                        # 'allDay': activity.start_time is None or activity.end_time is None,
                        'type': 'activity',
                        'answered': activity.id in answered_activity_ids,
                    })

            elif user.is_teacher:
                teacher_activities = Activity.objects.filter(subject__assign_teacher=user)
                for activity in teacher_activities:
                    activities.append({
                        'id': activity.id,
                        'title': activity.activity_name,
                        'start': activity.start_time.isoformat() if activity.start_time else '',
                        'end': activity.end_time.isoformat() if activity.end_time else '',
                        # 'allDay': activity.start_time is None or activity.end_time is None,
                        'type': 'activity',
                    })

            # Fetch holidays — scoped by department like events/announcements.
            # Emit `start` (not `date`) so FullCalendar's month grid paints
            # them; include holiday_type so the eventClick edit flow can
            # repopulate the type dropdown.
            dept_ids = visible_department_ids(request.user)
            if dept_ids is None:
                holiday_qs = Holiday.objects.all()
            else:
                holiday_qs = Holiday.objects.filter(
                    Q(department__isnull=True) | Q(department_id__in=dept_ids)
                )
            holidays = []
            for h in holiday_qs:
                if not h.date:
                    continue
                holidays.append({
                    'id': f"holiday-{h.id}",
                    'title': h.title,
                    'start': h.date.isoformat(),
                    'allDay': True,
                    'type': 'holiday',
                    'holiday_type': h.holiday_type,
                    'backgroundColor': h.color,
                    'borderColor': h.color,
                })

            # Fetch events
            events = []
            if dept_ids is None:
                events_qs = Event.objects.all()
            else:
                events_qs = Event.objects.filter(
                    Q(department__isnull=True) | Q(department_id__in=dept_ids)
                )
            for event in events_qs:
                events.append({
                    'id': event.id,
                    'title': event.title,
                    'start': event.start_date.isoformat() if event.start_date else None,
                    'end': event.end_date.isoformat() if event.end_date else None,
                    'date': event.start_date.isoformat() if event.start_date else None,  # For event_time handling
                    'event_time': event.time.isoformat() if event.time else None,
                    'type': 'event',
                    'location': event.location,
                })

            # Fetch announcements — same department scoping as events so
            # institution-wide (department IS NULL) plus the user's depts
            # are visible. Emit `start` (not `date`) so FullCalendar
            # actually paints them on the month grid.
            announcements = []
            if dept_ids is None:
                ann_qs = Announcement.objects.all()
            else:
                ann_qs = Announcement.objects.filter(
                    Q(department__isnull=True) | Q(department_id__in=dept_ids)
                )
            for a in ann_qs:
                if not a.date:
                    continue
                announcements.append({
                    'id': f"announcement-{a.id}",
                    'title': a.title,
                    'start': a.date.isoformat(),
                    'allDay': True,
                    'type': 'announcement',
                })

            # Combine all event types
            combined_events = events + activities + announcements + holidays
            return camel_json_response(combined_events)
        
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomPagination(PageNumberPagination):
    page_size = 5  # default per page
    page_size_query_param = 'page_size'
    max_page_size = 100

@api_view(['GET'])
@authentication_classes([SessionAuthentication, JWTAuthentication])
def announcement_api(request):
    try:
        # # --- Fetch holidays ---
        # holidays = [
        #     {
        #         'id': f"holiday-{h.id}",
        #         'title': h.title,
        #         'date': h.date.isoformat(),
        #         'allDay': True,
        #         'type': 'holiday',
        #         'backgroundColor': h.color,
        #         'borderColor': h.color,
        #     }
        #     for h in Holiday.objects.all()
        # ]

        # # --- Fetch events ---
        # events = [
        #     {
        #         'id': f"event-{e.id}",
        #         'title': e.title,
        #         'start_date': e.start_date.isoformat() if e.start_date else None,
        #         'end_date': e.end_date.isoformat() if e.end_date else None,
        #         'event_time': e.time.isoformat() if e.time else None,
        #         'type': 'event',
        #         'location': e.location,
        #     }
        #     for e in Event.objects.all()
        # ]

        # --- Fetch announcements ---
        # [Classedge LMS] Scope announcements the same way calendar_api scopes events:
        # institution-wide (department IS NULL) plus any dept the user belongs to or heads.
        dept_ids = visible_department_ids(request.user)
        if dept_ids is None:
            ann_qs = Announcement.objects.all()
        else:
            ann_qs = Announcement.objects.filter(
                Q(department__isnull=True) | Q(department_id__in=dept_ids)
            )
        announcements = [
            {
                'id': f"{a.id}",
                'title': f"{a.title}",
                'description': f"{a.description}",
                'date': a.date.isoformat(),
                'type': 'announcement',
            }
            for a in ann_qs
        ]

        # --- Combine all event types ---
        combined_events = announcements

        # --- Apply pagination ---
        paginator = CustomPagination()
        paginated_data = paginator.paginate_queryset(combined_events, request)

        # Return paginated response
        return paginator.get_paginated_response(paginated_data)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    

@login_required
@api_view(['GET'])
def api_event_list(request):
    if request.method == 'GET':
        today = date.today()
        upcoming_events = Event.objects.filter(date__gte=today).order_by('date')[:4]

        events = []
        for event in upcoming_events:
            events.append({
                'id': f"event-{event.id}",
                'title': event.title,
                'start_date': event.start_date.isoformat() if event.start_date else None,
                'end_date': event.end_date.isoformat() if event.end_date else None,
                'event_time': event.time.isoformat() if event.time else None,
                'type': 'event',
                'location': event.location,
            })

        return camel_json_response(events)

class EventViewSet(ModelViewSet):
    serializer_class = EventSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    # DjangoModelPermissions: GET requires no model perm (lets every
    # authenticated user read events for the calendar feed), but
    # POST/PUT/PATCH/DELETE require calendars.{add,change,delete}_event
    # respectively. Assign those perms to whichever roles should manage
    # events — no code change needed to onboard a new role.
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    pagination_class = CustomPagination

    def get_queryset(self):
        """[Classedge LMS] Scope events by the requester's department membership."""
        qs = self.serializer_class.Meta.model.objects.all()
        dept_ids = visible_department_ids(self.request.user)
        if dept_ids is not None:
            qs = qs.filter(Q(department__isnull=True) | Q(department_id__in=dept_ids))
        return qs.order_by('-created_at')
    
    def perform_create(self, serializer):
        # Save the event
        event = serializer.save(created_by=self.request.user)
        
        # Send push notification
        try:
            heading = "New Event"
            message = f"{event.title}"
            
            # Add description to message if available
            if event.description:
                # Truncate description if too long
                description = event.description[:100] + "..." if len(event.description) > 100 else event.description
                message = f"{event.title}: {description}"
            
            # Prepare notification data
            notification_data = {
                'type': 'event',
                'entityType': 'event',
                'entityId': event.id,
                'path': f'/event/{event.id}',
                'title': event.title,
                'startDate': event.start_date.isoformat() if event.start_date else None,
                'location': event.location
            }
            
            # Send to all subscribed users
            result = _send_onesignal_notification(
                heading=heading,
                message=message,
                segments=["Total Subscriptions"],
                data=notification_data
            )
            
            print(f"[EventViewSet] Push notification sent: {result}")
            
        except Exception as e:
            # Log error but don't fail the event creation
            print(f"[EventViewSet] Failed to send push notification: {str(e)}")


class AnnouncementViewSet(ModelViewSet):
    serializer_class = AnnouncementSerializer
    # Same model-permission enforcement as EventViewSet: reads are open
    # to any authenticated user, writes require the matching Django perm
    # (calendars.add_announcement / change / delete).
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    pagination_class = CustomPagination

    def get_queryset(self):
        """[Classedge LMS] Scope announcements by the requester's department membership."""
        qs = self.serializer_class.Meta.model.objects.all()
        dept_ids = visible_department_ids(self.request.user)
        if dept_ids is not None:
            qs = qs.filter(Q(department__isnull=True) | Q(department_id__in=dept_ids))
        return qs.order_by('-created_at')
    
    def perform_create(self, serializer):
        # Save the announcement
        announcement = serializer.save(created_by=self.request.user)
        
        # Send push notification
        try:
            heading = "New Announcement"
            message = f"{announcement.title}"
            
            # Add description to message if available
            if announcement.description:
                # Truncate description if too long
                description = announcement.description[:100] + "..." if len(announcement.description) > 100 else announcement.description
                message = f"{announcement.title}: {description}"
            
            # Prepare notification data
            notification_data = {
                'type': 'announcement',
                'entityType': 'announcement',
                'entityId': announcement.id,
                'path': f'/announcement/{announcement.id}',
                'title': announcement.title,
                'date': announcement.date.isoformat() if announcement.date else None
            }
            
            # Send to all subscribed users
            result = _send_onesignal_notification(
                heading=heading,
                message=message,
                segments=["Total Subscriptions"],
                data=notification_data
            )
            
            print(f"[AnnouncementViewSet] Push notification sent: {result}")
            
        except Exception as e:
            # Log error but don't fail the announcement creation
            print(f"[AnnouncementViewSet] Failed to send push notification: {str(e)}")
    
def news(request):
    """Unified News page: shows Announcements, Events, and Holidays as cards.

    Scopes content visible to the user: institution-wide rows (department is
    null) plus rows for the user's department, if any.
    """
    dept_filter = Q(department__isnull=True)
    user_dept_id = None
    try:
        profile = getattr(request.user, 'profile', None)
        # Profile uses `department_fields` (FK), so the actual id attribute is
        # `department_fields_id`. Fall back to `department_id` for safety in
        # case other code paths populate it.
        if profile is not None:
            user_dept_id = (
                getattr(profile, 'department_fields_id', None)
                or getattr(profile, 'department_id', None)
            )
    except Exception:
        user_dept_id = None
    if user_dept_id:
        dept_filter = dept_filter | Q(department_id=user_dept_id)

    # [Classedge LMS] Subject-scoped announcements: include those for subjects
    # the current user teaches (any role) or is actively enrolled in for the
    # current semester. Combined with `dept_filter` via OR so a user sees
    # institution-wide + their department + their class announcements.
    subject_ids = _user_subject_ids_for_current_sem(request.user)
    ann_filter = dept_filter & Q(subject__isnull=True)
    if subject_ids:
        ann_filter = ann_filter | Q(subject_id__in=subject_ids)

    announcements = (
        Announcement.objects
        .filter(ann_filter)
        .select_related('created_by', 'department', 'subject')
        .prefetch_related('events')
        .order_by('-date', '-created_at')
        .distinct()
    )
    events = (
        Event.objects
        .filter(dept_filter)
        .select_related('created_by', 'department')
        .order_by('start_date', 'time')
    )
    holidays = (
        Holiday.objects
        .filter(dept_filter)
        .select_related('department')
        .order_by('date')
    )

    # Campus News (Facebook posts) — cached for 10 minutes so we don't hit
    # Graph API on every page load.
    articles = cache.get("facebook_articles")
    if articles is None:
        try:
            articles = fetch_facebook_posts() or []
        except Exception:
            articles = []
        cache.set("facebook_articles", articles, timeout=600)

    return render(request, 'calendar/news.html', {
        'announcements': announcements,
        'events': events,
        'holidays': holidays,
        'announcement_count': announcements.count(),
        'event_count': events.count(),
        'holiday_count': holidays.count(),
        'articles': articles,
    })

def event_list(request):
    return render(request, 'calendar/event.html')

def announcement_details(request, id):
    announcement = get_object_or_404(Announcement, id=id)
    return render(request, 'calendar/announcement_details.html', {'announcement': announcement})


def event_details(request, id):
    event = get_object_or_404(Event, id=id)
    is_student_role = (
        request.user.is_authenticated
        and getattr(request.user, "is_student", False)
    )
    return render(request, 'calendar/event_details.html', {
        'event': event,
        'is_student_role': is_student_role,
    })


# ──────────────────────────────────────────────────────────────────────
# Subject-level announcements: CRUD page + JSON API for teachers.
# Visibility on /campus/news/ is handled inside `news()` via the
# subject-scoped filter above.
# ──────────────────────────────────────────────────────────────────────

def _teacher_subjects_queryset(user):
    try:
        from subject.models.subject_model import Subject
    except Exception:
        return None
    return Subject.objects.filter(
        Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user)
    ).distinct()


@login_required
def subject_announcements_page(request):
    """Teacher-facing page listing each subject and its announcements."""
    subjects_qs = _teacher_subjects_queryset(request.user)
    if subjects_qs is None:
        subjects_qs = []
    subjects = []
    for s in subjects_qs:
        anns = Announcement.objects.filter(subject=s).order_by('-date', '-created_at')
        subjects.append({
            'id': s.id,
            'name': getattr(s, 'subject_name', None) or str(s),
            'code': getattr(s, 'subject_code', '') or '',
            'announcements': anns,
        })
    return render(request, 'calendar/subject_announcements.html', {
        'subjects': subjects,
        'has_subjects': bool(subjects),
    })


@api_view(['GET', 'POST'])
def subject_announcement_list_api(request):
    """List or create subject announcements. Teacher must own the subject."""
    teacher_subs = _teacher_subjects_queryset(request.user)
    if teacher_subs is None:
        return Response({'error': 'Subject module unavailable.'}, status=500)

    if request.method == 'GET':
        subject_id = request.query_params.get('subject_id')
        qs = Announcement.objects.filter(subject__in=teacher_subs)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        qs = qs.order_by('-date', '-created_at')
        data = [{
            'id': a.id,
            'title': a.title,
            'description': a.description,
            'date': a.date.isoformat() if a.date else None,
            'subject_id': a.subject_id,
            'subject_name': getattr(a.subject, 'subject_name', None) if a.subject_id else None,
            'created_at': a.created_at.isoformat() if a.created_at else None,
        } for a in qs]
        return Response(data, status=200)

    # POST
    subject_id = request.data.get('subject_id') or request.data.get('subjectId')
    title = (request.data.get('title') or '').strip()
    description = (request.data.get('description') or '').strip()
    date_str = (request.data.get('date') or '').strip()

    if not subject_id or not title:
        return Response({'error': 'subject_id and title are required.'}, status=400)

    if not teacher_subs.filter(id=int(subject_id)).exists():
        return Response({'error': 'You do not teach this subject.'}, status=403)

    from datetime import datetime
    parsed_date = None
    if date_str:
        try:
            parsed_date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return Response({'error': 'Invalid date.'}, status=400)

    ann = Announcement.objects.create(
        title=title,
        description=description or None,
        date=parsed_date or date.today(),
        subject_id=int(subject_id),
        created_by=request.user,
    )
    return Response({
        'id': ann.id,
        'title': ann.title,
        'description': ann.description,
        'date': ann.date.isoformat() if ann.date else None,
        'subject_id': ann.subject_id,
    }, status=201)


@api_view(['PUT', 'PATCH', 'DELETE'])
def subject_announcement_detail_api(request, pk):
    teacher_subs = _teacher_subjects_queryset(request.user)
    if teacher_subs is None:
        return Response({'error': 'Subject module unavailable.'}, status=500)

    try:
        ann = Announcement.objects.get(pk=pk)
    except Announcement.DoesNotExist:
        return Response({'error': 'Not found.'}, status=404)

    if not ann.subject_id or not teacher_subs.filter(id=ann.subject_id).exists():
        return Response({'error': 'You can only modify announcements for subjects you teach.'}, status=403)

    if request.method == 'DELETE':
        ann.delete()
        return Response(status=204)

    title = request.data.get('title')
    description = request.data.get('description')
    date_str = request.data.get('date')

    if title is not None:
        ann.title = title.strip()
    if description is not None:
        ann.description = description.strip() or None
    if date_str:
        from datetime import datetime
        try:
            ann.date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return Response({'error': 'Invalid date.'}, status=400)
    ann.save()
    return Response({
        'id': ann.id,
        'title': ann.title,
        'description': ann.description,
        'date': ann.date.isoformat() if ann.date else None,
        'subject_id': ann.subject_id,
    }, status=200)
