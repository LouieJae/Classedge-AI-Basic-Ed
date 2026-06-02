from django.urls import path, include
from activity.views import *
from rest_framework.routers import DefaultRouter
from .student_export_utils import export_student_data_csv
from .student_import_utils import import_student_data
from activity.views.legacy_redirect_views import (
    legacy_grade_individual_redirect,
    legacy_grade_individual_redirect_cm,
)

router = DefaultRouter()
router.register(r'activity_type', ActivityTypeViewSet, basename='activity_type')
router.register(r'rubrics', RubricsViewSet, basename='rubrics')
router.register(r'student_score', StudentScoreViewSet, basename='student_score')

urlpatterns = [
    path('api/', include(router.urls)),

    # ── Assessment CRUD ────────────────────────────────────────────────
    path('course/<int:subject_id>/assessment/add/', AddAssessmentView.as_view(), name='add-assessment'),
    path('assessment/update/<str:activity_id>/', UpdateAssessment, name='update-assessment'),
    # Click-to-edit (cl-edit-inline) — PATCH-only rename endpoint
    path('assessment/rename/<str:activity_id>/', rename_activity, name='rename-activity'),
    path('assessment/retake/<str:activity_id>/', RetakeAssessmentView.as_view(), name='retake-assessment'),
    path('assessment/delete/<str:activity_id>/', delete_assessment, name='delete-assessment'),
    path('course/<int:subject_id>/assessment-cm/add//', AddAssessmentViewCM.as_view(), name='add-assessment-cm'),
    path('assessment-cm/update/<str:activity_id>/', UpdateAssessmentCM, name='update-assessment-cm'),

    # ── Assessment list / detail / completion ──────────────────────────
    path('assessment/list/', assessment_list, name='assessment-list'),
    path('course/assessment/list/<int:subject_id>/', subject_assessment_list, name='subject-assessment-list'),
    path('assessment/list-registrar/<int:subject_id>/', assessment_list_registrar, name='assessment-list-registrar'),
    path('assessment/details/<str:activity_id>/', AssessmentDetailsView.as_view(), name='assessment-details'),
    path('assessment/completed/<int:score>/<str:activity_id>/<str:show_score>/', assessment_completed_view, name='assessment-completed'),
    path('assessment/detail-cm/<str:activity_id>/', AssessmentDetailViewCM.as_view(), name='assessment-detail-cm'),
    path('assessment/list-cm/<int:subject_id>/', assessment_list_cm, name='assessment-list-cm'),

    # ── Question / quiz-type sub-flows (kept under their own names) ────
    path('quiz_type/<str:activity_id>/', AddQuizTypeView.as_view(), name='add_quiz_type'),
    path('quiz_typeCM/<str:activity_id>/', AddQuizTypeViewCM.as_view(), name='add_quiz_typeCM'),
    path('add_question/<str:activity_id>/<int:quiz_type_id>/', AddQuestionView.as_view(), name='add_question'),
    path('add_questionCM/<str:activity_id>/<int:quiz_type_id>/', AddQuestionViewCM.as_view(), name='add_questionCM'),
    path('delete_temp_question/<str:activity_id>/<int:index>/', DeleteTempQuestionView.as_view(), name='delete_temp_question'),
    path('edit_question/<str:activity_id>/<int:index>/', UpdateQuestionView.as_view(), name='edit_question'),
    path('edit_questionCM/<str:activity_id>/<int:index>/', UpdateQuestionViewCM.as_view(), name='edit_questionCM'),
    path('display_question/<str:activity_id>/', DisplayQuestionsView.as_view(), name='display_question'),
    path('DisplayQuestionsViewCM/<str:activity_id>/', DisplayQuestionsViewCM.as_view(), name='DisplayQuestionsViewCM'),
    path('submit_answers/<str:activity_id>/', SubmitAnswersView.as_view(), name='submit_answers'),
    path('auto_submit_answers/<str:activity_id>/', AutoSubmitAnswersView.as_view(), name='auto_submit_answers'),
    path('grade_essays/<str:activity_id>/', GradeEssayView.as_view(), name='grade_essays'),
    path('grade_essaysCM/<str:activity_id>/', GradeEssayViewCM.as_view(), name='grade_essaysCM'),
    path('grade_individual_essay/<str:activity_id>/<int:student_question_id>/',
         legacy_grade_individual_redirect, name='grade_individual_essay_legacy'),
    path('grade_individual_essayCM/<str:activity_id>/<int:student_question_id>/',
         legacy_grade_individual_redirect_cm, name='grade_individual_essayCM_legacy'),
    path('grade_individual_essay/<str:activity_id>/<str:detail_local_id>/', GradeIndividualEssayView.as_view(), name='grade_individual_essay'),
    path('grade_individual_essayCM/<str:activity_id>/<str:detail_local_id>/', GradeIndividualEssayViewCM.as_view(), name='grade_individual_essayCM'),
    path('save_all_questions/<str:activity_id>/', SaveAllQuestionsView.as_view(), name='save_all_questions'),
    path('save_partial_answer/<str:activity_id>/', SavePartialAnswerView.as_view(), name='save_partial_answer'),
    path('batch_save_questions/<str:activity_id>/', BatchSaveQuestionsView.as_view(), name='batch_save_questions'),
    path('upload_question_file/<str:activity_id>/', UploadQuestionFileView.as_view(), name='upload_question_file'),
    path('set_default_points/<str:activity_id>/', SetDefaultPointsView.as_view(), name='set_default_points'),
    path('apply_default_points/<str:activity_id>/', ApplyDefaultPointsView.as_view(), name='apply_default_points'),
    path('import_questions/<str:activity_id>/', ImportQuestionsUnifiedView.as_view(), name='import_questions_unified'),
    path('import_template/', DownloadImportTemplateView.as_view(), name='download_import_template'),
    path('save_all_questionsCM/<str:activity_id>/', SaveAllQuestionsViewCM.as_view(), name='save_all_questionsCM'),

    # ── Student-facing helpers ─────────────────────────────────────────
    path('viewStudentScore/<str:activity_id>/', viewStudentScore, name='viewStudentScore'),
    path('toggle-student-assessment-editable/', toggle_student_assessment_editable, name='toggle-student-assessment-editable'),
    path('scoreChangeLogs/<str:activity_id>/', scoreChangeLogs, name='scoreChangeLogs'),
    path('edit_student_score/', edit_student_score, name='edit_student_score'),
    path('toggleShowScore/<str:activity_id>/', toggleShowScore, name='toggleShowScore'),

    # ── Assessment copy flows ──────────────────────────────────────────
    path('import-assessments-from-previous-semester/<int:subject_id>/', copy_assessments, name='import-assessments-from-previous-semester'),
    path('import-assessments-from-previous-semester-cm/<int:subject_id>/', copy_assessments_cm, name='import-assessments-from-previous-semester-cm'),
    path('subject/<int:subject_id>/check-assessment-exists/', check_assessment_exists, name='check-assessment-exists'),
    path('subject/<int:subject_id>/get-subject-assessments-by-semester/', get_subject_assessments_by_semester, name='get-subject-assessments-by-semester'),
    path('copy/assessments/from/course/<int:target_subject_id>/', copy_assessments_from_subject, name='copy-assessments-from-subject'),
    path('copy-assessments-from-subject-cm/<int:target_subject_id>/', copy_assessments_from_subject_cm, name='copy-assessments-from-subject-cm'),
    path('get-subject-assessments/<int:subject_id>/', get_subject_assessments, name='get-subject-assessments'),
    path('check-subject-assessment-exists/<int:target_subject_id>/', check_subject_assessment_exists, name='check-subject-assessment-exists'),

    # ── Participation (separate concept) ───────────────────────────────
    path('participation_scores/<str:activity_id>/', participation_scores, name='participation_scores'),
    path('activity/<str:activity_id>/edit-participation/', EditParticipationView.as_view(), name='edit_participation'),
    path('edit_participationCM/<str:activity_id>/', EditParticipationViewCM.as_view(), name='edit_participationCM'),

    # ── Grading ────────────────────────────────────────────────────────
    path('grade-assessment/<str:activity_id>/', GradeAssessmentView.as_view(), name='grade-assessment'),
    path('grade-assessment-cm/<str:activity_id>/', GradeAssessmentViewCM.as_view(), name='grade-assessment-cm'),

    # ── API + dashboard ────────────────────────────────────────────────
    path('student_score_viewsets/', StudentScoreViewSet.as_view({'get': 'list'}), name='StudentScoreViewSet'),
    path('dashboard_student_grade/', dashboard_student_grade.as_view({'get': 'list'}), name='dashboard_student_grade'),
    path('api/subjects/', get_subjects, name='subjects'),
    path('api/student-assessment-summary/', StudentAssessmentSummaryView.as_view(), name='student-assessment-summary'),
    path('api/student-assessment-consolidated-summary/', StudentAssessmentConsolidatedSummaryView.as_view(), name='student-assessment-consolidated-summary'),
    path('api/student-assessment-summary-mobile/', StudentAssessmentSummaryMobileView.as_view(), name='student-assessment-summary-mobile'),

    # ── Question CRUD on saved assessments ─────────────────────────────
    path('edit-assessment-question/<str:activity_id>/<int:question_id>/', edit_assessment_question, name='edit-assessment-question'),
    path('list-assessment-questions/<str:activity_id>/', list_assessment_questions, name='list-assessment-questions'),
    path('delete-assessment-question/<str:activity_id>/<int:question_id>/', delete_assessment_question, name='delete-assessment-question'),

    # ── Rubrics ────────────────────────────────────────────────────────
    path('rubric/list/', rubric_list, name='rubric-list'),
    path('create/rubric/', create_rubric, name='create-rubric'),
    path('update/rubric/<int:rubric_id>/', update_rubric, name='update-rubric'),
    path('delete/rubric/<int:rubric_id>/', delete_rubric, name='delete-rubric'),

    # ── Bulk export / import ───────────────────────────────────────────
    path('export_activities', export_activities, name='export_activities'),
    path('import_activities', import_activities, name='import_activities'),
    path('import_and_export_activity_page/', import_and_export_activity_page, name='import_and_export_activity_page'),
    path('export_students/', export_student_data_csv, name='export_student_data'),
    path('import_students/', import_student_data, name='import_student_data'),
]
