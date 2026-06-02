from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
import uuid
from subject.models import Subject, SubjectCollaborator
from coil.utils import get_partner_school_by_email
from accounts.utils.security_utils import custom_ratelimit, log_security_event, check_token_expiry


@login_required
def send_collaboration_invite(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    email = request.POST.get('email')

    if not email:
        messages.error(request, "Email is required.")
        return redirect('material-list', id=subject_id)

    school = get_partner_school_by_email(email)
    if not school:
        messages.info(request, f"No registered COIL partner school found for domain: {email.split('@')[-1]}.")
    
    # Create or reuse existing invite
    invite, created = SubjectCollaborator.objects.get_or_create(
        subject=subject,
        email=email,
        defaults={'token': uuid.uuid4()}
    )

    invite_url = request.build_absolute_uri(
        reverse('accept_collaboration_invite', args=[str(invite.token)])
    )

    email_body = f"""
    Hello,

    You have been invited to collaborate on the subject: {subject.subject_name}.

    Please click the link below to accept the invitation:
    {invite_url}

    If you did not expect this email, you can ignore it.
    """

    send_mail(
        subject='COIL Collaboration Invitation',
        message=email_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )

    messages.success(request, f"Collaboration invite sent to {email}")
    return redirect('material-list', id=subject.id)


@custom_ratelimit(rate='10/h', method='ALL')
def accept_collaboration_invite(request, token):
    invite = get_object_or_404(SubjectCollaborator, token=token, accepted=False)
    
    # Check if token has expired (72 hours)
    if check_token_expiry(invite, expiry_hours=72):
        messages.error(request, "This invitation link has expired. Please contact the subject instructor.")
        return redirect('admin_login_view')
    
    log_security_event('COLLABORATION_INVITE_ACCEPTED', request, f"Token: {token}")
    request.session['invite_email'] = invite.email
    messages.info(request, "Please complete registration to join as a collaborator.")
    return redirect('register_user')