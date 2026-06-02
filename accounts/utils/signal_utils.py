from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from accounts.models import Profile, LoginHistory
from roles.models import Role
from django.contrib.auth.signals import user_logged_in
import threading

# Thread-local storage for context flags
_thread_locals = threading.local()

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Check if this user is being created from RMS sync
        is_rms_teacher = getattr(_thread_locals, 'creating_rms_teacher', False)
        is_rms_student = getattr(_thread_locals, 'creating_rms_student', False)
        
        if is_rms_teacher:
            # User is from RMS teacher sync - assign Teacher role
            teacher_role, _ = Role.objects.get_or_create(name='Teacher')
            Profile.objects.get_or_create(
                user=instance,
                defaults={
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'role': teacher_role
                }
            )
        elif is_rms_student:
            # User is from RMS student sync - assign Student role
            student_role, _ = Role.objects.get_or_create(name='Student')
            Profile.objects.get_or_create(
                user=instance,
                defaults={
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'role': student_role
                }
            )
        else:
            # Normal user creation - assign Student role (default)
            student_role, _ = Role.objects.get_or_create(name='Student')
            Profile.objects.get_or_create(
                user=instance,
                defaults={
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'role': student_role
                }
            )
    else:
        profile, _ = Profile.objects.get_or_create(user=instance)
        profile.first_name = instance.first_name
        profile.last_name = instance.last_name
        profile.save()

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    from accounts.models import CustomUser
    if not isinstance(user, CustomUser):
        return
    LoginHistory.objects.create(user=user)