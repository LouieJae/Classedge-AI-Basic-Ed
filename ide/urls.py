from django.urls import path

from ide import views

urlpatterns = [
    path("ide/exercise/<str:activity_id>/", views.exercise_detail, name="exercise_detail"),
    path("ide/exercise/<str:activity_id>/submit/", views.submit_code_view, name="submit_code"),
    path("ide/submission/<int:submission_id>/status/", views.submission_status, name="submission_status"),
    path("ide/exercise/<str:activity_id>/setup/", views.exercise_create, name="exercise_create"),
    path("ide/exercise/<int:exercise_id>/edit/", views.exercise_edit, name="exercise_edit"),
    path("ide/overview/", views.coding_overview, name="coding_overview"),
    path("ide/exercise/<int:exercise_id>/results/", views.coding_exercise_results, name="coding_exercise_results"),
    path("ide/submission/<int:submission_id>/override/", views.coding_score_override, name="coding_score_override"),
]
