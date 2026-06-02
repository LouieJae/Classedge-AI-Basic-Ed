from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models.deletion import ProtectedError
from datetime import timedelta
from course.models import Semester
from subject.models import Subject, Schedule, EvaluationAssignment
from subject.forms.schedule import scheduleForm
from subject.serializers import ScheduleDataSerializer
from module.models import Module
from collections import defaultdict
from activity.models import Activity
from subject.utils import get_file_type
from rest_framework.response import Response
import os
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from subject.models import Schedule
from subject.serializers import ScheduleDataSerializer
from datetime import time
from datetime import datetime
from rest_framework.permissions import DjangoModelPermissions
from accounts.utils import paginate_queryset, get_pagination_context
from django.db.models import Q


class Schedule_Data(ModelViewSet):
    serializer_class = ScheduleDataSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    queryset = Schedule.objects.all()

@login_required
def schedule_list(request):
    today = timezone.now().date()

    current_semester = Semester.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()

    error_message = None
    formatted_schedule = []
    search_query = request.GET.get('search', '').strip()
    schedule_queryset = Schedule.objects.none()

    if not current_semester:
        error_message = 'No active semester found.'
    else:
        schedule_queryset = Schedule.objects.filter(semester=current_semester).select_related('subject', 'subject__assign_teacher')

        if search_query:
            schedule_queryset = schedule_queryset.filter(
                Q(subject__subject_name__icontains=search_query) |
                Q(subject__subject_short_name__icontains=search_query) |
                Q(subject__subject_code__icontains=search_query) |
                Q(subject__assign_teacher__first_name__icontains=search_query) |
                Q(subject__assign_teacher__last_name__icontains=search_query) |
                Q(subject__room_number__icontains=search_query) |
                Q(schedule_type__icontains=search_query) |
                Q(days_of_week__icontains=search_query)
            )

        for schedule in schedule_queryset:
            start_time = schedule.schedule_start_time.strftime("%I:%M %p").replace("AM", "A.M.").replace("PM", "P.M.")
            end_time = schedule.schedule_end_time.strftime("%I:%M %p").replace("AM", "A.M.").replace("PM", "P.M.")
            formatted_schedule.append({
                'subject': schedule.subject,
                'schedule_start_time': start_time,
                'schedule_end_time': end_time,
                'schedule_type': schedule.schedule_type,
                'days_of_week': schedule.days_of_week,
                'room_number': schedule.subject.room_number,
                'assign_teacher': schedule.subject.assign_teacher,
                'id': schedule.id
            })

    page_obj, paginator = paginate_queryset(formatted_schedule, request, items_per_page=10)
    pagination_context = get_pagination_context(page_obj, request)

    context = {
        'form': scheduleForm(),
        'page_obj': page_obj,
        'error': error_message,
        'current_semester': current_semester,
        'search_query': search_query,
    }
    context.update(pagination_context)

    return render(request, 'schedule/schedule_list.html', context)


