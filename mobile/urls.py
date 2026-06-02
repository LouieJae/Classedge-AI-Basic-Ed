from django.urls import path, include
from mobile.views import *

from rest_framework.routers import DefaultRouter
router = DefaultRouter()

router.register(r'activities/pending', PendingStudentActivitiesViewSet, basename='pending_activities')
router.register(r'activity_retakerecord', RetakeRecordViewSet, basename='retake_record')
router.register(r'activity_retakerecorddetail', RetakeRecordDetailViewSet, basename='retake_record_detail')
router.register(r'activity_activity', ActivityViewSet, basename='activity_activity')
router.register(r'activity_studentactivity', ActivityStudentViewSet, basename='activity_studentactivity')
router.register(r'mobile_attachment', AttachmentViewSet, basename='attachment')

urlpatterns = [
    path('api/', include(router.urls)),

    # Activities
    path('api/activities/<str:activity_id>/questions/', ActivityQuestionListView.as_view(), name='activity-questions'),

    path('api/activity_activity/<str:activity_id>/', ActivityBatchSubmitView.as_view(), name='submit-all-questions'),

    path('api/activities/<str:id>/', ActivityDetailsView.as_view(), name='activity-details'),

    # Subjects
    path("api/subject/<int:subject_id>/students/", StudentsPerSubjectView.as_view(), name="subject-enrollments"),
    path('api/subject/<int:id>/', SubjectEnrollmentRetrieveView.as_view(), name='subjects'),
    path('api/subject/<int:subject_id>/lessons/', SubjectLessonListView.as_view(), name='lessons'),
    path('api/subject/<int:subject_id>/activities/', LessonActivityListView.as_view(), name='lesson-activities'),
    path('api/subject/lessons/activities/<int:subject_id>/', StudentActivityListView.as_view(), name='submit-activity'),
    path('api/lessons/<int:lesson_id>/', LessonRetrieveView.as_view(), name='lesson'),

    path('api/activities/<str:activity_id>/autosave/', ActivityAutosaveView.as_view(), name='activity-autosave'),

    path('api/activities/<str:activity_id>/timer/', ActivityTimerView.as_view(), name='activity-timer'),

    path("api/subject/<int:subject_id>/students/", StudentsBySubjectView.as_view(), name="subject-enrollments"),

    # Schedule
    path('api/class_schedule/', CurrentNextScheduleAPI.as_view(), name='current-next-schedule-api'),

    # User
    path('api/accounts_profile/<int:id>/', UserViewProfileView.as_view(), name='user-profile'),
    path('api/accounts_customuser/<int:id>/', OnboardingView.as_view(), name='onboarding'),
    path("api/accounts_customuser/request-otp/", otp_request_api, name="otp_request_api"),
    path("api/accounts_customuser/verify-otp/", otp_verify_api, name="otp_verify_api"),
    path("api/accounts_customuser/reset-password/", set_new_password_api, name="set_new_password_api"),

    # Attempts
    path('api/attempts/<int:attempt_id>/', RetrieveAttempt.as_view(), name='attempt-detail'),
    path('api/activities/<str:activity_id>/attempt/start/', RetakeView.as_view(), name='retake'),
]