"""
URL configuration for lms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import handler500
from django.conf.urls import handler403
from lms import views

urlpatterns = [
    path('Classify/Login/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('accounts.urls_legal')),
    path('', include('accounts.urls')),
    path('', include('module.urls')),
    path('', include('calendars.urls')),
    path('', include('subject.urls')),
    path('', include('roles.urls')),
    path('', include('course.urls')),
    path('', include('message.urls')),
    path('', include('activity.urls')),
    path('', include('message.urls')),
    path('', include('gradebookcomponent.urls')),
    path('', include('logs.urls')),
    path('', include('classroom.urls')),
    path('', include('coil.urls')),
    path('', include('rms.urls')),
    path('', include('mobile.urls')),
    path('social/', include('social_media.urls')),
    path('summernote/', include('django_summernote.urls')),
    path('captcha/', include('captcha.urls')),
    path('api/central/', include('received_central_content.urls')),
    path('', include('ai_content.urls')),
    path('', include('rag_tutor.urls')),
    path('', include('at_risk.urls')),
    path('', include('gamification.urls')),
    path('', include('ide.urls')),
    path("operations/migration/", include("migration.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve static files from finders (app static/ dirs + STATICFILES_DIRS)
    # so we don't need to run collectstatic every time a new file is added
    # to an app's static folder. Production unchanged (this branch is
    # DEBUG-only; nginx/whitenoise still handle prod from STATIC_ROOT).
    urlpatterns += staticfiles_urlpatterns()
    
# Add the handler for the 500 error
handler500 = 'lms.views.custom_500_view'
handler403 = 'lms.views.custom_403_view'
