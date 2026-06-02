from django.db import models
import os
import uuid


def display_image_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f'display_images/{uuid.uuid4()}{ext}'

class DisplayImage(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to=display_image_path)
    is_displayed = models.BooleanField(default=False)

    def __str__(self):
        return self.name