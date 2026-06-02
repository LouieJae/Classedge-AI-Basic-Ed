from django.urls import path, include
from .views import  *
from rest_framework.routers import DefaultRouter
router = DefaultRouter()

router.register('events', EventViewSet, basename='events')
router.register('announcements', AnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('api/', include(router.urls)),

    #api
    path('api/calendar/', calendar_api, name='calendar_api'),
    path('api/activities/', activity_api, name='activity_api'),
    path('api/holidays/', holiday_api, name='holiday_api'),
    # path('api/announcements/', announcement_api, name='announcements_api'),


    path('campus/news/', news, name='news'),
    path('api_event_list/', api_event_list, name='api_event_list'),
    path('event_list/', event_list, name='event_list'),
    path('calendars/', calendars, name='calendars'),

    path('announcement/details/<int:id>/', announcement_details, name='announcement_details'),
    path('event/details/<int:id>/', event_details, name='event_details'),

    # Subject-level announcements (teacher CRUD)
    path('course/announcements/', subject_announcements_page, name='subject_announcements'),
    path('api/subject-announcements/', subject_announcement_list_api, name='subject_announcement_list_api'),
    path('api/subject-announcements/<int:pk>/', subject_announcement_detail_api, name='subject_announcement_detail_api'),

]
