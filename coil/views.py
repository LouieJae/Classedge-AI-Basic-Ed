from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import CoilPartnerSchoolRegistrationForm, CoilSchoolInviteUpdateForm
from .models import CoilPartnerSchool
from .utils import get_partner_school_by_email
from django.core.mail import send_mail
from django.urls import reverse
import uuid
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import requests
from subject.models import Subject, SDG
from accounts.models import StudentSDG
from course.models import StudentInvite
from django.contrib.auth.decorators import login_required
from accounts.utils.security_utils import custom_ratelimit, log_security_event, check_token_expiry


@login_required
def send_student_invite(request, subject_id):
    """Email a COIL enrollment invite. Internal HCCCI emails skip the
    partner-school check; external emails must come from a verified COIL
    partner school."""
    email = request.POST.get('email')
    subject = get_object_or_404(Subject, id=subject_id)
    is_internal = email.lower().endswith('@hccci.edu.ph')

    if not is_internal and not get_partner_school_by_email(email):
        messages.error(request, "School is not verified for COIL.")
        return redirect('material-list', id=subject_id)

    invite, _ = StudentInvite.objects.get_or_create(
        email=email, subject=subject, defaults={'token': uuid.uuid4()},
    )

    invite_url = request.build_absolute_uri(
        reverse('accept_student_invite', args=[str(invite.token)])
    )
    lms_link = "https://classedge.hccci.edu.ph/"
    message_body = (
        f"Hi,\n\n"
        f"You have been invited to enroll in the LMS subject:\n"
        f"Subject: {subject.subject_name}\n\n"
        f"Please register and accept the invitation by visiting the following link:\n"
        f"{invite_url}\n\n"
        f"After registration, you may access the LMS here:\n"
        f"{lms_link}\n\n"
        f"If you have any questions, please contact your instructor.\n\n"
        f"Best,\nLMS Team"
    )
    send_mail(
        subject=" LMS Enrollment Invitation",
        message=message_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )
    messages.success(request, f"Invite sent to {email}")
    return redirect('material-list', id=subject_id)


@custom_ratelimit(rate='10/h', method='ALL')
def accept_student_invite(request, token):
    """Land an emailed invite recipient on the registration page, after
    sanity-checking the 72-hour token window."""
    invite = get_object_or_404(StudentInvite, token=token, accepted=False)
    if check_token_expiry(invite, expiry_hours=72):
        messages.error(request, "This invitation link has expired. Please contact your instructor.")
        return redirect('admin_login_view')

    log_security_event('STUDENT_INVITE_ACCEPTED', request, f"Token: {token}")
    request.session['student_invite_email'] = invite.email
    request.session['student_invite_token'] = str(invite.token)
    return redirect('register_user')

@login_required
def coil_school_list(request):
    coil_school = CoilPartnerSchool.objects.all()
    return render(request, 'coil/coil_school_list.html', {'coil_school': coil_school})

@login_required
def register_coil_school(request):
    if request.method == 'POST':
        form = CoilPartnerSchoolRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Save school
                school = form.save(commit=False)
                school.status = 'Pending Acceptance'  # set status here
                school.save()

                # Generate invite URL
                invite_url = request.build_absolute_uri(
                    reverse('accept_school_invite', args=[str(school.invite_token)])
                )

                # Email body
                body = f"""
                Hello {school.school_name},

                You've been invited to participate in our COIL Program.
                Please complete your registration here:
                {invite_url}

                Regards,
                COIL Team
                """

                # Send the email
                send_mail(
                    subject="COIL Program Participation Invitation",
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[school.school_email],
                )

                messages.success(request, f"{school.school_name} registered and invite sent to {school.school_email}.")
                return redirect('coil_school_list')
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = CoilPartnerSchoolRegistrationForm()

    return render(request, 'coil/coil_registration.html', {'form': form})

@login_required
def verify_school(request, school_id):
    school = get_object_or_404(CoilPartnerSchool, id=school_id)
    school.status = 'Partner'
    school.save()
    messages.success(request, f"{school.school_name} has been Partner.")
    return redirect('coil_school_list')

@login_required
def reject_school(request, school_id):
    school = get_object_or_404(CoilPartnerSchool, id=school_id)
    school.status = 'Rejected'
    school.save()
    messages.warning(request, f"{school.school_name} has been rejected.")
    return redirect('coil_school_list')


@custom_ratelimit(rate='10/h', method='ALL')
def accept_school_invite(request, token):
    school = get_object_or_404(CoilPartnerSchool, invite_token=token)
    
    # Check if token has expired (72 hours)
    if check_token_expiry(school, expiry_hours=72):
        messages.error(request, "This invitation link has expired.")
        return redirect('thank_you')

    if request.method == 'POST':
        form = CoilSchoolInviteUpdateForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School registration completed.")
            return redirect('thank_you')
        else:
            messages.error(request, "Please fix the errors.")
    else:
        form = CoilSchoolInviteUpdateForm(instance=school)

    return render(request, 'coil/complete_coil_registration.html', {'form': form})



def thank_you(request):
    return render(request, 'coil/thank_you.html')

@login_required
def video_room(request, room_name):
    return render(request, 'coil/conference_room.html', {'room_name': room_name})


@login_required
def ask_question(request):
    if request.method == 'POST':
        try:
            user_question = request.POST.get('question', '').strip()

            if not user_question:
                return JsonResponse({'status': 'error', 'message': 'No question provided.'}, status=400)

            api_key = settings.GOOGLE_API_KEY
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"

            api_data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": user_question
                            }
                        ]
                    }
                ]
            }

            response = requests.post(url, json=api_data, headers={'Content-Type': 'application/json'})
            response_data = response.json()

            if response.status_code == 200:
                candidates = response_data.get('candidates', [])
                if candidates and candidates[0].get('content') and candidates[0]['content'].get('parts'):
                    answer = candidates[0]['content']['parts'][0]['text']
                    return JsonResponse({'status': 'success', 'answer': answer})

            return JsonResponse({'status': 'error', 'message': 'No valid answer returned.'}, status=500)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def ask_question_page(request):
    return render(request, 'coil/ask_ai.html')

@login_required
def sdg(request, id):
    sdg = SDG.objects.get(id=id)
    subjects = Subject.objects.filter(is_coil = True,target_sdgs=sdg)

    try:
        student_SDG = StudentSDG.objects.get(student=request.user, sdg=sdg)
    except StudentSDG.DoesNotExist:
        # If no record exists yet, create one with count=0
        student_SDG = StudentSDG.objects.create(
            student=request.user,
            sdg=sdg,
            count=0
        )

    context = {
        'subjects': subjects,
        'sdg': sdg,
        'student_SDG': student_SDG,
    }
    return render(request, 'coil/sdg.html', context)

@login_required
def sdg_certificate_standalone(request, id):
    """Standalone certificate page without base.html"""
    student_SDG = StudentSDG.objects.get(id=id)
    sdg = student_SDG.sdg
    subjects = Subject.objects.filter(is_coil=True, target_sdgs=sdg)

    context = {
        'subjects': subjects,
        'sdg': sdg,
        'student_SDG': student_SDG,
    }
    return render(request, 'coil/sdg_certificate_standalone.html', context)