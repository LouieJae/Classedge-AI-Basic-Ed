from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db.models.deletion import ProtectedError
from .models import Module 

@receiver(pre_delete, sender=Module)
def prevent_module_delete_if_in_use(sender, instance, using, **kwargs):
    # If this module is linked to any Activity via additional_modules, block deletion
    if instance.additional_activities.exists():
        raise ProtectedError(
            "Cannot delete this Module because it is linked to one or more Activities.",
            list(instance.additional_activities.all()[:3])  # optional: sample objs in the error
        )
