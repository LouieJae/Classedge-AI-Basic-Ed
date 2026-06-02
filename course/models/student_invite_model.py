from django.db import models
import uuid

class StudentInvite(models.Model):
    email = models.EmailField()
    subject = models.ForeignKey('subject.Subject', on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    accepted = models.BooleanField(default=False)
    invited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} invited to {self.subject}"