from django.db import models
from logs.models import SubjectLog
import cuid
import uuid
import os

def get_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_name = f"{uuid.uuid4()}{ext}"
    return os.path.join('uploadDocuments', new_name)


def get_upload_file_instruction(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_name = f"{uuid.uuid4()}{ext}"
    return os.path.join('fileInstruction', new_name)


def get_upload_choice_image(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_name = f"{uuid.uuid4()}{ext}"
    return os.path.join('choiceImage', new_name)


def get_upload_activity_file_instruction(instance, filename):
    ext = os.path.splitext(filename)[1]
    new_name = f"{uuid.uuid4()}{ext}"
    return os.path.join('ActivityFile', new_name)

class ActivityType(models.Model):
    # `name` stays as the canonical identifier used by code branches
    # (e.g. `if activity_type.name == 'Participation'`). `display_name`
    # is purely cosmetic and what the UI should render via __str__.
    name = models.CharField(max_length=50)
    display_name = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.display_name or self.name


class QuizType(models.Model):
    QUIZ_CHOICES = [
        ("Multiple Choice", "Multiple Choice"),
        ("Essay", "Essay"),
        ("True/False", "True/False"),
        ("Fill in the Blank", "Fill in the Blank"),
        ("Matching Type", "Matching Type"),
        ("Calculated Numeric", "Calculated Numeric"),
        ("Document", "Document"),
        ("Participation", "Participation"),
        ("Direct Score", "Direct Score"),
    ]

    # Same pattern: `name` is the stable internal key (matches QUIZ_CHOICES);
    # `display_name` overrides what humans see.
    name = models.CharField(max_length=50, choices=QUIZ_CHOICES)
    display_name = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.display_name or self.name


class Activity(models.Model):
    activity_name = models.CharField(max_length=100)
    activity_type = models.ForeignKey("activity.ActivityType", on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey("subject.Subject", on_delete=models.PROTECT, null=True, blank=True)
    term = models.ForeignKey("course.Term", on_delete=models.CASCADE, null=True, blank=True)
    additional_modules = models.ManyToManyField("module.Module", blank=True, related_name="additional_activities")
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    show_score = models.BooleanField(default=False)
    remedial = models.BooleanField(default=False)
    remedial_students = models.ManyToManyField("accounts.CustomUser", blank=True, limit_choices_to={"profile__role__name__iexact": "Student"})
    max_retake = models.PositiveIntegerField(default=0)  # Number of retakes allowed
    time_duration = models.PositiveIntegerField(default=0)  # Time duration in minutes
    max_score = models.FloatField(default=100, null=True, blank=True)
    status = models.BooleanField(default=True)
    passing_score = models.FloatField(default=0)
    PASSING_SCORE_TYPE_CHOICES = [
        ("number", "Number"),
        ("percentage", "Percentage"),
    ]
    passing_score_type = models.CharField(
        max_length=10, choices=PASSING_SCORE_TYPE_CHOICES, default="percentage"
    )
    RETAKE_METHOD_CHOICES = [
        ("highest", "Highest Score"),
        ("latest", "Latest Take"),
        ("average", "Average"),
        ("first", "First Attempt"),
    ]
    retake_method = models.CharField(
        max_length=15, choices=RETAKE_METHOD_CHOICES, default="highest"
    )
    activity_instruction = models.TextField(null=True, blank=True)
    activity_file_instruction = models.FileField(upload_to=get_upload_activity_file_instruction, null=True, blank=True)
    classroom_mode = models.BooleanField(default=False)
    allow_late_submission = models.BooleanField(default=False)
    late_submission_days = models.PositiveIntegerField(default=0)
    late_submission_penalty_percent = models.PositiveIntegerField(default=0)
    is_graded = models.BooleanField(default=True)
    shuffle_questions = models.BooleanField(default=False)
    central_source_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    local_id = models.CharField(max_length=36, primary_key=True, default=cuid.cuid, editable=False)
    allow_late = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    @property
    def id(self):
        return self.local_id

    def __str__(self):
        return self.activity_name

    def save(self, *args, **kwargs):
        if not self.local_id:
            self.local_id = cuid.cuid()
        is_new = self._state.adding
        old_instance = None
        old_file_instruction = None

        if not is_new:
            try:
                old_instance = Activity.objects.get(pk=self.pk)
                old_file_instruction = old_instance.activity_file_instruction
            except Activity.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.activity_file_instruction and (is_new or old_file_instruction != self.activity_file_instruction):
            from mobile.models import Attachment
            Attachment.objects.create(
                activity=self,
                file=self.activity_file_instruction,
            )

        # ----- Logging -----
        # Skip subject-log creation for classroom-mode activities so the
        # bell-popover notifications stay consistent with the MessageNotification
        # path below (which also gates on `not self.classroom_mode`).
        if (
            self.subject
            and not self.classroom_mode
            and not SubjectLog.objects.filter(subject=self.subject, message__icontains=self.activity_name).exists()
        ):
            SubjectLog.objects.create(
                subject=self.subject,
                activity=True,
                message=f"A New {self.activity_type} Named '{self.activity_name}' Has Been Added For {self.subject.subject_name}."
            )

        # ----- Notifications -----
        should_notify = False
        message = None

        if is_new and self.subject:
            message = f"A new activity '{self.activity_name}' has been created for {self.subject.subject_name}."
            should_notify = True
        elif old_instance:
            if old_instance.activity_name != self.activity_name:
                message = f"Activity name changed from '{old_instance.activity_name}' to '{self.activity_name}'."
                should_notify = True
            elif old_instance.start_time != self.start_time or old_instance.end_time != self.end_time:
                message = f"Activity '{self.activity_name}' schedule has been updated."
                should_notify = True

        if should_notify and message and not self.classroom_mode:
            from logs.utils import create_notification_for_teacher, create_notifications_for_subject_students

            create_notification_for_teacher(
                subject=self.subject,
                entity_id=self.pk,
                entity_type='activity',
                name=self.activity_name,
                path=f'/assessment/{self.pk}',
                due_at=self.end_time,
                message_template=message
            )

            create_notifications_for_subject_students(
                subject=self.subject,
                entity_id=self.pk,
                entity_type='activity',
                name=self.activity_name,
                path=f'/assessment/{self.pk}',
                due_at=self.end_time,
                message_template=message,
                created_by=self.subject.assign_teacher
            )

class ActivityQuestion(models.Model):
    activity = models.ForeignKey("Activity", on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey("subject.Subject", on_delete=models.PROTECT, null=True, blank=True)
    question_text = models.TextField()
    question_instruction = models.FileField(upload_to=get_upload_file_instruction, null=True, blank=True)
    correct_answer = models.TextField()
    quiz_type = models.ForeignKey("QuizType", on_delete=models.CASCADE, null=True, blank=True)
    score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Question for {self.activity.activity_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_file = None
        if not is_new:
            try:
                old = ActivityQuestion.objects.get(pk=self.pk)
                old_file = old.question_instruction
            except ActivityQuestion.DoesNotExist:
                old_file = None

        super().save(*args, **kwargs)

        if self.question_instruction and (is_new or old_file != self.question_instruction):
            from mobile.models import Attachment
            Attachment.objects.create(
                activity_question=self,
                file=self.question_instruction,
            )

    @property
    def resolved_correct_choice(self):
        """For Multiple Choice questions, return the QuestionChoice the
        ``correct_answer`` field points at (or None).

        ``correct_answer`` is normally a choice index ("0", "1", ...) per
        the create flow's convention. Legacy data may store the literal
        choice text — fall back to a text match so existing questions
        still display correctly in list views.
        """
        if not self.correct_answer:
            return None
        if self.quiz_type and self.quiz_type.name != 'Multiple Choice':
            return None
        choices = list(self.choices.order_by('id'))
        raw = self.correct_answer.strip()
        if raw.isdigit():
            idx = int(raw)
            if 0 <= idx < len(choices):
                return choices[idx]
        for choice in choices:
            if choice.choice_text and choice.choice_text == raw:
                return choice
        return None


class QuestionChoice(models.Model):
    subject = models.ForeignKey("subject.Subject", on_delete=models.PROTECT, null=True, blank=True)
    question = models.ForeignKey(
        "ActivityQuestion", related_name="choices", on_delete=models.CASCADE, null=True, blank=True
    )
    choice_text = models.TextField(blank=True, default='')
    choice_image = models.ImageField(upload_to=get_upload_choice_image, null=True, blank=True)
    is_left_side = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Choice for {self.question.activity.activity_name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_file = None
        if not is_new:
            try:
                old = QuestionChoice.objects.get(pk=self.pk)
                old_file = old.choice_image
            except QuestionChoice.DoesNotExist:
                old_file = None

        super().save(*args, **kwargs)

        if self.choice_image and (is_new or old_file != self.choice_image):
            from mobile.models import Attachment
            Attachment.objects.create(
                question_choice=self,
                file=self.choice_image,
            )


class StudentQuestion(models.Model):
    """DEPRECATED: frozen legacy table. All writes go through RetakeRecord /
    RetakeRecordDetail. The only remaining production reads are the
    `is_participation=True` queries in course/ views, which are a temporary
    legacy bridge pending the participation-port follow-up. Scheduled drop:
    after the participation port + one semester of clean operation.
    """

    student = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, null=True, blank=True
    )
    activity_question = models.ForeignKey(
        "ActivityQuestion", on_delete=models.CASCADE, null=True, blank=True
    )
    activity = models.ForeignKey("Activity", on_delete=models.CASCADE, null=True, blank=True)
    score = models.FloatField(default=0)
    student_answer = models.TextField(null=True, blank=True)
    uploaded_file = models.FileField(upload_to=get_upload_path, null=True, blank=True)
    status = models.BooleanField(default=False)
    submission_time = models.DateTimeField(null=True, blank=True, default=None)
    is_participation = models.BooleanField(default=False)
    is_graded = models.BooleanField(null=True, blank=True, default=False)

    def __str__(self):
        if self.activity_question and self.activity_question.activity:
            return (
                f"{self.student.email} - {self.activity_question.activity.activity_name} - {self.activity_question.question_text}"
            )
        return f"{self.student.email} - No activity question available"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_file = None
        if not is_new:
            try:
                old = StudentQuestion.objects.get(pk=self.pk)
                old_file = old.uploaded_file
            except StudentQuestion.DoesNotExist:
                old_file = None

        super().save(*args, **kwargs)

        if self.uploaded_file and (is_new or old_file != self.uploaded_file):
            from mobile.models import Attachment
            Attachment.objects.create(
                student_question=self,
                file=self.uploaded_file,
            )


class ActivityIdRedirect(models.Model):
    """
    Maps pre-cutover integer Activity IDs to their new cuid PKs so that
    URLs, emails, and external references using the old integer continue
    to 301 to the correct page. One row per pre-cutover Activity.
    """
    legacy_id = models.PositiveIntegerField(unique=True, db_index=True)
    activity = models.ForeignKey(
        'Activity',
        on_delete=models.CASCADE,
        related_name='legacy_redirects',
    )
    created_at = models.DateTimeField(auto_now_add=True)
