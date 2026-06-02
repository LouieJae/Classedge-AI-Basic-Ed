from module.models.module import Module
from subject.models import  Subject
from accounts.models import Profile
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from datetime import date
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, F, Q
from activity.models import ActivityType
from django.utils.timezone import localtime, now as timezone_now
from datetime import timedelta
from django.contrib.sessions.models import Session
from course.models import Semester, SubjectEnrollment
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404
User = get_user_model()
from django.core.cache import cache


@login_required
def get_teacher_progress_report(request):
    data_by_subject = {} 


    semesters = Semester.objects.all().order_by("start_date")
    modules = Module.objects.exclude(start_date__isnull=True, end_date__isnull=True).order_by("start_date")

    for semester in semesters:
        current_date = semester.start_date
        semester_end_date = semester.end_date
        semester_months = set()

        while current_date <= semester_end_date:
            month_year = current_date.strftime("%B %Y") 
            semester_months.add(month_year)
            current_date = date(
                current_date.year + (1 if current_date.month == 12 else 0),
                1 if current_date.month == 12 else current_date.month + 1,
                1
            )

        num_months = len(semester_months)
        percentage_per_month = round(100 / num_months, 2) if num_months > 0 else 0

        for subject in Subject.objects.all():
            teacher = subject.active_teacher 
            teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown Teacher"

            subject_key = f"{subject.subject_name} (ID: {subject.id})"
            if subject_key not in data_by_subject:
                data_by_subject[subject_key] = {
                    "teacher_name": teacher_name, 
                    "total_progress": 0,
                    "data_by_month": {}
                }

            for month_year in semester_months:
                if month_year not in data_by_subject[subject_key]["data_by_month"]:
                    data_by_subject[subject_key]["data_by_month"][month_year] = {
                        "semesters": [],
                        "modules_count": 0
                    }

                data_by_subject[subject_key]["data_by_month"][month_year]["semesters"].append({
                    "semester_name": semester.semester_name,
                    "percentage": percentage_per_month
                })

    for module in modules:
        subject = module.subject
        teacher = subject.active_teacher 
        subject_key = f"{subject.subject_name} (ID: {subject.id})"

        if subject_key not in data_by_subject:
            data_by_subject[subject_key] = {
                "teacher_name": teacher_name, 
                "total_progress": 0,
                "data_by_month": {}
            }
        current_date = module.start_date.date()
        module_end_date = module.end_date.date()

        while current_date <= module_end_date:
            month_year = current_date.strftime("%B %Y")

            if month_year in data_by_subject[subject_key]["data_by_month"]:
                data_by_subject[subject_key]["data_by_month"][month_year]["modules_count"] += 1

            next_month = current_date.month + 1 if current_date.month < 12 else 1
            next_year = current_date.year if current_date.month < 12 else current_date.year + 1
            current_date = date(next_year, next_month, 1)

    for key, details in data_by_subject.items():
        total_progress = 0
        for month_year, month_data in details["data_by_month"].items():
            has_modules = month_data["modules_count"] > 0
            assigned_percentage = month_data["semesters"][0]["percentage"] if month_data["semesters"] else 0

            month_data["percentage"] = assigned_percentage if has_modules else 0
            total_progress += month_data["percentage"] if has_modules else 0

        details["total_progress"] = f"{total_progress:.2f}% out of 100%"

    response_data = {
        "progress_by_subject": data_by_subject  
    }

    return JsonResponse(response_data, safe=False)


_LOGIN_STATUS_MAP = {
    "Active Now": "success",
    "Recently Logged Out (<5 min)": "warning",
    "Away": "warning",
    "Recently Logged Out": "muted",
    "Logged Out More Than a Day Ago": "info",
    "Inactive (Few Days)": "info",
    "Inactive (1+ Month)": "danger",
    "Never Logged In": "muted",
}


def _login_report_table_ctx(label_singular, icon):
    return {
        "title": f"{label_singular.title()} Login Records",
        "icon": icon,
        "search_placeholder": f"Search {label_singular}s by name...",
        "empty_icon": icon,
        "empty_label": f"{label_singular} login records",
        "columns": [
            {"label": "#", "width": "60px", "type": "index"},
            {"label": "Name", "type": "name", "name_attr": "name"},
            {"label": "Status", "type": "status", "attr": "status", "map": _LOGIN_STATUS_MAP},
            {"label": "Last Login", "type": "meta", "attr": "last_login"},
        ],
    }


