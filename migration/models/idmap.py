from django.db import models


class IDMap(models.Model):
    app_label = models.CharField(max_length=64)
    model_name = models.CharField(max_length=64)
    old_pk = models.CharField(max_length=64)
    new_pk = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("app_label", "model_name", "old_pk")]
        indexes = [models.Index(fields=["app_label", "model_name", "old_pk"])]

    def __str__(self) -> str:
        return f"{self.app_label}.{self.model_name} {self.old_pk}->{self.new_pk}"

    @classmethod
    def resolve(cls, app_label: str, model_name: str, old_pk) -> str | None:
        row = cls.objects.filter(app_label=app_label, model_name=model_name, old_pk=str(old_pk)).only("new_pk").first()
        return row.new_pk if row else None

    @classmethod
    def upsert(cls, app_label: str, model_name: str, old_pk, new_pk) -> "IDMap":
        obj, _ = cls.objects.update_or_create(
            app_label=app_label, model_name=model_name, old_pk=str(old_pk),
            defaults={"new_pk": str(new_pk)},
        )
        return obj
