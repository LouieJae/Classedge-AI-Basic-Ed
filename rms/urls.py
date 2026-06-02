from django.urls import path
from .views import *

urlpatterns = [
    path('academic_terms/', academic_terms, name='academic_terms'),
    path('term_data/', term_data, name='term_data'),
    path('class_schedule/', class_schedule, name='class_schedule'),
    path('student_enrollment/', student_enrollment, name='student_enrollment'),
    path('student_data/', student_data, name='student_data'),
    path('courses/', courses, name='rms_courses'),

    path('student_finances/', student_finances, name='student_finances'),
    path('api/finance/', StudentFinancesAPIView.as_view(), name='api_student_finances'),
    path('api/academic-terms/', TermsAPIView.as_view(), name='api_student_finances'),
    path('api/academic-records/', GradesAPIView.as_view(), name='api_student_finances'),

    path('student_soa/', student_soa, name='student_soa'),
    path('fetch_student_total_payment/', fetch_student_total_payment, name='fetch_student_total_payment'),

    path('rms_data_import/', rms_data_import, name='rms_data_import'),
    path('rms_data_import/task_status/<str:task_id>/', rms_import_task_status, name='rms_import_task_status'),
]
