import csv
import io
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from .models import StudentActivity, StudentQuestion, Activity, ActivityQuestion, ActivityType
from accounts.models import CustomUser
from subject.models import Subject


@login_required
@require_POST
def import_student_data(request):
    import_file = request.FILES.get('import_file')
    if not import_file:
        messages.error(request, 'No file provided')
        return redirect('import_and_export_activity_page')

    try:
        # Read CSV content
        content = import_file.read().decode('utf-8-sig')
        
        # Quick validation
        rows = list(csv.DictReader(io.StringIO(content)))
        if not rows:
            messages.error(request, 'CSV file is empty or invalid format')
            return redirect('import_and_export_activity_page')
        
        # Queue the import task asynchronously
        from activity.tasks import process_student_data_import
        task = process_student_data_import.delay(content, request.user.id)
        
        messages.success(
            request,
            f"Student activity import started! Processing {len(rows)} rows in the background. "
            f"Task ID: {task.id}. You can continue working while the import completes."
        )
        
        return redirect('import_and_export_activity_page')
    
    except Exception as e:
        messages.error(request, f"Failed to process file: {str(e)}")
        return redirect('import_and_export_activity_page')


# Original synchronous version (kept for reference/fallback)
@login_required
@require_POST
def import_student_data_sync(request):
    import_file = request.FILES.get('import_file')
    if not import_file:
        messages.error(request, 'No file provided')
        return redirect('import_and_export_activity_page')

    try:
        # Read CSV content once
        content = import_file.read().decode('utf-8-sig')
        rows = list(csv.DictReader(io.StringIO(content)))

        if not rows:
            messages.error(request, 'CSV file is empty or invalid format')
            return redirect('import_and_export_activity_page')

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
        imported_count, updated_count, errors = process_batch(
            rows, existing_users, existing_subjects,
            existing_activities, existing_questions
        )

        # --- Feedback ---
        if errors:
            for e in errors[:10]:
                messages.error(request, e)
            if len(errors) > 10:
                messages.error(request, f"... and {len(errors)-10} more errors")

        if imported_count or updated_count:
            messages.success(
                request,
                f"Successfully imported {imported_count} student records and updated {updated_count} records."
            )
        else:
            messages.warning(request, "No student records were imported.")

        return redirect('import_and_export_activity_page')

    except Exception as e:
        messages.error(request, f"Failed to process file: {str(e)}")
        return redirect('import_and_export_activity_page')


def process_batch(rows, existing_users, existing_subjects, existing_activities, existing_questions):
    from datetime import datetime
    imported_count = 0
    updated_count = 0
    errors = []

    # To bulk insert/update later
    new_activities = []
    new_activity_questions = []
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
