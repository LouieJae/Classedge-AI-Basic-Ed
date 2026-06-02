from gamification.models import StudentBadge, StudentGamification, BadgeDefinition
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, get_object_or_404
from accounts.models import Profile
from subject.models import SDG

# Teacher Profile ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@login_required 
@permission_required('accounts.view_profile', raise_exception=True)
def teacher_profile(request, pk):
    
    profile = get_object_or_404(
        Profile.objects.select_related(
            'user', 'role', 'course', 'department_fields'
        ).prefetch_related('certificates'),
        user__id=pk
    )

    certificates = profile.certificates.all()
    sdg = SDG.objects.all()

    earned_list = list(
        StudentBadge.objects
        .filter(student=profile.user)
        .select_related('badge')
        .order_by('-is_featured', '-earned_at')
    )

    earned_badge_ids = {sb.badge_id for sb in earned_list}

    upcoming_badges = (
        BadgeDefinition.objects
        .filter(is_active=True, target_role='student')
        .exclude(id__in=earned_badge_ids)
        .exclude(tier='hidden')
        .order_by('tier', 'name')[:6]
    )

    try:
        gamification = profile.user.gamification
    except StudentGamification.DoesNotExist:
        gamification = None

    featured_badges = [b for b in earned_list if b.is_featured]
    other_badges = [b for b in earned_list if not b.is_featured]

    current_level = gamification.current_level if gamification else 1
    total_xp = gamification.total_xp if gamification else 0

    current_level_floor = (current_level ** 2) * 100
    next_level_floor = ((current_level + 1) ** 2) * 100

    xp_into_level = max(0, total_xp - current_level_floor)
    xp_span = max(1, next_level_floor - current_level_floor)
    xp_progress_pct = min(100, int((xp_into_level / xp_span) * 100))

    context = {
        'profile': profile,
        'certificates': certificates,
        'sdg': sdg,

        # gamification
        'earned_badges': earned_list,
        'earned_count': len(earned_list),
        'featured_badges': featured_badges,
        'other_badges': other_badges,
        'upcoming_badges': upcoming_badges,
        'gamification': gamification,

        # XP system
        'is_own_profile': profile.user_id == request.user.id,
        'current_level': current_level,
        'xp_into_level': xp_into_level,
        'xp_for_next_level': xp_span,
        'xp_progress_pct': xp_progress_pct,
    }

    return render(request, 'teacher/teacher_profile.html', context)
