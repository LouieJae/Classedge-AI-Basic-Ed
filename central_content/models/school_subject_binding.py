from django.db import models


class SchoolSubjectBinding(models.Model):
    central_subject = models.ForeignKey(
        "central_content.CentralSubject",
        on_delete=models.CASCADE,
        related_name="school_bindings",
    )
    target_school = models.ForeignKey(
        "central_content.School",
        on_delete=models.PROTECT,
        related_name="bindings",
    )
    school_subject_id = models.IntegerField()
    school_subject_name = models.CharField(max_length=200)
    school_subject_code = models.CharField(max_length=30, blank=True)

    pushed_version = models.PositiveIntegerField(null=True, blank=True)
    last_pushed_at = models.DateTimeField(null=True, blank=True)

    bound_by = models.ForeignKey(
        "central_content.CentralStaff",
        on_delete=models.PROTECT,
        related_name="bindings_created",
    )
    bound_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "central_content"
        db_table = "central_content_school_subject_binding"
        constraints = [
            models.UniqueConstraint(
                fields=["central_subject", "target_school"],
                name="uniq_central_subject_target_school",
            ),
        ]
        ordering = ["target_school", "central_subject"]

    @property
    def drift_state(self) -> str:
        if self.pushed_version is None:
            return "never"
        if self.pushed_version == self.central_subject.version:
            return "up_to_date"
        return "drift"

    def __str__(self):
        return f"{self.central_subject_id}->{self.target_school_id}"
