
from .activity_crud_views import *
from .answer_views import SavePartialAnswerView
from .batch_save_views import BatchSaveQuestionsView
from .upload_file_view import UploadQuestionFileView
from .activity_detail_views import *
from .activity_list_views import *
from .activity_type_views import *
from .answer_views import *
from .api_views import *
from .copy_views import *
from .grading_views import *
from .import_and_export_activity_views import *
from .participation_views import *
from .question_admin_views import *
from .question_views import *
from .quiz_type_views import *
from .rubrics_views import *
from .score_admin_views import *

from .assessment_views import assessment_list

__all__ = [
            # Assessment CRUD Views
            "AddAssessmentViewCM", "AddAssessmentView", "UpdateAssessment", "UpdateAssessmentCM",
            "rename_activity",

            # Assessment Detail Views
            "AssessmentDetailsView", "AssessmentDetailViewCM",

            # Assessment List Views (per-subject + utilities)
            "subject_assessment_list", "viewStudentScore", "assessment_list_cm",
            "toggleShowScore", "delete_assessment",
            "participation_scores", "assessment_list_registrar",

            # Activity Type Views
            "ActivityTypeViewSet", "RubricsViewSet",

            # Answer Views
            "DisplayQuestionsView", "DisplayQuestionsViewCM", "AutoSubmitAnswersView",
            "SubmitAnswersView", "RetakeAssessmentView", "assessment_completed_view",
            "SavePartialAnswerView",

            # Api Views
            "student_score", "StudentScoreViewSet", "get_subjects", "dashboard_student_grade",
            "StudentAssessmentSummaryView", "StudentAssessmentConsolidatedSummaryView",
            "StudentAssessmentSummaryMobileView",

            # Copy Views
            "copy_assessments_from_subject", "copy_assessments_from_subject_cm",
            "get_subject_assessments", "check_subject_assessment_exists",
            "copy_assessments", "copy_assessments_cm",
            "check_assessment_exists", "get_subject_assessments_by_semester",

            # Grading Views
            "GradeEssayView", "GradeEssayViewCM", "GradeIndividualEssayView", "GradeIndividualEssayViewCM",
            "GradeAssessmentView", "GradeAssessmentViewCM",

            # Import And Export Activity Views
            "import_and_export_activity_page", "export_activities", "import_activities",

            # Participation Views
            "EditParticipationView", "EditParticipationViewCM",

            # Question Admin Views
            "list_assessment_questions", "edit_assessment_question", "delete_assessment_question",

            # Question Views
            "AddQuestionView", "AddQuestionViewCM", "DeleteTempQuestionView", "UpdateQuestionView", "UpdateQuestionViewCM",
            "SaveAllQuestionsView", "SaveAllQuestionsViewCM",
            "ApplyDefaultPointsView", "SetDefaultPointsView",
            "BatchSaveQuestionsView", "UploadQuestionFileView",
            "DownloadImportTemplateView", "ImportQuestionsUnifiedView",

            # Quiz Type Views
            "AddQuizTypeView", "AddQuizTypeViewCM",

            # Rubrics Views
            "rubric_list", "create_rubric", "update_rubric", "delete_rubric",

            # Score Admin Views
            "scoreChangeLogs", "edit_student_score", "toggle_student_assessment_editable",

            # Global Assessment List
            "assessment_list",
]
