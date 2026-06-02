from django.urls import path

from received_central_content.views import catalog, ingest, schedule

app_name = "received_central_content"

urlpatterns = [
    path("subjects/", catalog.list_subjects, name="list_subjects"),
    path("ingest/", ingest.ingest_subject, name="ingest_subject"),
    path("ingest/<int:central_id>/", ingest.delete_subject, name="delete_subject"),
    path("schedule/<int:subject_id>/", schedule.subject_schedule, name="subject_schedule"),
]
