from django.urls import path
from .views import *

urlpatterns = [
    path('subjectLogDetails/', subjectLogDetails, name='subjectLogDetails'),
    path('coil_subect_update/', coil_subect_update, name='coil_subect_update'),
    path('hali_subect_update/', hali_subect_update, name='hali_subect_update'),
    path('student_log/', student_log, name='student_log'),
    path('logs/read/<int:log_id>/', mark_log_as_read, name='mark_log_as_read'),
    path('logs/open/<int:log_id>/', open_subject_log, name='open_subject_log'),
    path('notification/academic/<int:notif_id>/open/', open_academic_notification, name='open_academic_notification'),
    path('mark-notification-read/<int:log_id>/', mark_notification_read, name='mark_notification_read'),
    path('mark-all-notifications-read/', mark_all_notifications_read, name='mark_all_notifications_read'),

    # Mobile
    path('api/notifications/', NotificationList.as_view(), name='user_notifications_log_list'),
    path('api/notifications/count/', NotificationCount.as_view(), name='user_notifications_log_count'),
    path('api/logs_notification/<int:pk>/', NotificationDetail.as_view(), name='user_notifications_log_detail'),
    
    path('api/send_push_notification/', SendPushNotificationView.as_view(), name='send_push_notification_api'),

    path('send_push_notification/', send_push_notification, name='send_push_notification')
]
