from datetime import date

from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from activity.models.student_activity_model import StudentActivity
from gamification.models import StudentBadge, StudentGamification
from gamification.services import award_xp
from gamification.streaks import update_accuracy_streak, update_login_streak, update_submission_streak
from gamification.teacher_models import TeacherRating


@receiver(post_save, sender=StudentActivity)
def on_student_activity_save(sender, instance, created, **kwargs):
    if not created:
        return

    student = instance.student
    if not student:
        return

    rates = settings.GAMIFICATION_XP_RATES

    # Submission XP
    xp = rates["submission"]
    if instance.term and instance.term.end_date:
        days_early = (instance.term.end_date - date.today()).days
        if days_early > 1:
            xp = rates["early_submission"]

    award_xp(student, xp, "Assignment submitted", "activity", source_id=instance.pk)

    # Submission streak
    is_on_time = True
    if instance.term and instance.term.end_date:
        is_on_time = date.today() <= instance.term.end_date
    update_submission_streak(student, is_on_time)

    # Score-based XP
    activity = instance.activity
    if activity and activity.max_score and activity.max_score > 0:
        score_pct = (instance.total_score / activity.max_score) * 100

        if score_pct >= 90:
            award_xp(student, rates["score_90"], "Score >=90%", "activity_score_90", source_id=instance.pk)
        elif score_pct >= 75:
            award_xp(student, rates["score_75"], "Score >=75%", "activity_score_75", source_id=instance.pk)

        update_accuracy_streak(student, score_pct)


@receiver(user_logged_in)
def on_user_login(sender, request, user, **kwargs):
    from gamification.staff_badges import _is_staff_user, evaluate_staff_badges

    if _is_staff_user(user):
        evaluate_staff_badges(user)
        return

    rates = settings.GAMIFICATION_XP_RATES
    gam, _ = StudentGamification.objects.get_or_create(student=user)

    if gam.last_active_date == date.today():
        return

    award_xp(user, rates["daily_login"], "Daily login", "login", source_id=date.today().toordinal())
    update_login_streak(user)


@receiver(post_save, sender=StudentBadge)
def on_student_badge_earned(sender, instance, created, **kwargs):
    """When a student earns a badge, award 3 IP to their teachers."""
    if not created:
        return

    student = instance.student
    if not student:
        return

    from django.utils import timezone as tz
    from course.models.semester_model import Semester
    from course.models.subject_enrollment_model import SubjectEnrollment
    from subject.models.subject_model import Subject

    now = tz.now()
    semester = Semester.objects.filter(
        start_date__lte=now.date(), end_date__gte=now.date(),
    ).first()
    if not semester:
        return

    enrolled_subject_ids = SubjectEnrollment.objects.filter(
        student=student, semester=semester, status="enrolled",
    ).values_list("subject_id", flat=True)

    teacher_ids = set()
    for subj in Subject.objects.filter(pk__in=enrolled_subject_ids):
        if subj.assign_teacher_id:
            teacher_ids.add(subj.assign_teacher_id)
        if subj.substitute_teacher_id:
            teacher_ids.add(subj.substitute_teacher_id)

    from gamification.teacher_services import award_ip
    from accounts.models import CustomUser
    for teacher_id in teacher_ids:
        teacher = CustomUser.objects.filter(pk=teacher_id).first()
        if teacher:
            award_ip(teacher, 3, "Student earned badge", "student_badge_earned", source_id=instance.pk)


@receiver(post_save, sender=TeacherRating)
def on_teacher_rating_created(sender, instance, created, **kwargs):
    """When a student rates a teacher, award IP based on stars."""
    if not created:
        return

    from gamification.teacher_services import award_ip
    if instance.stars == 5:
        award_ip(instance.teacher, 3, "5-star rating", "star_rating_5", source_id=instance.pk)
    elif instance.stars == 4:
        award_ip(instance.teacher, 1, "4-star rating", "star_rating_4", source_id=instance.pk)


@receiver(post_save, sender="course.Attendance")
def on_attendance_saved(sender, instance, **kwargs):
    """Award 50 XP when a student achieves perfect attendance for the ISO week (Mon–Fri)."""
    from datetime import date, timedelta
    from course.models.attendance_model import Attendance, AttendanceStatus
    from gamification.models import XPTransaction

    student = instance.student
    today = date.today()
    # ISO week: Monday=0 ... Friday=4
    week_monday = today - timedelta(days=today.weekday())
    week_friday = week_monday + timedelta(days=4)
    weekdays = [week_monday + timedelta(days=i) for i in range(5)]

    present_statuses = list(
        AttendanceStatus.objects.filter(status__in=["Present", "Present_Online"])
        .values_list("id", flat=True)
    )
    if not present_statuses:
        return

    present_days = set(
        Attendance.objects.filter(
            student=student,
            date__gte=week_monday,
            date__lte=week_friday,
            status_id__in=present_statuses,
        ).values_list("date", flat=True)
    )

    if not all(d in present_days for d in weekdays):
        return

    # Dedup: don't award twice in the same ISO week
    already = XPTransaction.objects.filter(
        student=student,
        source_type="attendance_week",
        created_at__date__gte=week_monday,
        created_at__date__lte=week_friday,
    ).exists()
    if already:
        return

    xp_amount = getattr(settings, "GAMIFICATION_XP_RATES", {}).get(
        "perfect_attendance_week", 50
    )
    award_xp(
        student=student,
        amount=xp_amount,
        reason="Perfect attendance week",
        source_type="attendance_week",
        source_id=str(today.isocalendar()[1]),
    )
