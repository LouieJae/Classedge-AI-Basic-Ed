from django.db import models
from django.utils.timezone import now
import os
import uuid

def certificate_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'certificate/{uuid.uuid4()}{ext}'


class Certificate(models.Model):
    profiles = models.ManyToManyField('Profile', related_name='certificates')
    title = models.CharField(max_length=255)
    file = models.ImageField(upload_to=certificate_upload_path)
    issued_date = models.DateField(default=now)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        if self.pk:
            names = ", ".join([f"{p.first_name} {p.last_name}" for p in self.profiles.all()])
            return f"{self.title} - {names}"
        return self.title