from django.urls import path, include
from course.views import *
from course.utils import *

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'term', TermViewSet, basename='term')

urlpatterns = [
    path('api/', include(router.urls)),
    
    # Attendance Views
    path('attendance/record_attendanceCM/<int:subject_id>/', record_attendanceCM, name='record_attendanceCM'),
    path('record-attendance<int:subject_id>/', record_attendance, name='record-attendance'),
    path('attendance/self-mark/<int:subject_id>/', student_self_mark_attendance, name='student_self_mark_attendance'),
    path('attendance/toggle-self/<int:subject_id>/', toggle_self_attendance, name='toggle_self_attendance'),
    path('attendance_list/<int:subject_id>/', attendance_list, name='attendance_list'),
    path('attendance_list_CM/<int:subject_id>/', attendance_list_CM, name='attendance_list_CM'),
    path('update_attendace/<int:id>/', update_attendance, name='update_attendace'),
    path('update_attendance_CM/<int:id>/', update_attendance_CM, name='update_attendance_CM'),

    # Attendance Status
    path('status/add-points/', add_points, name='add-points'),
    path('status/list/', status_list, name='status-list'),
    path('status/update-points/<int:id>/', update_points, name='update-points'),
    path('status/delete-points/<int:id>/', delete_points, name='delete-points'),

    # Attendance Views
    path('attendance/report/', attendance_report, name='attendance-report'),
    path('student_subject_attendance/<int:subject_id>/student/<int:student_id>/',student_subject_attendance, name='student_subject_attendance'),
    path('student_subject_attendanceCM/<int:subject_id>/student/<int:student_id>/',student_subject_attendanceCM, name='student_subject_attendanceCM'),
    path('export_attendance/<int:subject_id>/', export_attendance_by_date_range, name='export_attendance_by_date_range'),
    path('export_attendanceCM/<int:subject_id>/', export_attendance_by_date_rangeCM, name='export_attendance_by_date_rangeCM'),
    path('export_student_attendance/<int:subject_id>/<int:student_id>/', export_student_attendance, name='export_student_attendance'),
    path('update_attendance_status/<int:attendance_id>/', update_attendance_status, name='update_attendance_status'),
    path('delete_attendance/<int:attendance_id>/', delete_attendance, name='delete_attendance'),
    path('get_attendance_statuses/', get_attendance_statuses, name='get_attendance_statuses'),

    # Classroom Views
    path('classroom_mode/<int:pk>/', classroom_mode,  name='classroom_mode'),
    
    # Coil and Hali Subject Views
    path('coil/course/list/', coil_subjectList, name='coil_subjectList'),
    path('hali/course/list/', hali_subjectList, name='hali_subjectList'),
    path('cte/course/list/', cte_subject_list, name='cte_subject_list'),
    
    # Enrollment Views
    path('enrollment/list/', enrollment_list, name='enrollment-list'),
    path('enrollment/bulk-drop/', bulk_drop_enrollments, name='bulk_drop_enrollments'),
    path('enrollment/drop-subject/<int:subject_id>/<int:semester_id>/', drop_all_in_subject, name='drop_all_in_subject'),
    path('enrollment/bulk-remove/', bulk_remove_enrollments, name='bulk_remove_enrollments'),
    path('enrollment/remove-subject/<int:subject_id>/<int:semester_id>/', remove_all_in_subject, name='remove_all_in_subject'),
    path('enroll/student/', EnrollStudentView.as_view(), name='enroll-student'),
    path('drop_student_from_subject/<int:enrollment_id>/', drop_student_from_subject, name='drop_student_from_subject'),
    path('restore_student_from_subject/<int:enrollment_id>/', restore_student_from_subject, name='restore_student_from_subject'),
    path('delete_student_from_subject/<int:enrollment_id>/', delete_student_from_subject, name='delete_student_from_subject'),
    path('import_and_export_enrollment_page/', import_and_export_enrollment_page, name='import_and_export_enrollment_page'),

    # Semester
    path('semester/list/', semester_list, name='semester-list'),
    path('semester/create/', create_semester, name='create-semester'),
    path('semester/update/<int:pk>/', update_semester, name='update-semester'),
    path('semester/delete/<int:pk>/', delete_semester, name='delete-semester'),
    path('end-semester/<int:pk>/', end_semester, name='end-semester'),

    # Course CM
    path('course/student/list/CM/<int:pk>/', subjectStudentListCM, name='subjectStudentListCM'),
    

    # Term Views
    path('term/list/', term_list, name='term-list'),
    path('term/create/', create_term, name='create-term'),
    path('term/update/<int:pk>/', update_term, name='update-term'),
    path('term/delete/<int:pk>/', delete_term, name='delete-term'),


    # Exort and Import Function
    path('import_students_and_enroll/', import_students_and_enroll, name='import_students_and_enroll'),
    path('export_students_with_subjects_csv/', export_students_with_subjects_csv, name='export_students_with_subjects_csv'),
    path('export_all_students_with_subjects_csv/', export_all_students_with_subjects_csv, name='export_all_students_with_subjects_csv'),


    path('api/enrolled_students/<int:subject_id>/', get_subject_students_api, name='get_subject_students_api'),

    # Classmates (student-facing)
    path('classmates/<int:subject_id>/', classmates, name='classmates'),
    
]