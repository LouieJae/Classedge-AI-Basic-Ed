
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from PIL import Image, ImageDraw, ImageFont
from django.utils.text import slugify
import os, uuid
from django.conf import settings
from django.shortcuts import render,redirect
from accounts.models import Certificate
from django.core.files import File  
from django.contrib import messages
from django.utils.translation import gettext as _
from accounts.forms import BulkCertificateForm
from subject.models import Subject

@login_required
def generate_certificate_from_uploaded_template(name, template_path):
    image = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
    font = ImageFont.truetype(font_path, size=72)

    bbox = font.getbbox(name)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    image_width, image_height = image.size

    x_position = (image_width - text_width) // 2
    y_position = (image_height - text_height) // 2 - 80 

    draw.text((x_position, y_position), name, font=font, fill="black")

    output_dir = os.path.join(settings.MEDIA_ROOT, 'certificates', 'generated')
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}_{slugify(name)}.png"
    output_path = os.path.join(output_dir, filename)
    image.save(output_path)

    return output_path


@login_required
def send_certificate_email(name, email, file_path):
    subject = "🎓 Your Certificate of Participation"
    message = (
        f"Dear {name},\n\n"
        f"Congratulations! Attached is your certificate for successfully participating in our event.\n\n"
        f"Best regards,\n"
        f"LMS Team"
    )

    email_msg = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    email_msg.attach_file(file_path, mimetype='image/png')
    email_msg.send()


@login_required
def send_and_save_certificate(request):
    if request.method == 'POST':
        form = BulkCertificateForm(request.POST, request.FILES)
        subject_id = request.POST.get('subject')
        subject = get_object_or_404(Subject, id=subject_id)

        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.save()

            students = CustomUser.objects.filter(
                subjectenrollment__subject=subject,
                profile__role__name__iexact='student',
                subjectenrollment__status='enrolled'
            ).distinct()

            template_path = certificate.file.path 

            for student in students:
                if hasattr(student, 'profile'):
                    name = f"{student.first_name} {student.last_name}"
                    cert_path = generate_certificate_from_uploaded_template(name, template_path)

                    send_certificate_email(name, student.email, cert_path)

                    with open(cert_path, 'rb') as f:
                        cert_obj = Certificate.objects.create(
                            title=certificate.title,
                            file=File(f, name=os.path.basename(cert_path)),
                            is_featured=certificate.is_featured,
                        )
                        cert_obj.profiles.add(student.profile)


            certificate.save()
            messages.success(request, "Certificates generated, saved, and sent to enrolled students.")
            return redirect('certificate-list')
    else:
        form = BulkCertificateForm()

    subjects = Subject.objects.all()
    return render(request, 'accounts/certificate/send_certificate_bulk.html', {'form': form, 'subjects': subjects})