@login_required
@permission_required('subject.add_schedule', raise_exception=True)
def create_schedule(request):
    # GET → render the standalone create page.
    if request.method != 'POST':
        form = scheduleForm()
        return render(request, 'schedule/create_schedule.html', {'form': form})

    form = scheduleForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Please correct the errors in the form.")
        return render(request, 'schedule/create_schedule.html', {'form': form})

    # Prepare base schedule info
    schedule = form.save(commit=False)
    subject = form.cleaned_data['subject']
    schedule.subject = subject
    assign_teacher = subject.assign_teacher
    room_number = subject.room_number

    schedule_start_time = form.cleaned_data['schedule_start_time']
    schedule_end_time = form.cleaned_data['schedule_end_time']
    days_of_week = form.cleaned_data['days_of_week']

    # 🔹 Get the current semester based on today's date
    today = timezone.localdate()
    current_semester = Semester.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()

    if not current_semester:
        messages.error(request, "No active semester found. Please set up the current semester.")
        return render(request, 'schedule/create_schedule.html', {'form': form})

    schedule.semester = current_semester

    # 🔹 Time validation
    if schedule_start_time >= schedule_end_time:
        messages.error(request, "End time must be after the start time.")
        return render(request, 'schedule/create_schedule.html', {'form': form})

    # 🔹 Subject conflict check (same subject, same semester)
    overlapping_schedules = Schedule.objects.filter(
        subject=subject,
        semester=current_semester,
        schedule_start_time__lt=schedule_end_time,
        schedule_end_time__gt=schedule_start_time
    )
    for existing_schedule in overlapping_schedules:
        if any(day in existing_schedule.days_of_week for day in days_of_week):
            messages.error(request, "This subject already has a class scheduled at this time on the selected days.")
            return render(request, 'schedule/create_schedule.html', {'form': form})

    # 🔹 Room conflict check (same room, same semester) — only when the subject
    # actually has a room assigned; otherwise the filter `room_number=None` would
    # collide with every other room-less subject and produce a false positive.
    if room_number:
        room_conflict = Schedule.objects.filter(
            subject__room_number=room_number,
            semester=current_semester,
            schedule_start_time__lt=schedule_end_time,
            schedule_end_time__gt=schedule_start_time
        ).exclude(subject=subject)
        for existing_schedule in room_conflict:
            if any(day in existing_schedule.days_of_week for day in days_of_week):
                messages.error(
                    request,
                    f"Room '{room_number}' is already booked at this time on the selected days."
                )
                return render(request, 'schedule/create_schedule.html', {'form': form})

    # 🔹 Teacher conflict check (same teacher, same semester) — only when the
    # subject has an assigned teacher; same false-positive concern as above.
    if assign_teacher:
        teacher_conflict = Schedule.objects.filter(
            subject__assign_teacher=assign_teacher,
            semester=current_semester,
            schedule_start_time__lt=schedule_end_time,
            schedule_end_time__gt=schedule_start_time
        ).exclude(subject=subject)
        for existing_schedule in teacher_conflict:
            if any(day in existing_schedule.days_of_week for day in days_of_week):
                messages.error(
                    request,
                    f"Teacher '{assign_teacher}' already has a subject scheduled at this time "
                    f"on {', '.join(days_of_week)}."
                )
                return render(request, 'schedule/create_schedule.html', {'form': form})

    # 🔹 Save the schedule
    schedule.save()
    messages.success(
        request,
        f"Schedule created successfully for {current_semester.semester_name}!"
    )
    return redirect('schedule')


