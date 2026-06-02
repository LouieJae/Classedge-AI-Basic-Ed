from celery import shared_task
from django.conf import settings
from django.core.mail import send_mass_mail
from django.db import transaction
from django.db.models import Q
from datetime import datetime
import csv
import io


@shared_task(bind=True, max_retries=3)
def send_activity_emails(self, student_ids, activity_id):
    """
    Send activity assignment emails to students asynchronously.
    
    Args:
        student_ids: List of student user IDs
        activity_id: Activity ID
    """
    
    try:
        from activity.models import Activity
        from accounts.models import CustomUser
        
        activity = Activity.objects.select_related('subject', 'subject__assign_teacher').get(pk=activity_id)
        students = CustomUser.objects.filter(id__in=student_ids)
        
        subject = f"New Activity Assigned: {activity.activity_name}"
        host_email = settings.EMAIL_HOST_USER
        base_url = settings.BASE_URL
        from_email = host_email
        teacher_name = activity.subject.assign_teacher.get_full_name() if activity.subject.assign_teacher else 'Your Teacher'
        
        email_messages = []
        
        for student in students:
            plain_message = f"""Dear {student.get_full_name()},

A new activity has been assigned to you in the subject {activity.subject.subject_name}.

Activity Name: {activity.activity_name}
Start Time: {activity.start_time.strftime('%Y-%m-%d %H:%M')}
End Time: {activity.end_time.strftime('%Y-%m-%d %H:%M')}

Please log in to your account to complete the activity. Don't miss the deadline!

You can view the activity here: {base_url}

Best regards,
{teacher_name}"""
            
            email_messages.append((subject, plain_message, from_email, [student.email]))
        
        send_mass_mail(email_messages, fail_silently=False)
        
        return {
            "status": "success",
            "emails_sent": len(email_messages)
        }
    
    except Exception as exc:
        if self.request.retries < 3:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def process_student_data_import(self, csv_content, user_id):
    """
    Process student activity data import asynchronously.
    
    Args:
        csv_content: CSV file content as string
        user_id: ID of the user who initiated the import
    """
    
    try:
        from activity.models import StudentActivity, StudentQuestion, Activity, ActivityQuestion, ActivityType
        from accounts.models import CustomUser
        from subject.models import Subject
        
        rows = list(csv.DictReader(io.StringIO(csv_content)))
        
        if not rows:
            return {
                "status": "error",
                "message": "CSV file is empty or invalid format"
            }

        
        # --- Collect identifiers ---
        all_emails = {row.get('student_email', '').strip() for row in rows}
        all_subjects = {row.get('subject_name', '').strip() for row in rows}
        all_activities = {
            (row.get('activity_name', '').strip(), row.get('subject_name', '').strip())
            for row in rows
        }
        all_questions = {
            (row.get('question_text', '').strip(), row.get('activity_name', '').strip())
            for row in rows if row.get('question_text', '').strip()
        }
        
        # --- Fetch existing ---
        existing_users = {u.email: u for u in CustomUser.objects.filter(email__in=all_emails)}
        existing_subjects = {s.subject_name: s for s in Subject.objects.filter(subject_name__in=all_subjects)}
        
        activity_filters = Q()
        for act, subj in all_activities:
            activity_filters |= Q(activity_name=act, subject__subject_name=subj)
        existing_activities = {
            (a.activity_name, a.subject.subject_name): a
            for a in Activity.objects.filter(activity_filters).select_related('subject')
        }
        
        question_filters = Q()
        for q, act in all_questions:
            question_filters |= Q(question_text=q, activity__activity_name=act)
        existing_questions = {
            (q.question_text, q.activity.activity_name): q
            for q in ActivityQuestion.objects.filter(question_filters).select_related('activity')
        }
        
        # --- Create missing subjects/users ---
        new_subjects = [Subject(subject_name=s, subject_code=s[:10].upper())
                        for s in all_subjects if s and s not in existing_subjects]
        if new_subjects:
            Subject.objects.bulk_create(new_subjects, ignore_conflicts=True)
            existing_subjects.update({
                s.subject_name: s for s in Subject.objects.filter(subject_name__in=all_subjects)
            })
        
        new_users = [CustomUser(email=e, username=e)
                     for e in all_emails if e and e not in existing_users]
        if new_users:
            CustomUser.objects.bulk_create(new_users, ignore_conflicts=True)
            existing_users.update({
                u.email: u for u in CustomUser.objects.filter(email__in=all_emails)
            })
        
        # --- Process rows in one big batch ---
        imported_count, updated_count, errors = _process_batch(
            rows, existing_users, existing_subjects,
            existing_activities, existing_questions
        )
        
        
        return {
            "status": "success",
            "imported": imported_count,
            "updated": updated_count,
            "errors": errors[:50]  # Return first 50 errors
        }
    
    except Exception as exc:
        if self.request.retries < 3:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


