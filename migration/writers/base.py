from django.apps import apps
from django.contrib.auth.models import Permission
from django.db import transaction

from migration.mappers.base import MapperResult, MissingFKError, require_fk
from migration.models import IDMap
from migration.side_effects import suppress_push_notifications, suppress_rag_indexing


class RowWriter:
    def __init__(self, *, app_label: str, model_name: str, target_model=None):
        self.app_label = app_label
        self.model_name = model_name
        self.target_model = target_model or apps.get_model(app_label, model_name)

    def write(self, *, old_pk, mapper_result: MapperResult, dry_run: bool = False):
        if mapper_result.skip:
            return None
        if dry_run:
            return None

        # Optional target override (e.g. archive logs.UserActivityLog into
        # migration.LegacyAuditLog). IDMap stays keyed by SOURCE identity.
        if mapper_result.target_app and mapper_result.target_model:
            target_model = apps.get_model(mapper_result.target_app, mapper_result.target_model)
        else:
            target_model = self.target_model

        with suppress_push_notifications(), suppress_rag_indexing(), transaction.atomic():
            existing_new_pk = IDMap.resolve(self.app_label, self.model_name, old_pk)
            instance = None
            if existing_new_pk:
                instance = target_model.objects.filter(pk=existing_new_pk).first()
                if instance is None:
                    # Stale IDMap pointing at a deleted row — drop it and create fresh.
                    IDMap.objects.filter(
                        app_label=self.app_label,
                        model_name=self.model_name,
                        old_pk=str(old_pk),
                    ).delete()
            if instance is None and mapper_result.natural_key:
                instance = target_model.objects.filter(**mapper_result.natural_key).first()
            if instance is None:
                instance = target_model()

            for fk_info in mapper_result.fk_resolutions:
                target_app, target_model, fk_old_pk, field_name = fk_info
                new_fk = require_fk(target_app, target_model, fk_old_pk, field_name=field_name)
                setattr(instance, f"{field_name}_id", new_fk)

            for fname, fvalue in mapper_result.fields.items():
                setattr(instance, fname, fvalue)
            instance.full_clean(exclude=self._exclude_for_clean(mapper_result))
            instance.save()

            for m2m_field, items in mapper_result.m2m_resolutions.items():
                self._apply_m2m(instance, m2m_field, items)

            # Post-save updates bypass auto_now_add / auto_now / signals.
            # Used to preserve original timestamps on append-only audit rows.
            if mapper_result.post_save_updates:
                target_model.objects.filter(pk=instance.pk).update(
                    **mapper_result.post_save_updates
                )
                instance.refresh_from_db()

            IDMap.upsert(self.app_label, self.model_name, old_pk, instance.pk)
        return instance

    def _exclude_for_clean(self, result: MapperResult) -> list[str]:
        return list(result.m2m_resolutions.keys()) + list(result.clean_exclude)

    def _apply_m2m(self, instance, field_name: str, items: list[tuple]) -> None:
        """Foundation plan only handles roles.Role.permissions (codename-keyed)."""
        from roles.models import Role as RoleModel
        if field_name == "permissions" and isinstance(instance, RoleModel):
            qs = Permission.objects.none()
            for app_label, codename in items:
                qs = qs | Permission.objects.filter(content_type__app_label=app_label, codename=codename)
            instance.permissions.set(qs.distinct())
            return
        raise NotImplementedError(f"No M2M handler for {field_name} on {self.target_model.__name__}")