@login_required
@permission_required('subject.change_schedule', raise_exception=True)
def update_schedule(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    subject = schedule.subject
    assign_teacher = subject.assign_teacher
    room_number = subject.room_number

    # 🔹 Always determine the current semester by date
    today = timezone.localdate()
    current_semester = Semester.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()

    if not current_semester:
        messages.error(request, "No active semester found. Please set up the current semester first.")
        return redirect('schedule')

    if request.method == 'POST':
        form = scheduleForm(request.POST, instance=schedule)

        # Basic validation for day selection
        days_of_week = request.POST.getlist('days_of_week')
        if not days_of_week:
            messages.error(request, "Please select at least one day of the week.")
            return render(request, 'schedule/update_schedule.html',
                          {'form': form, 'schedule': schedule, 'subject': subject})

        if form.is_valid():
            updated_schedule = form.save(commit=False)
            schedule_start_time = form.cleaned_data['schedule_start_time']
            schedule_end_time = form.cleaned_data['schedule_end_time']
            days_of_week = set(form.cleaned_data['days_of_week'])

            update_ctx = {'form': form, 'schedule': schedule, 'subject': subject}

            # 🔹 Validate times
            if schedule_start_time >= schedule_end_time:
                messages.error(request, "End time must be after the start time.")
                return render(request, 'schedule/update_schedule.html', update_ctx)

            # 🔹 Check for same-subject overlaps (within current semester)
            subject_conflicts = Schedule.objects.filter(
                subject=subject,
                semester=current_semester,
                schedule_start_time__lt=schedule_end_time,
                schedule_end_time__gt=schedule_start_time
            ).exclude(pk=schedule.pk)

            for existing_schedule in subject_conflicts:
                if days_of_week.intersection(set(existing_schedule.days_of_week)):
                    messages.error(
                        request,
                        "This subject already has a schedule at this time on the selected days."
                    )
                    return render(request, 'schedule/update_schedule.html', update_ctx)

            # 🔹 Teacher conflict (same teacher, same semester) — skip when the
            # subject has no assigned teacher.
            if assign_teacher:
                teacher_conflicts = Schedule.objects.filter(
                    subject__assign_teacher=assign_teacher,
                    semester=current_semester,
                    schedule_start_time__lt=schedule_end_time,
                    schedule_end_time__gt=schedule_start_time
                ).exclude(pk=schedule.pk)

                for existing_schedule in teacher_conflicts:
                    if days_of_week.intersection(set(existing_schedule.days_of_week)):
                        teacher_name = assign_teacher.get_full_name() if hasattr(assign_teacher, 'get_full_name') else str(assign_teacher)
                        messages.error(
                            request,
                            f"Teacher '{teacher_name}' already has a class at this time on the selected days."
                        )
                        return render(request, 'schedule/update_schedule.html', update_ctx)

            # 🔹 Room conflict (same room, same semester) — skip when the
            # subject has no room assigned, otherwise None == None matches all
            # room-less subjects and creates a false positive.
            if room_number:
                room_conflicts = Schedule.objects.filter(
                    subject__room_number=room_number,
                    semester=current_semester,
                    schedule_start_time__lt=schedule_end_time,
                    schedule_end_time__gt=schedule_start_time
                ).exclude(pk=schedule.pk)

                for existing_schedule in room_conflicts:
                    if days_of_week.intersection(set(existing_schedule.days_of_week)):
                        messages.error(
                            request,
                            f"Room '{room_number}' is already booked at this time on the selected days for another subject."
                        )
                        return render(request, 'schedule/update_schedule.html', update_ctx)

            # 🔹 Assign the validated semester
            updated_schedule.semester = current_semester
            updated_schedule.save()

            messages.success(
                request,
                f"Schedule updated successfully for {current_semester.semester_name}!"
            )
            return redirect('schedule')

        else:
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'schedule/update_schedule.html',
                          {'form': form, 'schedule': schedule, 'subject': subject})

    else:
        form = scheduleForm(instance=schedule)

    return render(
        request,
        'schedule/update_schedule.html',
        {
            'form': form,
            'schedule': schedule,
            'subject': subject
        }
    )

