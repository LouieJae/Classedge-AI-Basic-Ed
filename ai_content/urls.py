from django.urls import path

from ai_content import views

urlpatterns = [
    path("ai-content/generate/<int:subject_id>/", views.generate_content, name="ai_generate_content"),
]
