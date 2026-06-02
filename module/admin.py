from django.contrib import admin
from .models.module import Module
from .models.student_progress import StudentProgress
# Register your models here.

admin.site.register(Module)
admin.site.register(StudentProgress)
