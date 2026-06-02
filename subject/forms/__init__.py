# Re-export forms for backward compatibility: `from subject.forms import ...`
from .schedule import scheduleForm
from .subject import subjectForm, subjectPhotoForm, CoilSubjectForm
from .evaluation import (
    EvaluationQuestionForm,
    EvaluationAssignmentForm,
    TeacherEvaluationForm,
)
__all__ = [
    'scheduleForm','subjectForm','subjectPhotoForm','CoilSubjectForm','EvaluationQuestionForm',
    'EvaluationAssignmentForm','TeacherEvaluationForm'
    

]