@login_required
@permission_required('subject.delete_schedule', raise_exception=True)
def delete_schedule(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    if request.method == 'POST':
        try:
            schedule.delete()
            return JsonResponse({'status': 'success'})
        except ProtectedError:
            return JsonResponse({
                'status': 'error',
                'error_type': 'ProtectedError',
                'message': 'This schedule is protected and cannot be deleted.'
            })
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


class ScheduleAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, subject_id, semester_id=None):
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"error": "Subject not found"}, status=404)

        selected_month = request.GET.get('month', None)

        # Get Semester
        if semester_id and semester_id != "None":
            try:
                semester = Semester.objects.get(id=int(semester_id))
            except (Semester.DoesNotExist, ValueError):
                return Response({"error": "Semester not found"}, status=404)
        else:
            current_date = timezone.localdate()
            try:
                semester = Semester.objects.get(start_date__lte=current_date, end_date__gte=current_date)
            except Semester.DoesNotExist:
                return Response({"error": "Current semester not found"}, status=404)

        semester_start = semester.start_date
        semester_end = semester.end_date

        # Get months in semester
        months_in_semester = []
        current_date = semester_start
        while current_date <= semester_end:
            month_name = current_date.strftime('%B')
            if month_name not in months_in_semester:
                months_in_semester.append(month_name)
            current_date = current_date.replace(day=28) + timedelta(days=4)

        # Ensure that weeks start on Sunday
        first_day_of_month = semester_start.replace(day=1)
        first_week_start = first_day_of_month
        while first_week_start.weekday() != 6:  # Move to the previous Sunday
            first_week_start -= timedelta(days=1)

        week_schedule = {}
        current_week_start = first_week_start
        week_number = 1

        schedules = Schedule.objects.filter(subject=subject)

        # Get modules (lessons) that fall within the given date range
        modules = Module.objects.filter(
            subject=subject, start_date__lte=semester_end, end_date__gte=first_week_start
        )

        while current_week_start <= semester_end:
            current_week_end = current_week_start + timedelta(days=6)  # Week ends on Saturday
            
            # Store the week range as Sunday-Saturday
            week_start_str = current_week_start.strftime("%B %d")
            week_end_str = current_week_end.strftime("%B %d")
            
            # Collect unique modules for this week
            week_modules = {}
            week_schedule_times = []
            
            for day in range(7):
                date = current_week_start + timedelta(days=day)
                
                # Check modules for this date
                for module in modules:
                    # Convert to local timezone before extracting date
                    module_start_date = timezone.localtime(module.start_date).date()
                    module_end_date = timezone.localtime(module.end_date).date()
                    
                    if module_start_date <= date and module_end_date >= date:
                        if module.id not in week_modules:
                            # Get activities linked via the additional_modules ManyToMany field
                            activities = Activity.objects.filter(additional_modules=module, status=True).distinct()

                            activities_list = [
                                {
                                    "activity_id": activity.id,
                                    "activity_name": activity.activity_name,
                                    "activity_type": activity.activity_type.name if activity.activity_type else "N/A",
                                    "start_time": timezone.localtime(activity.start_time).strftime("%I:%M %p") if activity.start_time else None,
                                    "end_time": timezone.localtime(activity.end_time).strftime("%I:%M %p") if activity.end_time else None,
                                    "max_score": activity.max_score,
                                    "status": activity.status,
                                }
                                for activity in activities
                                if activity.activity_type.name.lower() != "participation"
                            ]

                            week_modules[module.id] = {
                                "module_id": module.id,
                                "lesson": module.file_name,
                                "description": module.description or "",
                                "file_url": module.file.url if module.file else None,
                                "embed": module.iframe_code if module.iframe_code else None,
                                "file_extension": os.path.splitext(module.file.name)[1].lower() if module.file else None,
                                "url": module.url if module.url else None,
                                "allow_download": module.allow_download,
                                "type": get_file_type(module),
                                "start_date": module_start_date.strftime("%Y-%m-%d"),
                                "end_date": module_end_date.strftime("%Y-%m-%d"),
                                "activities": activities_list
                            }
                
                # Collect schedule times for this week
                for schedule in schedules:
                    if schedule.days_of_week and date.strftime("%a") in schedule.days_of_week:
                        schedule_time = f"{format_time(schedule.schedule_start_time)} to {format_time(schedule.schedule_end_time)}"
                        if schedule_time not in week_schedule_times:
                            week_schedule_times.append(schedule_time)
            
            # Only add week if it has modules
            if week_modules:
                week_schedule[week_number] = {
                    "week": f"Week {week_number} - {week_start_str} to {week_end_str}",
                    "week_start": current_week_start.strftime("%Y-%m-%d"),
                    "week_end": current_week_end.strftime("%Y-%m-%d"),
                    "schedule_times": week_schedule_times,
                    "lessons": list(week_modules.values())
                }
                week_number += 1

            current_week_start += timedelta(days=7)

        formatted_schedule = [week_data for week_num, week_data in week_schedule.items()]

        # Filter by selected month if provided
        if selected_month:
            # Convert month name to month number for filtering
            from datetime import datetime as dt
            try:
                month_num = dt.strptime(selected_month, '%B').month
                month_str = f"-{month_num:02d}-"  # Format: -MM-
                formatted_schedule = [
                    week_data for week_data in formatted_schedule
                    if month_str in week_data['week_start'] or month_str in week_data['week_end']
                ]
            except ValueError:
                # If month parsing fails, return all weeks
                pass

        # Fetch Available Evaluations
        available_evaluations = None
        if request.user.is_authenticated:
            if hasattr(request.user, "profile") and getattr(request.user.profile.role, "name", "").lower() == "student":
                available_evaluations = EvaluationAssignment.objects.filter(
                    subject=subject,
                    semester=semester,
                    is_visible=True
                ).exclude(
                    evaluations__student=request.user
                ).select_related('teacher', 'subject').distinct()

        evaluations_list = [
            {
                "evaluation_id": evaluation.id,
                "teacher": f"{evaluation.teacher.first_name} {evaluation.teacher.last_name}",
                "subject": evaluation.subject.subject_name,
                "is_visible": evaluation.is_visible,
            }
            for evaluation in available_evaluations
        ] if available_evaluations else []

        return Response({
            'semester_months': months_in_semester,
            'schedule_data': formatted_schedule,
            'available_evaluations': evaluations_list 
        }, status=200)


