from django.urls import path

from at_risk import views

urlpatterns = [
    path("at-risk/dashboard/<int:subject_id>/", views.dashboard, name="at_risk_dashboard"),
]
