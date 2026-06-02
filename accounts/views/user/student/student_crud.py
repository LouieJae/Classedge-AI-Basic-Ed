from gamification.models import StudentBadge, StudentGamification, BadgeDefinition
from gamification.teacher_models import TeacherRecognition
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, get_object_or_404, redirect
from accounts.models import Profile
from subject.models import SDG


STAFF_ROLE_NAMES = {
    "admin", "it admin",
    "registrar", "coil admin",
    "academic director", "program head",
    "time keeper", "dean", "parent",
}


# Account Profile (dispatch) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@login_required
@permission_required('accounts.view_profile', raise_exception=True)
def student_profile(request, pk):
    """[Classedge LMS] Entry point for /account/profile/<pk>/ — routes the
    request to the right per-role template.

    Despite the legacy function name, every signed-in user lands here when
    they click their sidebar avatar. We dispatch:
      - student → student gamification profile
      - teacher → teacher profile (same gamification template, teacher-themed)
      - everyone else → slim staff profile (no XP / badges / streak)
    """

    # Students may only view their own profile via this route. Anyone else who
    # tampers with the URL gets bounced to their own profile.
    if pk != request.user.id:
        return redirect('account_profile', pk=request.user.id)

    profile = get_object_or_404(
        Profile.objects.select_related(
            'user', 'role', 'course', 'department_fields'
        ).prefetch_related('certificates'),
        user__id=pk
    )

    role_name = (profile.role.name.lower() if profile.role and profile.role.name else "").strip()

    # Staff / admin roles get a dedicated profile — no gamification context.
    if role_name in STAFF_ROLE_NAMES:
        return _render_staff_profile(request, profile)

    # Teachers keep the existing teacher template (gamification-aware).
    if role_name == "teacher":
        return _render_teacher_profile(request, profile)

    # Default: student profile.
    return _render_student_profile(request, profile)


def _gamification_context(profile):
    """Shared context builder for student/teacher templates (gamification)."""
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

    recognitions = (
        TeacherRecognition.objects
        .filter(student=profile.user)
        .select_related('teacher')
        .order_by('-created_at')[:12]
    )

    return {
        'earned_badges': earned_list,
        'earned_count': len(earned_list),
        'featured_badges': featured_badges,
        'other_badges': other_badges,
        'upcoming_badges': upcoming_badges,
        'gamification': gamification,
        'current_level': current_level,
        'xp_into_level': xp_into_level,
        'xp_for_next_level': xp_span,
        'xp_progress_pct': xp_progress_pct,
        'recognitions': recognitions,
        'recognitions_count': TeacherRecognition.objects.filter(student=profile.user).count(),
    }


def _render_student_profile(request, profile):
    context = {
        'profile': profile,
        'certificates': profile.certificates.all(),
        'sdg': SDG.objects.all(),
        'is_own_profile': profile.user_id == request.user.id,
    }
    context.update(_gamification_context(profile))
    return render(request, 'student/student_profile.html', context)


def _render_teacher_profile(request, profile):
    context = {
        'profile': profile,
        'certificates': profile.certificates.all(),
        'sdg': SDG.objects.all(),
        'is_own_profile': profile.user_id == request.user.id,
    }
    context.update(_gamification_context(profile))
    return render(request, 'teacher/teacher_profile.html', context)


def _render_staff_profile(request, profile):
    """Slim profile for non-teaching staff (admin, registrar, dean, time keeper, etc.)
    — no XP, no badges. Just identity, contact, and account info."""
    context = {
        'profile': profile,
        'certificates': profile.certificates.all(),
        'is_own_profile': profile.user_id == request.user.id,
    }
    return render(request, 'operations/staff_profile.html', context)