def _filter_login_rows(rows, search_query):
    if not search_query:
        return rows
    q = search_query.lower()
    return [r for r in rows if q in (r.get("name") or "").lower()]


@login_required
def teacher_login_report(request):
    from accounts.utils import get_pagination_context, paginate_queryset

    now = localtime()

    five_minutes_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    all_teachers = User.objects.filter(profile__role__name__iexact='teacher')

    active_sessions = Session.objects.filter(expire_date__gte=now)
    active_users = set()

    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            active_users.add(int(user_id))

    teacher_data = []
    active_now_count = 0

    for teacher in all_teachers:
        last_login = teacher.last_login

        if teacher.id in active_users:
            status = "Active Now"
            active_now_count += 1
            last_online = "Currently Online"
        elif last_login and last_login >= five_minutes_ago:
            status = "Recently Logged Out (<5 min)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_hour_ago:
            status = "Away"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_day_ago:
            status = "Recently Logged Out"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_week_ago:
            status = "Logged Out More Than a Day Ago"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_month_ago:
            status = "Inactive (Few Days)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login < one_month_ago:
            status = "Inactive (1+ Month)"
            last_online = "More than a month ago"
        else:
            status = "Never Logged In"
            last_online = "Never Logged In"

        teacher_data.append({
            "id": teacher.id,
            "name": teacher.get_full_name() or teacher.username,
            "last_login": last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "Never Logged In",
            "status": status,
            "last_online": last_online
        })

    search_query = request.GET.get("search", "").strip()
    rows = _filter_login_rows(teacher_data, search_query)
    page_obj, _ = paginate_queryset(rows, request, items_per_page=10)
    context = {
        "active_now_count": active_now_count,
        "search_query": search_query,
        **_login_report_table_ctx("teacher", "fa-chalkboard-teacher"),
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "accounts/reports/teacher_login_report.html", context)


@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def enrollment_report(request, student_id):
    student_profile = get_object_or_404(Profile, id=student_id)
    
    enrolled_subjects = SubjectEnrollment.objects.filter(
        student=student_profile.user, 
        status="enrolled"
    ).select_related("subject", "semester")

    return render(request, 'accounts/reports/enrollment_report.html', {
        'enrolled_subjects': enrolled_subjects,
        'student_profile': student_profile
    })

@login_required
def student_login_report(request):
    from accounts.utils import get_pagination_context, paginate_queryset

    now = localtime(timezone_now())

    five_minutes_ago = now - timedelta(minutes=5)
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    all_students = User.objects.filter(profile__role__name__iexact='student')

    active_sessions = Session.objects.filter(expire_date__gte=now)
    active_users = set()

    for session in active_sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            active_users.add(int(user_id))

    student_data = []
    active_now_count = 0

    for student in all_students:
        last_login = student.last_login

        if student.id in active_users:
            status = "Active Now"
            active_now_count += 1
            last_online = "Currently Online"
        elif last_login and last_login >= five_minutes_ago:
            status = "Recently Logged Out (<5 min)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_hour_ago:
            status = "Away"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_day_ago:
            status = "Recently Logged Out"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_week_ago:
            status = "Logged Out More Than a Day Ago"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login >= one_month_ago:
            status = "Inactive (Few Days)"
            last_online = last_login.strftime("%Y-%m-%d %H:%M:%S")
        elif last_login and last_login < one_month_ago:
            status = "Inactive (1+ Month)"
            last_online = "More than a month ago"
        else:
            status = "Never Logged In"
            last_online = "Never Logged In"

        student_data.append({
            "id": student.id,
            "name": student.get_full_name() or student.username,
            "last_login": last_login.strftime("%Y-%m-%d %H:%M:%S") if last_login else "Never Logged In",
            "status": status,
            "last_online": last_online
        })

    search_query = request.GET.get("search", "").strip()
    rows = _filter_login_rows(student_data, search_query)
    page_obj, _ = paginate_queryset(rows, request, items_per_page=10)
    context = {
        "active_now_count": active_now_count,
        "search_query": search_query,
        **_login_report_table_ctx("student", "fa-user-graduate"),
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "accounts/reports/student_login_report.html", context)


@login_required
def teacher_progress_report(request):
    return render(request, 'accounts/reports/teacher_progress_report.html')


