from django.db import models

class StudentSDG(models.Model):
    student = models.ForeignKey('accounts.CustomUser', on_delete=models.PROTECT, null=True, blank=True)
    sdg = models.ForeignKey('subject.SDG', on_delete=models.PROTECT, null=True, blank=True)
    count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('student', 'sdg')
        
    def __str__(self):
        return f"{self.student} - {self.sdg} ({self.count})"
    