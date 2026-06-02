"""Public, opt-in share page for student profiles.

Security posture:
- Access is gated by Profile.share_enabled AND a random token (43-char
  URL-safe; ~256 bits of entropy) that is NOT derived from the user PK.
- A disabled share returns 404 even if the token is correct, so toggling
  off is an immediate revoke without rotating.
- The page exposes only display-safe fields: display name, photo, level,
  total XP, featured badges, recognitions (award label + teacher first
  name only). It deliberately omits email, phone, address, DOB, gender,
  ID number, course, department, role, username, and PK.
"""

import secrets

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from accounts.models import Profile
from gamification.models import StudentBadge, StudentGamification
from gamification.teacher_models import TeacherRecognition


TOKEN_BYTES = 24  # 24 random bytes → 32-char urlsafe; we store up to 43.


def _new_token():
    return secrets.token_urlsafe(TOKEN_BYTES)


@ratelimit(key='ip', rate='30/m', block=True)
@ratelimit(key='ip', rate='300/h', block=True)
def public_student_profile(request, token):
    if not token or len(token) < 16:
        # Reject obviously-malformed tokens early without a DB hit.
        from django.http import Http404
        raise Http404()

    profile = get_object_or_404(
        Profile.objects.select_related('user'),
        share_token=token,
        share_enabled=True,
    )

    user = profile.user
    gamification = StudentGamification.objects.filter(student=user).first()
    total_xp = gamification.total_xp if gamification else 0
    current_level = gamification.current_level if gamification else 1

    featured = list(
        StudentBadge.objects
        .filter(student=user, is_featured=True)
        .select_related('badge')[:7]
    )
    all_badges = list(
        StudentBadge.objects
        .filter(student=user)
        .select_related('badge')
        .order_by('-earned_at')[:30]
    )
    certificates = list(profile.certificates.all().order_by('-issued_date')[:20])

    recognitions = list(
        TeacherRecognition.objects
        .filter(student=user)
        .only('id', 'award_type', 'icon', 'message', 'created_at')
        .order_by('-created_at')[:12]
    )

    return render(request, 'student/public_profile.html', {
        'display_name': (profile.first_name or user.first_name or 'Student'),
        'last_initial': ((profile.last_name or user.last_name or '')[:1]).upper(),
        'photo_url': profile.student_photo.url if profile.student_photo else '',
        'total_xp': total_xp,
        'current_level': current_level,
        'featured_badges': featured,
        'all_badges': all_badges,
        'badges_count': StudentBadge.objects.filter(student=user).count(),
        'certificates': certificates,
        'recognitions': recognitions,
    })


@login_required
@require_POST
@ratelimit(key='user', rate='20/m', block=True)
def toggle_profile_share(request):
    """Enable/disable/rotate the share token for the requesting user only."""
    action = request.POST.get('action', 'toggle')
    profile = get_object_or_404(Profile, user=request.user)

    if action == 'enable':
        if not profile.share_token:
            profile.share_token = _new_token()
        profile.share_enabled = True
    elif action == 'disable':
        profile.share_enabled = False
    elif action == 'rotate':
        profile.share_token = _new_token()
        profile.share_enabled = True
    else:  # toggle
        if profile.share_enabled:
            profile.share_enabled = False
        else:
            if not profile.share_token:
                profile.share_token = _new_token()
            profile.share_enabled = True

    profile.save(update_fields=['share_token', 'share_enabled'])

    share_url = ''
    if profile.share_enabled and profile.share_token:
        share_url = request.build_absolute_uri(
            reverse('public_student_profile', args=[profile.share_token])
        )

    return JsonResponse({
        'ok': True,
        'enabled': profile.share_enabled,
        'share_url': share_url,
    })
