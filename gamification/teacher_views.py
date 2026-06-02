import json

from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.db.models import Q

from course.models.semester_model import Semester
from course.models.subject_enrollment_model import SubjectEnrollment
from gamification.recognition_presets import AWARD_PRESETS, preset_list
from gamification.services import award_xp
from gamification.teacher_models import TeacherRecognition, TeacherRating
from gamification.teacher_services import award_ip


def _teacher_student_ids(teacher):
    """Student IDs currently enrolled in any subject this teacher leads or collaborates on."""
    teacher_subjects = Q(subject__assign_teacher=teacher) | Q(subject__substitute_teacher=teacher) | Q(subject__collaborators=teacher)
    return (
        SubjectEnrollment.objects
        .filter(teacher_subjects, status='enrolled', student__isnull=False)
        .values_list('student_id', flat=True)
        .distinct()
    )


@login_required
@permission_required('gamification.add_teacherrecognition', raise_exception=True)
def recognition_page(request):
    from accounts.models import CustomUser
    student_ids = list(_teacher_student_ids(request.user))
    students = CustomUser.objects.filter(pk__in=student_ids).order_by("first_name", "last_name")
    recent = (
        TeacherRecognition.objects.filter(teacher=request.user)
        .select_related("student")
        .order_by("-created_at")[:20]
    )
    return render(request, "teacher/gamification/recognition_page.html", {
        "students": students,
        "recent": recent,
        "award_presets": preset_list(),
    })


@require_POST
@login_required
@permission_required('gamification.add_teacherrecognition', raise_exception=True)
def send_recognition(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    student_id = data.get("student_id")
    message = data.get("message", "").strip()
    award_type = (data.get("award_type") or "").strip()

    if not student_id or not message:
        return JsonResponse({"ok": False, "error": "Missing student_id or message"}, status=400)

    preset = AWARD_PRESETS.get(award_type)
    if not preset:
        return JsonResponse({"ok": False, "error": "Invalid award type"}, status=400)

    xp_amount = preset["xp"]
    icon = preset["icon"]

    if len(message) > 300:
        return JsonResponse({"ok": False, "error": "Message too long"}, status=400)

    from accounts.models import CustomUser
    student = CustomUser.objects.filter(pk=student_id).first()
    if not student:
        return JsonResponse({"ok": False, "error": "Student not found"}, status=404)

    if student.pk not in set(_teacher_student_ids(request.user)):
        return JsonResponse({"ok": False, "error": "Student is not enrolled in your subjects"}, status=403)

    recognition = TeacherRecognition.objects.create(
        teacher=request.user, student=student,
        message=message, xp_awarded=xp_amount,
        award_type=award_type, icon=icon,
    )

    award_xp(student, xp_amount, "Teacher recognition", "recognition", source_id=recognition.pk)
    award_ip(request.user, 1, "Sent recognition", "recognition_sent", source_id=recognition.pk)

    return JsonResponse({"ok": True})


@require_POST
@login_required
def submit_rating(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    teacher_id = data.get("teacher_id")
    stars = data.get("stars")

    if not teacher_id or not stars or stars not in range(1, 6):
        return JsonResponse({"ok": False, "error": "Invalid teacher_id or stars (1-5)"}, status=400)

    now = timezone.localtime(timezone.now())
    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()
    if not semester:
        return JsonResponse({"ok": False, "error": "No active semester"}, status=400)

    from accounts.models import CustomUser
    teacher = CustomUser.objects.filter(pk=teacher_id).first()
    if not teacher:
        return JsonResponse({"ok": False, "error": "Teacher not found"}, status=404)

    rating, created = TeacherRating.objects.update_or_create(
        teacher=teacher, student=request.user, semester=semester,
        defaults={"stars": stars},
    )

    if created:
        if stars == 5:
            award_ip(teacher, 3, "5-star rating", "star_rating_5", source_id=rating.pk)
        elif stars == 4:
            award_ip(teacher, 1, "4-star rating", "star_rating_4", source_id=rating.pk)

    return JsonResponse({"ok": True})
