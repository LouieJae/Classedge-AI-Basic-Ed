from django.urls import path

from rag_tutor import views

urlpatterns = [
    path("rag-tutor/ask/<int:subject_id>/", views.ask, name="rag_tutor_ask"),
    path("rag-tutor/history/<int:subject_id>/", views.history, name="rag_tutor_history"),
]
