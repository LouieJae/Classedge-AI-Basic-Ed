from django.shortcuts import render, get_object_or_404
from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.db.models import Avg
from activity.models import Activity, StudentActivity
from subject.models import Subject
from activity.utils.authorization import check_activity_access
from activity.views.answer_views import _effective_deadline


# Display activity details
@method_decorator(login_required, name='dispatch')
class AssessmentDetailsView(View):

    def get(self, request, activity_id):
        user = request.user
        activity = get_object_or_404(Activity, local_id=activity_id)

        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====
        is_audit = (
            user.is_admin
            or user.is_registrar
            or user.is_dean
            or user.is_program_head
            or user.is_academic_director
        )
        show_staff_view = user.is_teacher or is_audit

        has_gradable_questions = activity.activityquestion_set.filter(
            quiz_type__name__in=['Document', 'Essay']
        ).exists()

        effective_deadline = _effective_deadline(activity)
        activity_ended = timezone.now() > effective_deadline if effective_deadline else False
        in_late_window = bool(
            activity.end_time
            and activity.allow_late_submission
            and (activity.late_submission_days or 0) > 0
            and activity.end_time < timezone.now() <= (effective_deadline or activity.end_time)
        )
        student_activity = StudentActivity.objects.filter(student=user, activity=activity).first()
        student_attempt = student_activity.retake_count if student_activity else 0

        retake_records = []
        canonical_retake_id = None
        if user.is_student and student_activity:
            retake_records = list(
                student_activity.retake_records
                .exclude(status='ongoing')
                .order_by('retake_number')
            )
            # The canonical retake (per the activity's retake_method) is the one
            # the teacher's manual grade is recorded against. Mark it so the
            # template can fall back to student_activity.total_score for legacy
            # rows where the per-attempt score hasn't been backfilled yet.
            method = activity.retake_method
            scored_qs = student_activity.retake_records.exclude(status='ongoing')
            if scored_qs.exists():
                if method == 'highest':
                    canonical = scored_qs.order_by('-score', '-retake_time').first()
                elif method == 'first':
                    canonical = scored_qs.order_by('retake_time').first()
                else:
                    canonical = scored_qs.order_by('-retake_time').first()
                canonical_retake_id = canonical.pk if canonical else None

        # An attempt is "in progress" when the student already opened the
        # activity (start_time stamped) but hasn't finalized a submission
        # (retake_count is still 0). The button label flips to "Resume" so
        # it's clear they're picking up where they left off.
        attempt_in_progress = bool(
            user.is_student
            and student_activity
            and student_activity.start_time
            and (student_activity.retake_count or 0) == 0
        )

        teacher_stats = None
        if show_staff_view and activity.subject_id:
            User = get_user_model()
            enrolled_total = User.objects.filter(
                subjectenrollment__subject_id=activity.subject_id,
                subjectenrollment__status='enrolled',
            ).distinct().count()
            submissions_qs = StudentActivity.objects.filter(
                activity=activity, retake_count__gte=1
            )
            submitted_count = submissions_qs.count()
            graded_count = submissions_qs.filter(total_score__gt=0).count()
            pending_count = max(submitted_count - graded_count, 0)
            avg_score = submissions_qs.aggregate(avg=Avg('total_score'))['avg']
            teacher_stats = {
                'enrolled_total': enrolled_total,
                'submitted_count': submitted_count,
                'not_submitted_count': max(enrolled_total - submitted_count, 0),
                'graded_count': graded_count,
                'pending_count': pending_count,
                'avg_score': avg_score,
            }

        return render(request, 'activity/assessments/assessment-detail.html', {
            'activity': activity,
            'is_teacher': user.is_teacher,
            'is_student': user.is_student,
            'is_student_role': user.is_student,
            'is_time_keeper': user.is_time_keeper,
            'is_audit': is_audit,
            'show_staff_view': show_staff_view,
            'activity_ended': activity_ended,
            'in_late_window': in_late_window,
            'effective_deadline': effective_deadline,
            'now': now(),
            'student_attempt': student_attempt,
            'attempt_in_progress': attempt_in_progress,
            'teacher_stats': teacher_stats,
            'retake_records': retake_records,
            'has_gradable_questions': has_gradable_questions,
            'student_activity': student_activity,
            'canonical_retake_id': canonical_retake_id,
        })


# Display activity details (Classroom Mode)
@method_decorator(login_required, name='dispatch')
class AssessmentDetailViewCM(View):
    def get(self, request, activity_id):
        user = request.user
        activity = get_object_or_404(Activity, local_id=activity_id)
        
        # ===== AUTHORIZATION CHECK =====
        has_access, redirect_response = check_activity_access(request, activity)
        if not has_access:
            return redirect_response
        # ===== END AUTHORIZATION CHECK =====
        
        subject = activity.subject
        subject = subject_id = activity.subject.id
        subject = get_object_or_404(Subject, local_id=subject_id)

        # Check if the user is a teacher or a student
        is_teacher = user.is_authenticated and user.is_teacher
        is_student = user.is_authenticated and user.is_student
        effective_deadline = _effective_deadline(activity)
        activity_ended = timezone.now() > effective_deadline if effective_deadline else False

        student_activity = None
        is_absent = False
        is_present = False

        if is_student:
            student_activity = StudentActivity.objects.filter(student=user, activity=activity).first()
            if student_activity:
                attendance_mode = student_activity.attendance_mode.strip().lower() if student_activity.attendance_mode else None
                if attendance_mode == 'absent':
                    is_absent = True
                elif attendance_mode == 'present':
                    is_present = True

        return render(request, 'activity/assessments/assessment-detail-cm.html', {
            'subject': subject,
            'activity': activity,
            'is_teacher': is_teacher,
            'is_student': is_student,
            'activity_ended': activity_ended,
            'is_absent': is_absent,
            'is_present': is_present,
        })
