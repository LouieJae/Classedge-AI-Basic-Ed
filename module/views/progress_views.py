from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q

from activity.models import Activity, ActivityQuestion, StudentQuestion
from ..models.module import Module
from ..models.student_progress import StudentProgress


@login_required
def module_progress(request):
    if request.method == 'GET':
        module_id = request.GET.get('module_id')
        if not module_id:
            return JsonResponse({'status': 'error', 'message': 'module_id required'}, status=400)
        try:
            record = StudentProgress.objects.get(
                student=request.user, module_id=module_id
            )
            return JsonResponse({
                'status': 'success',
                'progress': float(record.progress),
                'last_page': record.last_page,
                'completed': record.completed,
                'time_spent': record.time_spent,
            })
        except StudentProgress.DoesNotExist:
            return JsonResponse({
                'status': 'success',
                'progress': 0,
                'last_page': 1,
                'completed': False,
                'time_spent': 0,
            })

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        module_id = data.get('module_id')
        progress_value = data.get('progress')
        last_page = data.get('last_page', 1)

        module = Module.objects.get(id=module_id)
        student = request.user

        progress_record, _ = StudentProgress.objects.get_or_create(
            student=student,
            module=module,
            defaults={'last_page': last_page, 'progress': progress_value, 'time_spent': 0}
        )

        now = timezone.now()

        if progress_record.last_accessed and request.session.get('is_active', False):
            time_delta = now - progress_record.last_accessed
            added_time = int(time_delta.total_seconds())
            progress_record.time_spent += added_time
            request.session['is_active'] = False

        progress_record.progress = progress_value
        progress_record.last_page = last_page
        progress_record.last_accessed = now
        if progress_record.first_accessed is None:
            progress_record.first_accessed = now
        try:
            if float(progress_value) >= 100:
                progress_record.completed = True
        except (TypeError, ValueError):
            pass
        progress_record.save()

        return JsonResponse({'status': 'success', 'progress': float(progress_record.progress)})

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def start_module_session(request):
    if request.method == 'POST':
        request.session['is_active'] = True
        return JsonResponse({'status': 'session started'})


@login_required
def stop_module_session(request):
    if request.method == 'POST':
        request.session['is_active'] = False
        return JsonResponse({'status': 'session stopped'})


@login_required
def progress_list(request):
    module_ids = StudentProgress.objects.filter(
        student__profile__role__name__iexact='student',
        module__isnull=False
    ).values('module_id').distinct()
    module_progress = Module.objects.filter(id__in=module_ids).select_related('subject')

    activity_ids = StudentProgress.objects.filter(
        student__profile__role__name__iexact='student',
        activity__isnull=False
    ).values('activity_id').distinct()
    activity_progress = Activity.objects.filter(pk__in=activity_ids).select_related('subject')

    from collections import defaultdict
    subjects = defaultdict(lambda: {'modules': [], 'activities': []})

    for module in module_progress:
        subjects[module.subject]['modules'].append(module)

    for activity in activity_progress:
        subjects[activity.subject]['activities'].append(activity)

    return render(request, 'module/progress/progress-list.html', {
        'subjects': dict(subjects),
    })


@login_required
def detail_module_progress(request, module_id):
    progress_list = StudentProgress.objects.filter(module_id=module_id, student__profile__role__name__iexact='student')
    module = get_object_or_404(Module, id=module_id)
    activity_name = module.file_name

    for p in progress_list:
        seconds = p.time_spent
        if seconds is not None:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                p.formatted_time_spent = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                p.formatted_time_spent = f"{minutes}m {seconds}s"
            else:
                p.formatted_time_spent = f"{seconds}s"
        else:
            p.formatted_time_spent = "N/A"

    return render(request, 'module/progress/detail-progress.html', {
        'progress_list': progress_list,
        'activity_name': activity_name
    })


@login_required
def detail_module_progress_cm(request, module_id):
    """Classroom-mode (projector) view of lesson progress — no sidebar/topbar."""
    progress_list = StudentProgress.objects.filter(module_id=module_id, student__profile__role__name__iexact='student')
    module = get_object_or_404(Module, id=module_id)
    activity_name = module.file_name
    subject = module.subject

    for p in progress_list:
        seconds = p.time_spent
        if seconds is not None:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                p.formatted_time_spent = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                p.formatted_time_spent = f"{minutes}m {seconds}s"
            else:
                p.formatted_time_spent = f"{seconds}s"
        else:
            p.formatted_time_spent = "N/A"

    return render(request, 'module/progress/detail-progress-cm.html', {
        'progress_list': progress_list,
        'activity_name': activity_name,
        'module': module,
        'subject': subject,
    })


@login_required
def detail_activity_progress(request, activity_id):
    progress_list = StudentProgress.objects.filter(activity_id=activity_id, student__profile__role__name__iexact='student')
    activity = get_object_or_404(Activity, pk=activity_id)
    activity_name = activity.activity_name

    for p in progress_list:
        seconds = p.time_spent
        if seconds is not None:
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                p.formatted_time_spent = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                p.formatted_time_spent = f"{minutes}m {seconds}s"
            else:
                p.formatted_time_spent = f"{seconds}s"
        else:
            p.formatted_time_spent = "N/A"

    return render(request, 'module/progress/detail-activity-progress.html', {
        'progress_list': progress_list,
        'activity_name': activity_name
    })
