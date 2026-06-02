
from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from course.models import Semester
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from subject.models import Subject 
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from rest_framework import generics, mixins
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import NotificationSerializer
from .models import Notification
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.pagination import PageNumberPagination
import onesignal
from onesignal.api import default_api
from onesignal.model.string_map import StringMap
from onesignal.model.notification import Notification as OneSignalNotification
from rest_framework.views import APIView
from django.conf import settings
from accounts.models import CustomUser


ONE_SIGNAL_APP_ID = settings.ONE_SIGNAL_APP_ID
ONE_SIGN_API_KEY = settings.ONE_SIGN_API_KEY
ORGANIZATION_API_KEY = settings.ORGANIZATION_API_KEY
ONE_SIGNAL_ANDROID_CHANNEL_ID = settings.ONE_SIGNAL_ANDROID_CHANNEL_ID
ONE_SIGNAL_ANDROID_PRIORITY = 10
ONE_SIGNAL_ANDROID_VISIBILITY = 1

def _send_onesignal_notification(
    heading,
    message,
    user_ids=None,
    external_ids=None,
    segments=None,
    data=None,
    app_id=ONE_SIGNAL_APP_ID,
    rest_api_key=ONE_SIGN_API_KEY,
    organization_api_key=ORGANIZATION_API_KEY
):
    import requests
    import json
    """
    Utility function to send a push notification via OneSignal.
    
    Args:
        heading (str): The notification heading/title
        message (str): The notification message content
        user_ids (list, optional): List of specific OneSignal player IDs to target
        external_ids (list, optional): List of external user IDs (Django user IDs) to target
        segments (list, optional): List of segments to target (e.g., ['Subscribed Users', 'Active Users'])
        data (dict, optional): Additional data to send with the notification
        app_id (str): OneSignal App ID
        rest_api_key (str): OneSignal REST API Key
        organization_api_key (str): OneSignal Organization API Key
    
    Returns:
        dict: Response from OneSignal API with notification ID and recipient count
        
    Raises:
        Exception: If notification sending fails
    
    Example:
        # Send to all subscribed users
        result = _send_onesignal_notification(
            heading='New Assignment',
            message='You have a new assignment due tomorrow',
            segments=['Subscribed Users']
        )
        
        # Send to specific users by external ID (Django user ID)
        result = _send_onesignal_notification(
            heading='Grade Posted',
            message='Your grade for Quiz 1 is now available',
            external_ids=['1', '2', '3'],
            data={'quiz_id': 123, 'type': 'grade'}
        )
        
        # Send to specific users by player ID
        result = _send_onesignal_notification(
            heading='Grade Posted',
            message='Your grade for Quiz 1 is now available',
            user_ids=['player-id-1', 'player-id-2'],
            data={'quiz_id': 123, 'type': 'grade'}
        )
    """
    try:
        print(f"[OneSignal] Preparing notification: heading='{heading}', message='{message}'")
        print(f"[OneSignal] Target: user_ids={user_ids}, external_ids={external_ids}, segments={segments}")
        print(f"[OneSignal] Android config -> channel_id={ONE_SIGNAL_ANDROID_CHANNEL_ID!r}, priority={ONE_SIGNAL_ANDROID_PRIORITY}, visibility={ONE_SIGNAL_ANDROID_VISIBILITY}")

        # Use direct REST API for external_ids to avoid SDK bug
        if external_ids:
            print(f"[OneSignal] Using REST API for external_ids: {external_ids}")

            payload = {
                'app_id': app_id,
                'contents': {'en': message},
                'headings': {'en': heading},
                'include_aliases': {
                    'external_id': [str(eid) for eid in external_ids]
                },
                'target_channel': 'push',
                'priority': ONE_SIGNAL_ANDROID_PRIORITY,
                'android_visibility': ONE_SIGNAL_ANDROID_VISIBILITY,
            }
            if ONE_SIGNAL_ANDROID_CHANNEL_ID:
                payload['android_channel_id'] = ONE_SIGNAL_ANDROID_CHANNEL_ID

            if data:
                payload['data'] = data
                print(f"[OneSignal] Additional data: {data}")
            
            print(f"[OneSignal] REST API Payload: {json.dumps(payload, indent=2)}")
            
            headers = {
                'Content-Type': 'application/json; charset=utf-8',
                'Authorization': f'Key {rest_api_key}'
            }
            
            response = requests.post(
                'https://api.onesignal.com/notifications',
                headers=headers,
                json=payload
            )
            
            result = response.json()
            print(f"[OneSignal] REST API Status: {response.status_code}")
            print(f"[OneSignal] REST API Response: {result}")
            
            if response.status_code == 200 and result.get('id'):
                return {
                    'success': True,
                    'notification_id': result.get('id'),
                    'recipients': result.get('recipients'),
                    'errors': result.get('errors')
                }
            else:
                error_msg = result.get('errors', 'Unknown error')
                return {
                    'success': False,
                    'error': f"OneSignal API error: {error_msg}",
                    'notification_id': None,
                    'recipients': result.get('recipients', 0)
                }
        
        configuration = onesignal.Configuration(
            app_key=rest_api_key,
            user_key=organization_api_key,
        )

        with onesignal.ApiClient(configuration) as api_client:
            client = default_api.DefaultApi(api_client)

            notification_params = {
                'app_id': app_id,
                'contents': StringMap(en=message),
                'headings': StringMap(en=heading),
                'priority': ONE_SIGNAL_ANDROID_PRIORITY,
                'android_visibility': ONE_SIGNAL_ANDROID_VISIBILITY,
            }
            if ONE_SIGNAL_ANDROID_CHANNEL_ID:
                notification_params['android_channel_id'] = ONE_SIGNAL_ANDROID_CHANNEL_ID

            # Validate and map segment names
            VALID_SEGMENTS = {
                'all': 'Subscribed Users',
                'subscribed': 'Subscribed Users',
                'active': 'Active Users',
                'inactive': 'Inactive Users',
            }
            
            if user_ids:
                notification_params['include_player_ids'] = user_ids
                print(f"[OneSignal] Targeting {len(user_ids)} specific user(s) by player_id")
            elif segments:
                # Map segment names to valid OneSignal segments
                mapped_segments = []
                for seg in segments:
                    seg_lower = seg.lower()
                    if seg_lower in VALID_SEGMENTS:
                        mapped_segments.append(VALID_SEGMENTS[seg_lower])
                    else:
                        # Use as-is if not in mapping (might be a custom segment)
                        mapped_segments.append(seg)
                
                notification_params['included_segments'] = mapped_segments
                print(f"[OneSignal] Targeting segments: {segments} -> {mapped_segments}")
            else:
                notification_params['included_segments'] = ['Subscribed Users']
                print("[OneSignal] Targeting default segment: Subscribed Users")

            if data:
                notification_params['data'] = data
                print(f"[OneSignal] Additional data: {data}")

            notification = OneSignalNotification(**notification_params)
            print(f"[OneSignal] Notification object created: {notification}")
            
            response = client.create_notification(notification)
            print(f"[OneSignal] API Response: {response}")
            print(f"[OneSignal] Response Type: {type(response)}")
            print(f"[OneSignal] Response Dir: {dir(response)}")
            
            # Convert response to dict for JSON serialization
            notification_id = str(response.id) if response.id else ''
            recipients = getattr(response, 'recipients', None)
            errors = response.errors if hasattr(response, 'errors') else {}
            
            print(f"[OneSignal] Notification ID: {notification_id}")
            print(f"[OneSignal] Recipients: {recipients if recipients else 'N/A'}")
            
            # Extract detailed error information
            error_details = []
            
            # Check for errors object with _data_store
            if hasattr(errors, '_data_store') and errors._data_store:
                error_details.append(f"Error data: {errors._data_store}")
                print(f"[OneSignal] Errors _data_store: {errors._data_store}")
            
            # Check for invalid identifiers
            for attr in ['invalid_player_ids', 'invalid_external_user_ids']:
                if hasattr(errors, attr):
                    invalid_ids = getattr(errors, attr)
                    if invalid_ids:
                        error_details.append(f"{attr}: {invalid_ids}")
                        print(f"[OneSignal] {attr}: {invalid_ids}")
            
            # Check response for additional error fields
            for attr in ['warnings']:
                if hasattr(response, attr):
                    warnings = getattr(response, attr)
                    if warnings:
                        error_details.append(f"Warnings: {warnings}")
                        print(f"[OneSignal] {attr}: {warnings}")
            
            # Empty notification_id means OneSignal rejected the request
            if not notification_id:
                error_msg = "OneSignal rejected the notification. "
                
                # Provide specific error guidance
                if not recipients or recipients == 0:
                    error_msg += "No recipients found. Possible causes: "
                    if segments:
                        error_msg += f"Segment '{segments}' may not exist or has no subscribers. "
                    error_msg += "Ensure users are subscribed to push notifications in OneSignal."
                else:
                    error_msg += "Check app_id, API keys, and segment configuration in OneSignal dashboard."
                
                if error_details:
                    error_msg += f" Details: {'; '.join(error_details)}"
                
                print(f"[OneSignal] ERROR: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'notification_id': None,
                    'recipients': recipients
                }

            return {
                'success': True,
                'notification_id': notification_id,
                'recipients': recipients,
                'errors': str(errors) if errors else None
            }

    except Exception as e:
        print(f"[OneSignal] ERROR: {str(e)}")
        import traceback
        print(f"[OneSignal] Traceback: {traceback.format_exc()}")
        return {
            'success': False,
            'error': str(e)
        }