@login_required
def subject_report(request):
    user = request.user
    selected_semester_id = request.GET.get("semester")
    teacher_id = request.GET.get("teacher_id")  

    cache_key = f"student_per_subject_{user.id}_{selected_semester_id or 'current'}_{teacher_id or 'all'}"
    data = cache.get(cache_key)
    if data:
        return render(request, "accounts/reports/subject_report.html", {"subjects": data})

    selected_semester = None
    if selected_semester_id:
        selected_semester = get_object_or_404(Semester, id=selected_semester_id)
    else:
        now = timezone.localtime(timezone.now())
        selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if not selected_semester:
        return render(request, "accounts/reports/subject_report.html", {"subjects": []})

    role_name = user.role_name
    is_teacher = role_name == "teacher"
    is_student = role_name == "student"
    is_registrar = role_name == "registrar"

    if not teacher_id and is_teacher:
        teacher_id = user.id

    if is_registrar and teacher_id:
        teacher = get_object_or_404(User, id=teacher_id)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=teacher, semester=selected_semester
        )
    elif is_teacher:
        student_enrollments = SubjectEnrollment.objects.filter(
            subject__assign_teacher=user, semester=selected_semester
        )
    elif is_student:
        student_subjects = SubjectEnrollment.objects.filter(
            student=user, semester=selected_semester
        ).values_list("subject", flat=True)
        student_enrollments = SubjectEnrollment.objects.filter(
            subject_id__in=student_subjects, semester=selected_semester
        )
    else:
        student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

    student_counts = student_enrollments.values(
        subject_name=F("subject__subject_name"),
        subject_short_name=F("subject__subject_code")
    ).annotate(
        student_count=Count("student")
    ).order_by("subject__subject_name")

    subjects = [
        {
            "subject_name": entry["subject_name"],
            "subject_short_name": entry["subject_short_name"],
            "student_count": entry["student_count"]
        }
        for entry in student_counts
    ]

    cache.set(cache_key, subjects, timeout=600)
    return render(request, 'accounts/reports/subject_report.html', {"subjects": subjects})


_COURSE_REPORT_COLUMNS = [
    {"label": "#", "width": "60px", "type": "index"},
    {"label": "Program", "type": "name", "name_attr": "course_name"},
    {"label": "Code", "type": "pill", "attr": "course_short_name"},
    {"label": "Year Level", "type": "meta", "attr": "year_level"},
    {"label": "Students", "type": "meta", "attr": "student_count"},
]


@login_required
def course_report(request):
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset
    user = request.user
    selected_semester_id = request.GET.get("semester")
    cache_key = f"student_per_course_{user.id}_{selected_semester_id or 'current'}"

    courses = cache.get(cache_key)
    if courses is None:
        selected_semester = None
        if selected_semester_id and selected_semester_id != "None":
            selected_semester = get_object_or_404(Semester, id=selected_semester_id)
        else:
            now = timezone.localtime(timezone.now())
            selected_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

        if not selected_semester:
            courses = []
        else:
            if hasattr(user, "profile") and user.is_teacher:
                teacher_subjects = Subject.objects.filter(assign_teacher=user)
                student_enrollments = SubjectEnrollment.objects.filter(
                    subject__in=teacher_subjects, semester=selected_semester
                )
            else:
                student_enrollments = SubjectEnrollment.objects.filter(semester=selected_semester)

            student_counts = Profile.objects.filter(
                id__in=student_enrollments.values("student"),
                course__isnull=False,
                grade_year_level__isnull=False,
            ).values(
                course_name=F("course__name"),
                course_short_name=F("course__short_name"),
                year_level=F("grade_year_level"),
            ).annotate(
                student_count=Count("id")
            ).order_by("course__name", "year_level")

            courses = [
                {
                    "course_name": e["course_name"],
                    "course_short_name": e["course_short_name"],
                    "year_level": e["year_level"],
                    "student_count": e["student_count"],
                }
                for e in student_counts
            ]
        cache.set(cache_key, courses, timeout=600)

    search_query = request.GET.get("search", "").strip()
    if search_query:
        q = search_query.lower()
        courses = [c for c in courses if q in (c.get("course_name") or "").lower()
                   or q in (c.get("course_short_name") or "").lower()]
    page_obj, _ = paginate_queryset(courses, request, items_per_page=10)
    context = {
        "search_query": search_query,
        "title": "Students Per Program",
        "icon": "fa-graduation-cap",
        "search_placeholder": "Search by course name or code...",
        "empty_icon": "fa-graduation-cap",
        "empty_label": "course records",
        "columns": _COURSE_REPORT_COLUMNS,
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get("partial") == "1":
        return render(request, "includes/_list_table.html", context)
    return render(request, "accounts/reports/course_report.html", context)

