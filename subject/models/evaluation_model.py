import uuid
from django.db import models
from django.conf import settings


class EvaluationQuestion(models.Model):
    question_text = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.question_text


class EvaluationAssignment(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_evaluations")
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    semester = models.ForeignKey('course.Semester', on_delete=models.CASCADE)
    questions = models.ManyToManyField('EvaluationQuestion', related_name="assignments")
    is_visible = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Evaluation Assignment"
        verbose_name_plural = "Evaluation Assignments"

    def __str__(self):
        return f"Evaluation for {self.teacher.get_full_name()} in {self.subject.subject_name} ({self.semester})"


class TeacherEvaluation(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assignment = models.ForeignKey('EvaluationAssignment', on_delete=models.CASCADE, related_name="evaluations", null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    general_feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Evaluation by {self.student.get_full_name()} for {self.assignment.teacher.get_full_name()}"


class TeacherEvaluationResponse(models.Model):
    evaluation = models.ForeignKey('TeacherEvaluation', on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey('EvaluationQuestion', on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()

    def __str__(self):
        return f"Response to '{self.question}' with rating {self.rating}"


class SubjectCollaborator(models.Model):
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE, related_name='collaborator_invites')
    email = models.EmailField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    token = models.UUIDField(default=uuid.uuid4, unique=True, null=True, blank=True)

    def __str__(self):
        return self.email
