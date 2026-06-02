from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    short_name = models.CharField(max_length=50, null=True, blank=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True )

    def __str__(self):
        return self.name