def _process_batch(rows, existing_users, existing_subjects, existing_activities, existing_questions):
    """Helper function to process batch of rows"""
    from activity.models import StudentActivity, StudentQuestion, Activity, ActivityQuestion, ActivityType
    
    imported_count = 0
    updated_count = 0
    errors = []
    
    # To bulk insert/update later
    new_student_activities = []
    update_student_activities = []
    new_student_questions = []
    update_student_questions = []
    
    # Cache lookups for existing StudentActivity and StudentQuestion
    sa_keys = set()
    sq_keys = set()
    
    # Preload existing activities/questions by composite keys
    for sa in StudentActivity.objects.select_related("student", "activity"):
        sa_keys.add((sa.student_id, sa.activity_id))
    for sq in StudentQuestion.objects.select_related("student", "activity_question"):
        sq_keys.add((sq.student_id, sq.activity_question_id))
    
    def parse_datetime(dt_str):
        if not dt_str:
            return None
        try:
            return datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    
    for row_num, row in enumerate(rows, start=2):
        try:
            student_email = row.get("student_email", "").strip()
            student_name = row.get("student_name", "").strip()
            subject_name = row.get("subject_name", "").strip()
            activity_name = row.get("activity_name", "").strip()
            activity_type = row.get("activity_type", "").strip()
            
            if not all([student_email, subject_name, activity_name]):
                errors.append(f"Row {row_num}: Missing required fields")
                continue
            
            student = existing_users.get(student_email)
            if not student:
                errors.append(f"Row {row_num}: Student not found")
                continue
            
            # Update name in-memory only (not saving row by row)
            if student_name:
                parts = student_name.split(" ", 1)
                student.first_name = parts[0]
                student.last_name = parts[1] if len(parts) > 1 else ""
            
            subject = existing_subjects.get(subject_name)
            if not subject:
                errors.append(f"Row {row_num}: Subject not found")
                continue
            
            # --- Activity ---
            activity_key = (activity_name, subject_name)
            activity = existing_activities.get(activity_key)
            if not activity:
                atype_obj = None
                if activity_type:
                    atype_obj, _ = ActivityType.objects.get_or_create(name=activity_type)
                activity = Activity(
                    activity_name=activity_name,
                    subject=subject,
                    max_score=float(row.get("max_score") or 100),
                    activity_type=atype_obj
                )
                activity.save()
                existing_activities[activity_key] = activity
            
            # --- StudentActivity ---
            sa_data = dict(
                total_score=float(row.get("total_score") or 0),
                retake_count=int(row.get("retake_count") or 0),
                attendance_mode=row.get("attendance_mode") or None,
                start_time=parse_datetime(row.get("start_time")),
                end_time=parse_datetime(row.get("end_time")),
            )
            sa_key = (student.id, activity.id)
            if sa_key in sa_keys:
                sa = StudentActivity.objects.get(student=student, activity=activity)
                for k, v in sa_data.items():
                    setattr(sa, k, v)
                update_student_activities.append(sa)
                updated_count += 1
            else:
                new_student_activities.append(StudentActivity(student=student, activity=activity, **sa_data))
                imported_count += 1
                sa_keys.add(sa_key)
            
            # --- Questions ---
            q_text = row.get("question_text", "").strip()
            if q_text:
                q_key = (q_text, activity_name)
                activity_question = existing_questions.get(q_key)
                if not activity_question:
                    activity_question = ActivityQuestion(
                        activity=activity,
                        question_text=q_text,
                        score=float(row.get("max_question_score") or 1),
                    )
                    activity_question.save()
                    existing_questions[q_key] = activity_question
                
                sq_key = (student.id, activity_question.id)
                sq_data = dict(
                    student_answer=row.get("student_answer", "").strip(),
                    score=float(row.get("question_score") or 0),
                    submission_time=parse_datetime(row.get("submission_time")),
                    status=(row.get("status", "").lower() == "completed"),
                    is_participation=(row.get("is_participation", "").lower() in ["true", "1", "yes"]),
                )
                if sq_key in sq_keys:
                    sq = StudentQuestion.objects.get(student=student, activity_question=activity_question)
                    for k, v in sq_data.items():
                        setattr(sq, k, v)
                    update_student_questions.append(sq)
                else:
                    new_student_questions.append(StudentQuestion(
                        student=student, activity_question=activity_question, activity=activity, **sq_data
                    ))
                    sq_keys.add(sq_key)
        
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    # --- Bulk ops ---
    if new_student_activities:
        StudentActivity.objects.bulk_create(new_student_activities, batch_size=1000)
    if update_student_activities:
        StudentActivity.objects.bulk_update(update_student_activities,
            ["total_score", "retake_count", "attendance_mode", "start_time", "end_time"],
            batch_size=1000,
        )
    
    if new_student_questions:
        StudentQuestion.objects.bulk_create(new_student_questions, batch_size=1000)
    if update_student_questions:
        StudentQuestion.objects.bulk_update(update_student_questions,
            ["student_answer", "score", "submission_time", "status", "is_participation"],
            batch_size=1000,
        )
    
    return imported_count, updated_count, errors


