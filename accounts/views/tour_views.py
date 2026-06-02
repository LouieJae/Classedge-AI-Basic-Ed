"""Guided-tour completion endpoint.

Persists which Shepherd tours a user has finished or dismissed onto their
Profile (`seen_tours`), so a walkthrough never auto-shows again for that
account — regardless of browser, device, or cleared local storage.
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


@require_POST
@login_required
def mark_tour_seen(request):
    """Record a tour id as seen for the current user. Idempotent."""
    tour_id = (request.POST.get("tour_id") or "").strip()
    if not tour_id or len(tour_id) > 100:
        return JsonResponse({"ok": False, "error": "invalid tour_id"}, status=400)

    profile = getattr(request.user, "profile", None)
    if profile is None:
        return JsonResponse({"ok": False, "error": "no profile"}, status=200)

    seen = profile.seen_tours if isinstance(profile.seen_tours, list) else []
    if tour_id not in seen:
        seen.append(tour_id)
        profile.seen_tours = seen
        profile.save(update_fields=["seen_tours"])

    return JsonResponse({"ok": True, "seen": seen})
