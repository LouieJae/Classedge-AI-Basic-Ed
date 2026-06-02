def send_activity_assignment_emails(students, activity):
    """Send activity assignment emails to students using Celery"""
    from activity.tasks import send_activity_emails
    
    # Extract student IDs for Celery task
    student_ids = [student.id for student in students]
    
    # Queue the email task asynchronously
    task = send_activity_emails.delay(student_ids, activity.id)
        
    return task.id


# Original synchronous version (kept for reference/fallback)
def send_activity_assignment_emails_sync(students, activity):
    """Send activity assignment emails to students synchronously"""
    from django.conf import settings
    from django.core.mail import send_mass_mail
    
    subject = f"New Activity Assigned: {activity.activity_name}"
    host_email = settings.EMAIL_HOST_USER
    url = settings.BASE_URL
    from_email = host_email
    
    base_url = url 
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

    try:
        send_mass_mail(email_messages, fail_silently=False)
    except Exception:
        pass