@shared_task(bind=True, max_retries=3)
def export_student_data_csv_async(self, subject_id=None, activity_id=None):
    """
    Export student activity data asynchronously.
    Note: This returns CSV content as string. For large exports, consider using file storage.
    
    Args:
        subject_id: Optional subject ID filter
        activity_id: Optional activity ID filter
    """
    try:
        from activity.models import StudentActivity, StudentQuestion, ActivityQuestion
        from django.db.models import Prefetch
        
        # Build optimized queryset
        student_activities = StudentActivity.objects.select_related(
            'student', 'activity', 'activity__subject', 'activity__activity_type'
        ).prefetch_related(
            Prefetch(
                'activity__activityquestion_set',
                queryset=ActivityQuestion.objects.all(),
                to_attr='cached_questions'
            )
        )
        
        if subject_id:
            student_activities = student_activities.filter(activity__subject_id=subject_id)
        if activity_id:
            student_activities = student_activities.filter(activity_id=activity_id)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        headers = [
            'student_email', 'student_name', 'subject_name', 'activity_name', 'activity_type',
            'total_score', 'max_score', 'percentage_score', 'retake_count', 'start_time',
            'end_time', 'attendance_mode', 'is_editable', 'question_order', 'question_text',
            'student_answer', 'question_score', 'max_question_score', 'submission_time',
            'status', 'is_participation'
        ]
        writer.writerow(headers)
        
        rows_exported = 0
        
        # Process in batches
        for student_activity in student_activities.iterator(chunk_size=1000):
            student_name = f"{student_activity.student.first_name} {student_activity.student.last_name}".strip()
            subject_name = student_activity.activity.subject.subject_name
            activity_name = student_activity.activity.activity_name
            activity_type = student_activity.activity.activity_type.name if student_activity.activity.activity_type else ''
            max_score = student_activity.activity.max_score or 100
            percentage_score = round((student_activity.total_score / max_score) * 100, 2) if max_score else 0
            
            start_time = student_activity.start_time.strftime('%Y-%m-%d %H:%M:%S') if student_activity.start_time else ''
            end_time = student_activity.end_time.strftime('%Y-%m-%d %H:%M:%S') if student_activity.end_time else ''
            attendance_mode = student_activity.attendance_mode or ''
            
            # Get questions
            questions = StudentQuestion.objects.filter(
                student=student_activity.student,
                activity=student_activity.activity
            ).select_related('activity_question')
            
            if not questions.exists():
                writer.writerow([
                    student_activity.student.email, student_name, subject_name, activity_name, activity_type,
                    student_activity.total_score, max_score, percentage_score, student_activity.retake_count,
                    start_time, end_time, attendance_mode, student_activity.is_editable,
                    '', '', '', '', '', '', '', ''
                ])
                rows_exported += 1
            else:
                for question_order, student_question in enumerate(questions, 1):
                    question_text = student_question.activity_question.question_text if student_question.activity_question else ''
                    max_question_score = student_question.activity_question.score if student_question.activity_question else 0
                    submission_time = student_question.submission_time.strftime('%Y-%m-%d %H:%M:%S') if student_question.submission_time else ''
                    
                    writer.writerow([
                        student_activity.student.email, student_name, subject_name, activity_name, activity_type,
                        student_activity.total_score, max_score, percentage_score, student_activity.retake_count,
                        start_time, end_time, attendance_mode, student_activity.is_editable,
                        question_order, question_text, student_question.student_answer or '',
                        student_question.score, max_question_score, submission_time,
                        'Completed' if student_question.status else 'Pending', student_question.is_participation
                    ])
                    rows_exported += 1
        
        csv_content = output.getvalue()
        output.close()
        
        return {
            "status": "success",
            "rows_exported": rows_exported,
            "csv_content": csv_content
        }
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@shared_task(bind=True, max_retries=2)
def finalize_expired_attempts(self):
    """[Classedge LMS] Auto-submit student activity attempts whose timer/late
    window has elapsed without a manual submit.

    Picks up any in-progress StudentActivity (started but retake_count == 0)
    where:
      * the per-attempt timer (sa.end_time) has expired, AND
      * the activity's effective deadline (end_time + grace days when
        ``allow_late_submission`` is on) is also in the past.

    If late submission is allowed and we're still inside the grace window,
    the attempt is left alone so the student can come back and submit.
    """
    from django.utils import timezone
    from datetime import timedelta
    from activity.models import StudentActivity, Activity
    from activity.views.answer_views import _grade_existing_attempt

    now = timezone.now()
    finalized = 0
    candidates = (
        StudentActivity.objects
        .filter(retake_count=0, start_time__isnull=False, end_time__lte=now)
        .select_related('activity')
    )
    for sa in candidates.iterator():
        activity = sa.activity
        if not activity:
            continue
        # Respect the teacher's late-submission grace window: if the activity
        # still accepts late work, don't auto-finalize until that window also
        # closes. Per-attempt timer alone shouldn't lock them out.
        late_window_end = activity.end_time
        if (activity.end_time and activity.allow_late_submission
                and (activity.late_submission_days or 0) > 0):
            late_window_end = activity.end_time + timedelta(days=activity.late_submission_days)
        if late_window_end and now < late_window_end:
            continue
        try:
            _grade_existing_attempt(sa)
            finalized += 1
        except Exception:
            # Don't let a single bad row poison the whole batch.
            continue
    return {'finalized': finalized}
