
from subject.models import  Subject
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Exists, OuterRef
from activity.models import ActivityType, StudentActivity
from django.shortcuts import render

@login_required
def assessment_list(request):
    from activity.models import Activity

    user = request.user
    activity_types = list(ActivityType.objects.all().order_by('name'))

    teacher_subjects = Subject.objects.filter(
        Q(assign_teacher=user) | Q(collaborators=user)
    ).distinct().order_by('subject_name')

    submitted_subq = StudentActivity.objects.filter(
        activity=OuterRef('pk'), retake_count__gte=1
    )
    activities_qs = (
        Activity.objects.filter(subject__in=teacher_subjects, status=True)
        .select_related('activity_type', 'subject', 'term')
        .annotate(has_submissions=Exists(submitted_subq))
        .order_by('-start_time', '-local_id')
    )

    type_counts = [
        {'type': t, 'count': activities_qs.filter(activity_type_id=t.id).count()}
        for t in activity_types
    ]

    return render(request, 'assessment/assessment-list.html', {
        'activities': activities_qs,
        'activity_types': activity_types,
        'type_counts': type_counts,
        'teacher_subjects': teacher_subjects,
        'total_activities': activities_qs.count(),
    })