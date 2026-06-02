from django.conf import settings
from django.db import models


class CodingExercise(models.Model):
    # Slugs match Monaco editor language IDs and the keys in
    # ide.judge0_client.LANGUAGE_IDS — keep these three in lockstep.
    LANGUAGE_CHOICES = [
        ("python", "Python"),
        ("javascript", "JavaScript"),
        ("typescript", "TypeScript"),
        ("java", "Java"),
        ("c", "C"),
        ("cpp", "C++"),
        ("csharp", "C#"),
        ("go", "Go"),
        ("rust", "Rust"),
        ("ruby", "Ruby"),
        ("php", "PHP"),
        ("kotlin", "Kotlin"),
        ("swift", "Swift"),
        ("shell", "Bash"),
        ("sql", "SQL"),
        ("r", "R"),
        ("lua", "Lua"),
    ]

    activity = models.OneToOneField(
        "activity.Activity",
        on_delete=models.CASCADE,
        related_name="coding_exercise",
    )
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    starter_code = models.TextField(blank=True)
    solution_code = models.TextField(blank=True)
    test_cases = models.JSONField()
    time_limit_seconds = models.PositiveSmallIntegerField(default=5)
    memory_limit_kb = models.PositiveIntegerField(default=256000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CodingExercise({self.activity})"


class CodeSubmission(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("error", "Error"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="code_submissions",
    )
    exercise = models.ForeignKey(
        CodingExercise,
        on_delete=models.CASCADE,
    )
    code = models.TextField()
    language = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    result_json = models.JSONField(default=dict)
    score = models.FloatField(null=True)
    execution_time_ms = models.PositiveIntegerField(null=True)
    memory_used_kb = models.PositiveIntegerField(null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["student", "exercise"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"CodeSubmission({self.student}, {self.exercise})"