def format_time(time_value):
    if not time_value:
        return None

    # If already a datetime.time object, format it directly
    if isinstance(time_value, time):
        return time_value.strftime("%I:%M %p").lstrip("0")  # 12-hour format with AM/PM

    try:
        # If it's a string, convert it to a time object first
        time_obj = datetime.strptime(time_value, "%H:%M:%S").time()
        return time_obj.strftime("%I:%M %p").lstrip("0")  # 12-hour format with AM/PM
    except (ValueError, TypeError):
        return time_value 
    
class Classroom_Mode_ScheduleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id, semester_id=None):
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"error": "Subject not found"}, status=404)

        selected_month = request.GET.get('month', None)

        # Get Semester
        if semester_id and semester_id != "None":
            try:
                semester = Semester.objects.get(id=int(semester_id))
            except (Semester.DoesNotExist, ValueError):
                return Response({"error": "Semester not found"}, status=404)
        else:
            current_date = timezone.localdate()
            try:
                semester = Semester.objects.get(start_date__lte=current_date, end_date__gte=current_date)
            except Semester.DoesNotExist:
                return Response({"error": "Current semester not found"}, status=404)

        semester_start = semester.start_date
        semester_end = semester.end_date

        # Get months in semester
        months_in_semester = []
        current_date = semester_start
        while current_date <= semester_end:
            month_name = current_date.strftime('%B')
            if month_name not in months_in_semester:
                months_in_semester.append(month_name)
            current_date = current_date.replace(day=28) + timedelta(days=4)

        # Ensure that weeks start on Sunday
        first_day_of_month = semester_start.replace(day=1)
        first_week_start = first_day_of_month
        while first_week_start.weekday() != 6:  # Move to the previous Sunday
            first_week_start -= timedelta(days=1)

        week_schedule = {}
        current_week_start = first_week_start
        week_number = 1

        schedules = Schedule.objects.filter(subject=subject)

        # Get modules (lessons) that fall within the given date range
        modules = Module.objects.filter(
            subject=subject, start_date__lte=semester_end, end_date__gte=first_week_start
        )

        while current_week_start <= semester_end:
            current_week_end = current_week_start + timedelta(days=6)  # Week ends on Saturday
            week_schedule[week_number] = {
                "week": f"Week {week_number}",
                "week_start": current_week_start.strftime("%Y-%m-%d"),
                "week_end": current_week_end.strftime("%Y-%m-%d"),
                "dates": []
            }

            # Store the week range as Sunday-Saturday
            week_start_str = current_week_start.strftime("%B %d")
            week_end_str = current_week_end.strftime("%B %d")

            for day in range(7):
                date = current_week_start + timedelta(days=day)
                formatted_date = date.strftime("%Y-%m-%d")

                lessons_for_date = []
                unique_modules = set()

                for schedule in schedules:
                    if date.strftime("%a") in schedule.days_of_week:
                        for module in modules:
                            # Convert to local timezone before extracting date
                            module_start_date = timezone.localtime(module.start_date).date()
                            module_end_date = timezone.localtime(module.end_date).date()
                            
                            if module_start_date <= date and module_end_date >= date:
                                if module.id not in unique_modules:
                                    unique_modules.add(module.id)
                                    # Get activities linked via the additional_modules ManyToMany field
                                    activities = Activity.objects.filter(additional_modules=module, status=True).distinct()

                                    activities_list = [
                                        {
                                            "activity_id": activity.id,
                                            "activity_name": activity.activity_name,
                                            "activity_type": activity.activity_type.name if activity.activity_type else "N/A",
                                            "start_time": timezone.localtime(activity.start_time).strftime("%I:%M %p") if activity.start_time else None,
                                            "end_time": timezone.localtime(activity.end_time).strftime("%I:%M %p") if activity.end_time else None,
                                            "max_score": activity.max_score,
                                            "status": activity.status,
                                        }
                                        for activity in activities
                                        if activity.activity_type.name.lower() != "participation"
                                    ]

                                    lessons_for_date.append({
                                        "module_id": module.id,
                                        "lesson": module.file_name,
                                        "description": module.description or "",
                                        "file_url": module.file.url if module.file else None,
                                        "embed": module.iframe_code if module.iframe_code else None,
                                        "file_extension": os.path.splitext(module.file.name)[1].lower() if module.file else None,
                                        "url": module.url if module.url else None,
                                        "allow_download": module.allow_download,
                                        "type": get_file_type(module),
                                        "activities": activities_list
                                    })

                # Append lessons to the correct date
                week_schedule[week_number]["dates"].append({
                    "date": formatted_date,
                    "day": date.strftime("%A"),
                    "time": f"{format_time(schedule.schedule_start_time)} to {format_time(schedule.schedule_end_time)}"
                            if schedule.schedule_start_time and schedule.schedule_end_time else None,
                    "lessons": lessons_for_date,
                })

            # Update the week label to include the full range
            week_schedule[week_number]["week"] = f"Week {week_number} - {week_start_str} to {week_end_str}"

            current_week_start += timedelta(days=7)
            week_number += 1

        formatted_schedule = [week_data for week_num, week_data in week_schedule.items() if week_data["dates"]]

        # Modify filtering to include previous month's data in the first week
        if selected_month:
            formatted_schedule = [
                {
                    "week": week_data["week"],
                    "dates": [
                        date for date in week_data["dates"]
                        if selected_month in date['date'] or week_num == 1  # Ensure Week 1 is always included
                    ]
                }
                for week_num, week_data in week_schedule.items() if week_data["dates"]
            ]

        # Fetch Available Evaluations
        available_evaluations = None
        if request.user.is_authenticated:
            if hasattr(request.user, "profile") and getattr(request.user.profile.role, "name", "").lower() == "student":
                available_evaluations = EvaluationAssignment.objects.filter(
                    subject=subject,
                    semester=semester,
                    is_visible=True
                ).exclude(
                    evaluations__student=request.user
                ).select_related('teacher', 'subject').distinct()

        evaluations_list = [
            {
                "evaluation_id": evaluation.id,
                "teacher": f"{evaluation.teacher.first_name} {evaluation.teacher.last_name}",
                "subject": evaluation.subject.subject_name,
                "is_visible": evaluation.is_visible,
            }
            for evaluation in available_evaluations
        ] if available_evaluations else []

        return Response({
            'semester_months': months_in_semester,
            'schedule_data': formatted_schedule,
            'available_evaluations': evaluations_list 
        }, status=200)
