from django.urls import path
from gradebookcomponent.views import * 

urlpatterns = [
    # Gradebook
    path('gradebook/list/', grade_book, name='grade-book'), 
    path('gradebook/create', create_grade_book, name='create-grade-book'),
    path('gradebook/update/<int:pk>/', update_grade_book, name='update-grade-book'),

    path('gradebook/copy/', copy_grade_book, name='copy-grade-book'),
    path('get-terms/<int:semester_id>/', get_terms_and_subjects, name='get_terms_and_subjects'),

    path('delete-grade-book/<int:pk>/', delete_grade_book, name='delete-grade-book'),
    path('delete_multiple_gradebookcomponents/', delete_multiple_gradebookcomponents, name='delete_multiple_gradebookcomponents'),

    #display score for student for each activity
    path('grades/score-sheet/<str:activity_id>/', score_sheet, name='score-sheet'),
    path('teacherActivityViewCM/<str:activity_id>/', teacherActivityViewCM, name='teacherActivityViewCM'),
    path('grades/my-assessment-score/<str:activity_id>/', my_assessment_score, name='my-assessment-score'),

    #dislay student total score for a particular activity type
    path('studentTotalScore/<int:student_id>/<int:subject_id>/', studentTotalScore, name='studentTotalScore'),
    #dislay student total grade for a particular activity type
    path('studentTotalScoreForActivity/', studentTotalScoreForActivityType, name='studentTotalScoreForActivity'),

    # Termbook
    path('termbook/list/', term_book, name='term-book'),
    path('termbook/create/', create_term_book, name='create-term-book'),
    path('termbook/update/<int:id>/', update_term_book, name='update-term-book'),
    path('termbook/view/<int:id>/', view_term_book, name='view-term-book'),
    path('termbook/delete/<int:id>/', delete_term_book, name='delete-term-book'),

    #json format data
    path('getSubjects/', getSubjects, name='getSubjects'),
    path('get-used-activity-types/', get_used_activity_types, name='get_used_activity_types'),
    path('getSemesters/', getSemesters, name='getSemesters'),
    #allow grade visibility
    path('allow_grade_visibility/<int:student_id>/', allowGradeVisibility, name='allow_grade_visibility'),
    
    # Grade visibility management
    path('manage_grade_visibility/', manage_grade_visibility, name='manage_grade_visibility'),
    path('toggle_grade_visibility/', toggle_grade_visibility, name='toggle_grade_visibility'),

    #crud for transmutation
    path('transmutation/list/', transmutation_list, name='transmutation-list'),
    path('transmutation/create/', create_transmutation, name='create-transmutation'),
    path('transmutation/update/<int:id>/', update_transmutation, name='update-transmutation'),
    path('transmutation/delete/<int:id>/', delete_transmutation, name='delete-transmutation'),
    path('get_transmutation_rules/', get_transmutation_rules, name='get_transmutation_rules'),
    
    #student grades
    path('my/grades/', student_grades, name='my-grades'),
    path('grades/', grades, name='grades'),
    path('export_grades_excel/', export_grades_excel, name='export_grades_excel'),
    path('export_my_grades_excel/', export_my_grades_excel, name='export_my_grades_excel'),

    path('api/transmutation_rules/', get_transmutation_rules, name='transmutation-rules'),

    # --- [Classedge LMS] Instructor grading surface ---
    path('gradebook/', gradebook_home, name='gradebook_home'),
    path('gradebook/course/<int:subject_id>/', subject_gradebook, name='gradebook_subject'),
    path('gradebook/course/<int:subject_id>/export.csv', subject_gradebook_csv, name='gradebook_subject_csv'),
    path('gradebook/course/<int:subject_id>/export.xlsx', subject_gradebook_xlsx, name='gradebook_subject_xlsx'),
    path('gradebook/queue/', grading_queue, name='gradebook_queue'),
    path('gradebook/grade/<str:student_activity_id>/', grade_submission, name='gradebook_grade'),
    path('gradebook/override/<str:student_activity_id>/', override_score, name='gradebook_override'),
]