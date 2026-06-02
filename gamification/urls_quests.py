from django.urls import path
from gamification import quest_views as v

urlpatterns = [
    path("quests/module/<int:module_id>/", v.quest_mode_select, name="quest_mode_select"),
    path("quests/module/<int:module_id>/generate/", v.quest_generate, name="quest_generate"),
    path("quests/job/<int:job_id>/", v.quest_job_status, name="quest_job_status"),
    path("quests/module/<int:module_id>/manual/", v.quest_manual_init, name="quest_manual_init"),
    path("quests/module/<int:module_id>/upload/", v.quest_upload, name="quest_upload"),
    path("quests/module/<int:module_id>/review/", v.quest_review, name="quest_review"),
    path("quests/module/<int:module_id>/publish/", v.quest_publish_all, name="quest_publish_all"),
    path("quests/<int:quest_id>/toggle-grade/", v.quest_toggle_grade, name="quest_toggle_grade"),
    path("quests/<int:quest_id>/delete/", v.quest_delete, name="quest_delete"),
]

from gamification import quest_player_views as pv
urlpatterns += [
    path("quests/module/<int:module_id>/play/", pv.quest_play, name="quest_play"),
    path("quests/<int:quest_id>/submit/", pv.quest_play_submit, name="quest_play_submit"),
]
