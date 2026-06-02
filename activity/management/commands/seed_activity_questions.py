"""
Seed a sample activity (with answerable questions) on a chosen subject and
attach it to one or more lessons so it shows up nested under each lesson on
the student lesson list.

Usage:
    # Seed a quiz on subject 1, auto-linked to every lesson on the subject:
    python manage.py seed_activity_questions --subject-id 1

    # Link only to a specific lesson:
    python manage.py seed_activity_questions --subject-id 1 --link-lesson-id 5

    # Wipe a student's attempt history so they can answer it again:
    python manage.py seed_activity_questions --subject-id 1 --reset-student rey.antiquin@gmail.com

    # Seed a fresh activity with a unique name (so retakes never matter):
    python manage.py seed_activity_questions --subject-id 1 --fresh

Idempotent on the same activity name: re-running rebuilds the questions in
place. `--reset-student` clears the named student's StudentActivity +
StudentQuestion rows for the activity so attempts go back to 0.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from activity.models import (
    Activity,
    ActivityQuestion,
    ActivityType,
    QuestionChoice,
    QuizType,
    StudentActivity,
    StudentQuestion,
)
from module.models.module import Module
from subject.models import Subject


SAMPLE_QUESTIONS = [
    {
        "quiz_type": "Multiple Choice",
        "question_text": "Which planet is known as the Red Planet?",
        "choices": ["Venus", "Mars", "Jupiter", "Saturn"],
        "correct_answer": "1",
        "score": 2.0,
    },
    {
        "quiz_type": "True/False",
        "question_text": "The Pacific Ocean is the largest ocean on Earth.",
        "correct_answer": "True",
        "score": 1.0,
    },
    {
        "quiz_type": "Fill in the Blank",
        "question_text": "The chemical symbol for water is ____.",
        "correct_answer": "H2O",
        "score": 2.0,
    },
    {
        "quiz_type": "Essay",
        "question_text": "Briefly explain how photosynthesis converts light energy into chemical energy. Mention chlorophyll and at least one product of the reaction.",
        "correct_answer": "Plants use chlorophyll to absorb sunlight, which drives a reaction that converts CO2 and water into glucose and oxygen.",
        "score": 5.0,
    },
    {
        "quiz_type": "Matching Type",
        "question_text": "Match each country to its capital.",
        "left_choices": ["France", "Japan", "Egypt", "Brazil"],
        "right_choices": ["Paris", "Tokyo", "Cairo", "Brasília"],
        "correct_answer": "France->Paris;Japan->Tokyo;Egypt->Cairo;Brazil->Brasília",
        "score": 4.0,
    },
]


class Command(BaseCommand):
    help = "Seed a demo activity with answerable questions on a given subject."

    def add_arguments(self, parser):
        parser.add_argument("--subject-id", type=int, required=True,
                            help="ID of the Subject to attach the activity to.")
        parser.add_argument("--activity-name", type=str, default="Practice Quiz",
                            help="Activity name (default: 'Practice Quiz').")
        parser.add_argument("--type", type=str, default="Quiz",
                            help="ActivityType name (default: 'Quiz'). Created if missing.")
        parser.add_argument("--link-lesson-id", type=int, default=None,
                            help="Specific Module ID to attach. Default: link to every lesson on the subject.")
        parser.add_argument("--no-link", action="store_true",
                            help="Skip lesson auto-linking.")
        parser.add_argument("--reset-student", type=str, default=None,
                            help="Student email or numeric id. Wipes StudentActivity + StudentQuestion rows for this activity so attempts reset to 0.")
        parser.add_argument("--fresh", action="store_true",
                            help="Append a timestamp suffix to the activity name so a new activity is always created (sidesteps retake limits without touching old data).")

    def _resolve_student(self, ident):
        User = get_user_model()
        if ident.isdigit():
            try:
                return User.objects.get(pk=int(ident))
            except User.DoesNotExist:
                raise CommandError(f"User id={ident} not found.")
        try:
            return User.objects.get(email=ident)
        except User.DoesNotExist:
            raise CommandError(f"User with email '{ident}' not found.")

    @transaction.atomic
    def handle(self, *args, **options):
        subject_id = options["subject_id"]
        activity_name = options["activity_name"]
        type_name = options["type"]
        link_lesson_id = options["link_lesson_id"]
        no_link = options["no_link"]
        reset_student = options["reset_student"]
        fresh = options["fresh"]

        try:
            subject = Subject.objects.get(pk=subject_id)
        except Subject.DoesNotExist:
            raise CommandError(f"Subject id={subject_id} not found.")

        if fresh:
            activity_name = f"{activity_name} ({timezone.now().strftime('%b %d %H:%M')})"

        activity_type, _ = ActivityType.objects.get_or_create(name=type_name)

        now = timezone.now()
        activity, created = Activity.objects.update_or_create(
            activity_name=activity_name,
            subject=subject,
            defaults={
                "activity_type": activity_type,
                "start_time": now - timedelta(hours=1),
                "end_time": now + timedelta(days=14),
                "max_score": sum(q["score"] for q in SAMPLE_QUESTIONS),
                "passing_score": 60,
                "passing_score_type": "percentage",
                "max_retake": 5,
                "time_duration": 30,
                "show_score": True,
                "is_graded": True,
                "status": True,
                "activity_instruction": (
                    "Answer each question. You'll see your score and the "
                    "correct answers right after submitting."
                ),
            },
        )

        ActivityQuestion.objects.filter(activity=activity).delete()
        for q in SAMPLE_QUESTIONS:
            quiz_type, _ = QuizType.objects.get_or_create(name=q["quiz_type"])
            question = ActivityQuestion.objects.create(
                activity=activity,
                subject=subject,
                quiz_type=quiz_type,
                question_text=q["question_text"],
                correct_answer=q["correct_answer"],
                score=q["score"],
            )
            if q["quiz_type"] == "Multiple Choice":
                for choice_text in q["choices"]:
                    QuestionChoice.objects.create(
                        question=question, subject=subject, choice_text=choice_text,
                    )
            elif q["quiz_type"] == "Matching Type":
                for left in q["left_choices"]:
                    QuestionChoice.objects.create(
                        question=question, subject=subject,
                        choice_text=left, is_left_side=True,
                    )
                for right in q["right_choices"]:
                    QuestionChoice.objects.create(
                        question=question, subject=subject,
                        choice_text=right, is_left_side=False,
                    )

        # Lesson linking — attach the activity to one or all lessons in the
        # subject so the student lesson list nests it as a child row.
        if not no_link:
            if link_lesson_id is not None:
                try:
                    lesson = Module.objects.get(pk=link_lesson_id, subject=subject)
                except Module.DoesNotExist:
                    raise CommandError(
                        f"Lesson id={link_lesson_id} not found in subject {subject_id}."
                    )
                activity.additional_modules.add(lesson)
                self.stdout.write(self.style.SUCCESS(
                    f"  Linked to lesson '{lesson.file_name}' (id={lesson.id})."
                ))
            else:
                lessons = list(Module.objects.filter(subject=subject))
                if not lessons:
                    self.stdout.write(self.style.WARNING(
                        "  No lessons exist on this subject — activity will not be nested under any lesson."
                    ))
                else:
                    activity.additional_modules.add(*lessons)
                    self.stdout.write(self.style.SUCCESS(
                        f"  Linked to {len(lessons)} lesson(s) on this subject:"
                    ))
                    for lesson in lessons:
                        self.stdout.write(f"    · {lesson.file_name} (id={lesson.id})")

        # Optionally reset a student's attempts on this activity.
        if reset_student:
            student = self._resolve_student(reset_student)
            sa_count = StudentActivity.objects.filter(
                activity=activity, student=student
            ).delete()[0]
            sq_count = StudentQuestion.objects.filter(
                activity=activity, student=student
            ).delete()[0]
            self.stdout.write(self.style.SUCCESS(
                f"  Reset attempts for {student.email}: removed {sa_count} StudentActivity, {sq_count} StudentQuestion rows."
            ))

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} activity '{activity_name}' (id={activity.id}) on subject "
            f"'{subject.subject_name}' with {len(SAMPLE_QUESTIONS)} questions, "
            f"max_score={activity.max_score}, max_retake={activity.max_retake}."
        ))
