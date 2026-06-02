from django.core.exceptions import ValidationError
from django.db import models


class CurriculumPlan(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    textbook = models.ForeignKey(
        "central_content.ParsedTextbook",
        on_delete=models.CASCADE,
        related_name="plans",
    )
    school_subject_id = models.PositiveIntegerField()
    session_count = models.PositiveIntegerField()
    minutes_per_session = models.PositiveIntegerField()
    model_key = models.CharField(max_length=50)
    plan_data = models.JSONField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    generated_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="curriculum_plans",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_curriculum_plan"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Plan for {self.textbook.title} ({self.model_key})"

    def clean(self):
        super().clean()
        if not self.plan_data:
            return
        self._validate_plan_data()

    def _validate_plan_data(self):
        if not isinstance(self.plan_data, list) or len(self.plan_data) == 0:
            raise ValidationError("plan_data must be a non-empty list.")

        textbook_chapter_numbers = set(
            self.textbook.chapters.values_list("chapter_number", flat=True)
        )

        week_numbers = [entry["week"] for entry in self.plan_data]
        expected_weeks = list(range(1, len(self.plan_data) + 1))
        if week_numbers != expected_weeks:
            raise ValidationError(
                f"Weeks must be sequential starting from 1. Got: {week_numbers}"
            )

        all_assigned = []
        for entry in self.plan_data:
            chapters = entry.get("chapters", [])
            if len(chapters) == 0:
                raise ValidationError(
                    f"Week {entry['week']} must have at least one chapter."
                )
            all_assigned.extend(chapters)

        assigned_set = set(all_assigned)
        if len(all_assigned) != len(assigned_set):
            duplicates = [c for c in all_assigned if all_assigned.count(c) > 1]
            raise ValidationError(
                f"Duplicate chapter assignments: {set(duplicates)}"
            )

        nonexistent = assigned_set - textbook_chapter_numbers
        if nonexistent:
            raise ValidationError(
                f"Chapters do not exist in textbook: {nonexistent}"
            )

        missing = textbook_chapter_numbers - assigned_set
        if missing:
            raise ValidationError(
                f"Missing chapters not assigned to any week: {missing}"
            )