class SendPushNotificationView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication, JWTAuthentication]

    def post(self, request):
        heading = request.data.get('heading')
        message = request.data.get('message')
        # Expecting a list of Django User IDs from the frontend
        target_user_ids = request.data.get('user_ids', []) 
        entity_type = request.data.get('entity_type', 'general')
        entity_id = request.data.get('entity_id', 0)
        
        if not heading or not message:
            return Response({'error': 'Heading and message required'}, status=400)

        # Fetch the User objects
        users = CustomUser.objects.filter(id__in=target_user_ids)
        
        if not users.exists():
            return Response({'error': 'No valid users found'}, status=400)

        # Create notification records - signal will automatically send push notifications
        notifications_created = 0
        for user in users:
            Notification.objects.create(
                user_id=user,
                name=heading,
                entity_type=entity_type,
                entity_id=entity_id,
                message=message,
                created_by=request.user,
                is_read=False
            )
            notifications_created += 1
        
        return Response({
            'success': True, 
            'detail': f'{notifications_created} notification(s) created and push notifications sent automatically via signal.'
        })


def send_push_notification(request):
    return render(request, 'logs/push_notification.html')


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow URL parameter to override
    max_page_size = 100  # Maximum allowed page size


class NotificationList(generics.ListAPIView):
    serializer_class = NotificationSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return notifications for the current user
        return Notification.objects.filter(user_id=self.request.user).order_by('-created_at')
      
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            page = self.paginate_queryset(queryset)

            unread_count = queryset.filter(is_read=False).count()

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response = self.get_paginated_response(serializer.data)
                response.data['count'] = unread_count 
                return response

            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "count": unread_count,
                "results": serializer.data
            })

        except Notification.DoesNotExist:
            return Response({"message": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
 
class NotificationCount(generics.ListAPIView):
    serializer_class = NotificationSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only return notifications for the current user
        return Notification.objects.filter(user_id=self.request.user).order_by('-created_at')
      
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()

            unread_count = queryset.filter(is_read=False).count()

            return Response({
                "count": unread_count,
            })

        except Notification.DoesNotExist:
            return Response({"message": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
 
    
class NotificationDetail(mixins.UpdateModelMixin, generics.RetrieveAPIView):
    serializer_class = NotificationSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only the current user's notifications
        return Notification.objects.filter(user_id=self.request.user)

    # GET: retrieve + mark THIS notification as read
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Notification.objects.filter(
            pk=instance.pk, user_id=request.user, is_read=False
        ).update(is_read=True)
        instance.refresh_from_db(fields=["is_read"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # PATCH: allow marking as read even with an empty body
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        Notification.objects.filter(
            pk=instance.pk, user_id=request.user, is_read=False
        ).update(is_read=True)
        instance.refresh_from_db(fields=["is_read"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
        

    def handle_exception(self, exc):
        if isinstance(exc, MethodNotAllowed):
            return Response({"message": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        if isinstance(exc, Notification.DoesNotExist):
            return Response({"message": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        return super().handle_exception(exc)
    
    

@login_required
@permission_required('logs.view_subjectlog', raise_exception=True)
def subjectLogDetails(request):
    user = request.user

    # Get the current semester
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not current_semester:
        messages.error(request, "No active semester found.")
        return render(request, 'logs/subjectLogDetails.html', {'latest_logs': []})

    role_name = user.role_name

    # Get logs based on user role
    if role_name == 'teacher':
        subjects = Subject.objects.filter(assign_teacher=user)
    elif role_name == 'student':
        subjects = Subject.objects.filter(subjectenrollment__student=user, subjectenrollment__semester=current_semester)
    else:
        subjects = Subject.objects.all()  # Admins or other roles can see all logs

    # Fetch latest logs for these subjects
    latest_logs = SubjectLog.objects.filter(subject__in=subjects).order_by('-created_at')[:5]

    # Add student logs only for relevant subjects
    for log in latest_logs:
        log.student_logs = StudentActivityLog.objects.filter(subject=log.subject, activity=log.activity).order_by('-submission_time')

    return render(request, 'logs/subjectLogDetails.html', {
        'latest_logs': latest_logs,
    })


@login_required
@permission_required('logs.view_subjectlog', raise_exception=True)
def coil_subect_update(request):
    user = request.user

    # Get the current semester
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not current_semester:
        messages.error(request, "No active semester found.")
        return render(request, 'course/coil_latest_update.html', {'latest_logs': []})

    role_name = user.role_name

    # Apply is_coil=True for all roles
    if role_name == 'teacher':
        subjects = Subject.objects.filter(assign_teacher=user, is_coil=True)
    elif role_name == 'student':
        subjects = Subject.objects.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester=current_semester,
            is_coil=True
        )
    else:
        subjects = Subject.objects.filter(is_coil=True)

    latest_logs = SubjectLog.objects.filter(subject__in=subjects).order_by('-created_at')[:5]

    for log in latest_logs:
        log.student_logs = StudentActivityLog.objects.filter(
            subject=log.subject,
            activity=log.activity
        ).order_by('-submission_time')

    return render(request, 'course/coil_latest_update.html', {
        'latest_logs': latest_logs,
    })

@login_required
@permission_required('logs.view_subjectlog', raise_exception=True)
def hali_subect_update(request):
    user = request.user

    # Get the current semester
    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not current_semester:
        messages.error(request, "No active semester found.")
        return render(request, 'course/hali_latest_update.html', {'latest_logs': []})

    role_name = user.role_name

    # Apply is_hali=True for all roles
    if role_name == 'teacher':
        subjects = Subject.objects.filter(assign_teacher=user, is_hali=True)
    elif role_name == 'student':
        subjects = Subject.objects.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester=current_semester,
            is_hali=True
        )
    else:
        subjects = Subject.objects.filter(is_hali=True)

    latest_logs = SubjectLog.objects.filter(subject__in=subjects).order_by('-created_at')[:5]

    for log in latest_logs:
        log.student_logs = StudentActivityLog.objects.filter(
            subject=log.subject,
            activity=log.activity
        ).order_by('-submission_time')

    return render(request, 'course/hali_latest_update.html', {
        'latest_logs': latest_logs,
    })

@login_required
@permission_required('logs.view_studentactivitylog', raise_exception=True)
def student_log(request):
    user = request.user

    # Filter logs based on user's role
    if user.is_teacher:
        student_logs = StudentActivityLog.objects.filter(subject__assign_teacher=user).order_by('-submission_time')
    elif user.is_student:
        student_logs = StudentActivityLog.objects.filter(student=user).order_by('-submission_time')
    else:
        student_logs = StudentActivityLog.objects.all().order_by('-submission_time')

    # Group logs by subject
    grouped_logs = {}
    for log in student_logs:
        if log.subject.subject_name not in grouped_logs:
            grouped_logs[log.subject.subject_name] = []
        grouped_logs[log.subject.subject_name].append(log)

    return render(request, 'logs/student_activity_log.html', {
        'grouped_logs': grouped_logs,
    })

@login_required
def mark_log_as_read(request, log_id):
    if request.user.is_authenticated:
        log = get_object_or_404(SubjectLog, id=log_id)
        user_log, created = UserSubjectLog.objects.get_or_create(user=request.user, subject_log=log)
        user_log.read = True
        user_log.save()
        return redirect('material-list', id=log.subject.id)


@login_required
def open_subject_log(request, log_id):
    """Mark a UserSubjectLog as read for the current user, then redirect
    to ?next=<url>. Used by the bell popover so clicking an unread
    subject-log notification persists the read flag *and* lands the user
    on the relevant classroom — no JS race."""
    log = get_object_or_404(SubjectLog, id=log_id)
    UserSubjectLog.objects.update_or_create(
        user=request.user, subject_log=log, defaults={'read': True}
    )
    target = request.GET.get('next') or '/'
    if not target.startswith('/') or target.startswith('//'):
        target = '/'
    return redirect(target)


@login_required
def open_academic_notification(request, notif_id):
    """Mark an academic Notification read, then redirect to ?next= (or its
    own path). Mirrors open_subject_log so the bell flips read on click."""
    n = get_object_or_404(Notification, pk=notif_id, user_id=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=['is_read'])
    target = request.GET.get('next') or n.path or '/'
    if not target.startswith('/') or target.startswith('//'):
        target = '/'
    return redirect(target)


@require_POST
@csrf_protect
def mark_notification_read(request, log_id):
    try:
        user_log = UserSubjectLog.objects.get(subject_log_id=log_id, user=request.user)
        user_log.read = True
        user_log.save()
        return JsonResponse({'success': True})
    except UserSubjectLog.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@require_POST
@csrf_protect
def mark_notification_read(request, log_id):
    try:
        user_log = UserSubjectLog.objects.get(subject_log_id=log_id, user=request.user)
        user_log.read = True
        user_log.save()
        return JsonResponse({'success': True})
    except UserSubjectLog.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@require_POST
@csrf_protect
def mark_all_notifications_read(request):
    UserSubjectLog.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({'success': True})