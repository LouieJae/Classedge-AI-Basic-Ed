from django.db import models
from django.conf import settings
from django.utils.timezone import now, localdate

class Holiday(models.Model):
    title = models.CharField(max_length=100)
    date = models.DateField()
    color = models.CharField(max_length=20)

    HOLIDAY_TYPE_CHOICES = [
        ('Regular Holiday', 'Regular Holiday'),
        ('Special Holiday', 'Special Holiday'),
        ('Restday Regular Holiday', 'Restday Regular Holiday'),
        ('Restday Special Holiday', 'Restday Special Holiday'),
    ]

    holiday_type = models.CharField(max_length=30, choices=HOLIDAY_TYPE_CHOICES, default='Regular Holiday')
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)ss",
    )
    # [Classedge LMS] Null => institution-wide (visible to all).
    # Non-null => scoped to members of that department only.

    def __str__(self):
        return self.title


class Event(models.Model):
    title = models.CharField(max_length=200, verbose_name="Event Title")
    description = models.TextField(verbose_name="Event Description", blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    time = models.TimeField(verbose_name="Event Time", blank=True, null=True)
    location = models.CharField(max_length=255, verbose_name="Location", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Created By",
        related_name="events"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)ss",
    )
    # [Classedge LMS] Null => institution-wide (visible to all).
    # Non-null => scoped to members of that department only.

    def __str__(self):
        return f"{self.title} - {self.start_date}"

    class Meta:
        ordering = ['start_date']
        verbose_name = "Event"
        verbose_name_plural = "Events"

class Announcement(models.Model):
    title = models.CharField(max_length=200, verbose_name="Announcement Title")
    description = models.TextField(verbose_name="Event Description", blank=True, null=True)
    date = models.DateField(verbose_name="Date of Announcement", default=localdate)
    events = models.ManyToManyField('Event', blank=True, related_name="announcements")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Created By",
        related_name="announcements"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)ss",
    )
    # [Classedge LMS] Null => institution-wide (visible to all).
    # Non-null => scoped to members of that department only.
    subject = models.ForeignKey(
        "subject.Subject",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="announcements",
    )
    # [Classedge LMS] When set, the announcement is visible only to users
    # connected to that subject in the current semester — the teaching team
    # (assign_teacher / substitute_teacher / collaborators) and any student
    # with an active enrollment. Coexists with `department` for layered scopes.

    def __str__(self):
        return self.title