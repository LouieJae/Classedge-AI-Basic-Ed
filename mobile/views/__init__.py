from .student_question_views import StudentQuestionCreateView
from .lesson_activity_views import LessonActivityListView, LessonRetrieveView
from .student_activity_views import StudentActivityListView, ActivityBatchSubmitView
from .subject_enrollment_views import SubjectEnrollmentListView, SubjectEnrollmentRetrieveView
from .activity_question_views import ActivityQuestionListView, ActivityAutosaveView
from .subject_lesson_views import SubjectLessonListView, StudentsBySubjectView
from .activity_details import ActivityDetailsView, PendingStudentActivitiesViewSet, ActivityTimerView, ActivityViewSet
from .student_per_subject_views import StudentsPerSubjectView
from .user_view_profile import UserViewProfileView, OnboardingView, otp_request_api, otp_verify_api, set_new_password_api
from .retake_views import RetrieveAttempt, RetakeView
from .retake_record_views import RetakeRecordViewSet, RetakeRecordDetailViewSet
from .schedule_views import CurrentNextScheduleAPI
from .student_activity_views import ActivityStudentViewSet
from .attachment_views import AttachmentViewSet

all = [
    LessonActivityListView,
    LessonRetrieveView,
    StudentActivityListView,
    StudentQuestionCreateView,
    ActivityQuestionListView,
    ActivityDetailsView,
    SubjectLessonListView,
    ActivityBatchSubmitView,
    SubjectEnrollmentListView,
    SubjectEnrollmentRetrieveView,
    StudentsPerSubjectView,
    UserViewProfileView,
    PendingStudentActivitiesViewSet,
    ActivityAutosaveView,
    ActivityTimerView,
    CurrentNextScheduleAPI,
    OnboardingView,
    otp_request_api,
    otp_verify_api,
    set_new_password_api,
    RetrieveAttempt,
    RetakeView,
    RetakeRecordViewSet,
    RetakeRecordDetailViewSet,
    ActivityViewSet,
    ActivityStudentViewSet,
    AttachmentViewSet,
    StudentsBySubjectView,
]