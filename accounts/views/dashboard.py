import logging

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)
from django.core.cache import cache
from course.models import Semester, SubjectEnrollment
from subject.models import Subject
from accounts.views.api_views import get_user_subject_count, get_student_count_per_course
from django.contrib.auth import get_user_model
from django.db.models.functions import TruncDate
from django.db.models import Count
from accounts.utils import fetch_facebook_posts
from datetime import datetime
from calendars.models import Event
from calendars.models import Announcement
from activity.models import Activity, StudentActivity
from itertools import chain
from django.utils.timezone import now
from django.shortcuts import render, redirect
from gamification.teacher_dashboard import teacher_dashboard as gamification_teacher_dashboard
from accounts.views.registrar import registrar_dashboard as registrar_ops_dashboard
from accounts.views.coil_admin import coil_admin_dashboard as coil_admin_ops_dashboard
from accounts.views.academic_director import academic_director_dashboard as academic_director_ops_dashboard
from accounts.views.program_head import program_head_dashboard as program_head_ops_dashboard
from accounts.views.time_keeper import time_keeper_dashboard as time_keeper_ops_dashboard
User = get_user_model()
from django.db.models import Q
from decimal import Decimal
import requests
from django.conf import settings

@login_required
def dashboard(request):
    today = timezone.now().date()
    one_week_ago = today - timedelta(days=7)

    user = request.user

    cache_key_subjects = f"subjects_{user.id}"

    subjects = cache.get(cache_key_subjects)
    courses = get_student_count_per_course(user)
    if subjects is None:
        subjects = get_user_subject_count(user)
        cache.set(cache_key_subjects, subjects, timeout=600)  

    cache_key_semester = "current_semester"
    current_semester = cache.get(cache_key_semester)
    if current_semester is None:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        cache.set(cache_key_semester, current_semester, timeout=600)

    # [Classedge LMS] Superusers go to the Super Admin dashboard (system-wide
    # control panel); the operational IT Admin role uses a different view.
    if user.is_superuser:
        return redirect("super_admin_dashboard")

    role_name = user.role_name
    is_teacher = role_name == 'teacher'
    is_student = role_name == 'student'
    is_registrar = role_name == 'registrar'
    is_coil_admin = role_name == 'coil admin'
    is_academic_director = role_name == 'academic director'
    is_program_head = role_name == 'program head'
    is_time_keeper = role_name == 'time keeper'
    # Accept both the literal "IT Admin" role and the legacy "Admin" role —
    # demo data ships with "Admin" while the seed command creates "IT Admin",
    # and both should land on the operations dashboard.
    is_it_admin = role_name in ('it admin', 'admin')

    if is_it_admin:
        return redirect("it_admin_dashboard")

    if is_student:
        return redirect("student_dashboard")

    if is_teacher:
        return gamification_teacher_dashboard(request)

    if is_registrar:
        return registrar_ops_dashboard(request)

    if is_coil_admin:
        return coil_admin_ops_dashboard(request)

    if is_academic_director:
        return academic_director_ops_dashboard(request)

    if is_program_head:
        return program_head_ops_dashboard(request)

    if is_time_keeper:
        return time_keeper_ops_dashboard(request)

    cache_key_active_students = f"active_users_{user.id}"
    active_users_per_day = cache.get(cache_key_active_students)
    if active_users_per_day is None:
        active_students = get_user_model().objects.filter(
            last_login__date__gte=one_week_ago,
            profile__role__name__iexact='student'
        ).distinct()

        active_users_per_day = active_students.annotate(
            date=TruncDate('last_login')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        cache.set(cache_key_active_students, list(active_users_per_day), timeout=600)

    cache_key_articles = "facebook_articles"
    articles = cache.get(cache_key_articles)
    if articles is None:
        articles = fetch_facebook_posts()
        cache.set(cache_key_articles, articles, timeout=600)

    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good Morning"
    elif 12 <= current_hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    subject_count = subjects.count()
    
    total_subject_count = 0
    if not is_teacher and current_semester:
        total_subject_count = Subject.objects.filter(
            subjectenrollment__semester=current_semester
        ).distinct().count()
    
    course_count = len(courses)

    events = Event.objects.filter(start_date__gte=today).order_by("start_date")[:5]
    for event in events:
        event.type = "event" 

    announcements = Announcement.objects.filter(date__gte=today).order_by("date")[:5]
    for announcement in announcements:
        announcement.type = "announcement"

    combined_list = sorted(
        chain(events, announcements), 
        key=lambda item: getattr(item, 'start_date', None) or getattr(item, 'date', None)
    )[:4]

    announcement_count = announcements.count()

    if is_student:
        enrolled_subjects = SubjectEnrollment.objects.filter(student=user).values_list("subject", flat=True)
        ongoing_activities = Activity.objects.filter(
            start_time__lte=now(),
            end_time__gte=now(),
            subject__in=enrolled_subjects  
        ).exclude(
            activity_type__name__iexact="Participation" 
        ).order_by("-start_time")
    else:
        ongoing_activities = Activity.objects.filter(
            start_time__lte=now(),
            end_time__gte=now()
        ).exclude(
            activity_type__name__iexact="Participation"
        ).order_by("-start_time")


    ongoing_activities_count = ongoing_activities.count() if ongoing_activities.exists() else 0

    total_enrolled_students = 0
    if current_semester:
        if is_teacher:
            teacher_subjects = Subject.objects.filter(
                Q(assign_teacher=user) | Q(substitute_teacher=user) | Q(collaborators=user)
            ).distinct()
            
            total_enrolled_students = SubjectEnrollment.objects.filter(
                semester=current_semester,
                status="enrolled",
                subject__in=teacher_subjects
            ).values("student").distinct().count()
        else:
            total_enrolled_students = SubjectEnrollment.objects.filter(
                semester=current_semester, 
                status="enrolled"
            ).values("student").distinct().count()

    pending_activity = StudentActivity.objects.filter(student=user, retake_count=0).count()

    # Fetch total payment for students
    total_payment = Decimal("0")
    if is_student and hasattr(user, 'email') and user.email:
        try:
            from rms.views import fetch_student_total_payment
            total_payment = fetch_student_total_payment(user.email)
        except Exception:
            logger.exception("fetch_student_total_payment failed for %s", user.email)
            total_payment = Decimal("0")
    
    context = {
        'active_users_count': active_users_per_day,
        'current_semester': current_semester,
        'articles': articles,
        'greeting': greeting,
        'user_name': user.first_name or user.username,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'is_registrar': is_registrar,
        'subject_count': subject_count,
        'course_count': course_count,
        'combined_list': combined_list,
        'announcement_count': announcement_count,
        'ongoing_activities_count': ongoing_activities_count,
        'total_enrolled_students': total_enrolled_students,
        'total_subject_count': total_subject_count,
        'pending_activity': pending_activity,
        'total_payment': total_payment,
    }

    return render(request, 'accounts/interface/dashboard.html', context)


def student_dashboard(request):
    today = timezone.now().date()

    user = request.user

    cache_key_subjects = f"subjects_{user.id}"

    subjects = cache.get(cache_key_subjects)
    courses = get_student_count_per_course(user)
    if subjects is None:
        subjects = get_user_subject_count(user)
        cache.set(cache_key_subjects, subjects, timeout=600)  

    cache_key_semester = "current_semester"
    current_semester = cache.get(cache_key_semester)
    if current_semester is None:
        current_semester = Semester.objects.filter(start_date__lte=today, end_date__gte=today).first()
        cache.set(cache_key_semester, current_semester, timeout=600)

    cache_key_articles = "facebook_articles"
    articles = cache.get(cache_key_articles)
    if articles is None:
        articles = fetch_facebook_posts()
        cache.set(cache_key_articles, articles, timeout=600)

    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good Morning"
    elif 12 <= current_hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    subject_count = subjects.count()
    

    events = Event.objects.filter(start_date__gte=today).order_by("start_date")[:5]
    for event in events:
        event.type = "event" 

    announcements = Announcement.objects.filter(date__gte=today).order_by("date")[:5]
    for announcement in announcements:
        announcement.type = "announcement"

    combined_list = sorted(
        chain(events, announcements), 
        key=lambda item: item.date if hasattr(item, 'date') else item.start_date
    )[:4]

    enrolled_subjects = SubjectEnrollment.objects.filter(student=user).values_list("subject", flat=True)
    now_ts = timezone.localtime(timezone.now())
    activities_qs = Activity.objects.filter(
        subject__in=enrolled_subjects,
        status=True,
    ).exclude(
        activity_type__name__iexact="Participation"
    ).exclude(
        studentquestion__is_participation=True
    )

    ongoing_activities = activities_qs.filter(
        start_time__lte=now_ts,
        end_time__gte=now_ts,
    ).order_by("end_time")

    upcoming_activities = activities_qs.filter(
        start_time__gt=now_ts,
    ).order_by("start_time")

    upcoming_due_activities = activities_qs.filter(
        end_time__gte=now_ts,
        end_time__lte=now_ts + timedelta(days=3),
    ).order_by("end_time")

    # Keep dashboard compact
    ongoing_activities_list = list(ongoing_activities[:5])
    upcoming_activities_list = list(upcoming_activities[:5])
    upcoming_due_activities_list = list(upcoming_due_activities[:5])

    todo_items = []
    for act in upcoming_due_activities_list:
        todo_items.append({
            "title": f"Submit: {act.activity_name}",
            "subtitle": f"Due {timezone.localtime(act.end_time).strftime('%b %d, %Y %I:%M %p')}" if act.end_time else "Due date not set",
            "url": f"/activity_detail/{act.id}",
        })


    ongoing_activities_count = ongoing_activities.count() if ongoing_activities.exists() else 0

    pending_activity = StudentActivity.objects.filter(student=user, retake_count=0).count()

    # Fetch total payment for students
    total_payment = Decimal("0")
    if hasattr(user, 'email') and user.email:
        try:
            from rms.views import fetch_student_total_payment
            total_payment = fetch_student_total_payment(user.email)
        except Exception:
            logger.exception("fetch_student_total_payment failed for %s", user.email)
            total_payment = Decimal("0")
    
    context = {
        'greeting': greeting,
        'user_name': user.first_name or user.username,
        'current_semester': current_semester,

        'articles': articles,
        'subject_count': subject_count,

        'combined_list': combined_list,
        'ongoing_activities_count': ongoing_activities_count,
        'pending_activity': pending_activity,
        'total_payment': total_payment,
        'ongoing_activities_list': ongoing_activities_list,
        'upcoming_activities_list': upcoming_activities_list,
        'upcoming_due_activities_list': upcoming_due_activities_list,
        'todo_items': todo_items,
    }

    return render(request, 'dashboard/student_dashboard.html', context)

