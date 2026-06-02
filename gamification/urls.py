from django.urls import include, path

from gamification import side_activity_views, teacher_views, views
from gamification.subject_analytics import subject_panel_view, student_detail_view

urlpatterns = [
    path("gamification/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("gamification/leaderboard/", views.leaderboard, name="gamification_leaderboard"),
    path("gamification/badges/", views.badge_collection, name="gamification_badges"),
    path("gamification/share/badge/<str:token>/", views.shared_badge_view, name="shared_badge"),
    path("gamification/calendar/", views.student_calendar, name="student_calendar"),
    path("gamification/quest-map/", views.quest_map_picker, name="quest_map_picker"),
    path("gamification/quest-map/<int:subject_id>/", views.quest_map, name="quest_map"),
    path("gamification/side-activities/<int:subject_id>/", side_activity_views.side_activity_list, name="side_activity_list"),
    path("gamification/side-activity/<str:activity_id>/play/", side_activity_views.side_activity_play, name="side_activity_play"),
    path("gamification/side-activity/<str:activity_id>/submit/", side_activity_views.side_activity_submit, name="side_activity_submit"),
    path("gamification/side-activities/<int:subject_id>/create/", side_activity_views.side_activity_create, name="side_activity_create"),
    path("gamification/side-activity/<str:activity_id>/edit/", side_activity_views.side_activity_edit, name="side_activity_edit"),
    path("gamification/side-activity/<str:activity_id>/delete/", side_activity_views.side_activity_delete, name="side_activity_delete"),
    path("gamification/badges/manage/", views.badge_list, name="badge_management"),
    path("gamification/badges/featured/", views.set_featured_badges, name="set_featured_badges"),
    path("gamification/badges/<int:badge_id>/toggle/", views.badge_toggle_active, name="badge_toggle_active"),
    path("gamification/badges/<int:badge_id>/edit/", views.badge_edit, name="badge_edit"),
    path("gamification/badges/<int:badge_id>/award/", views.badge_manual_award, name="badge_manual_award"),
    path("gamification/recognition/", teacher_views.recognition_page, name="recognition_page"),
    path("gamification/recognition/send/", teacher_views.send_recognition, name="send_recognition"),
    path("gamification/rating/submit/", teacher_views.submit_rating, name="submit_rating"),
    path("courses/<int:subject_id>/analytics/panel/", subject_panel_view, name="subject_analytics_panel"),
    path("courses/<int:subject_id>/student/<int:student_id>/", student_detail_view, name="subject_student_detail"),
]

urlpatterns += [path("", include("gamification.urls_quests"))]
