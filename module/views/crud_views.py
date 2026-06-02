from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models.deletion import ProtectedError
from django.db import close_old_connections, transaction
from django.urls import reverse
import os
import threading
from subject.models import Subject
from course.models import Semester, Term
from module.models.module import Module
from module.models.student_progress import StudentProgress
from module.forms import moduleForm, ModuleURLForm, ModuleEmbedForm, UpdateModuleEmbedForm, UpdateModuleURLForm
from module.forms.update_module_form import updatemoduleForm
from django.conf import settings
from django.contrib.auth import get_user_model
from module.services.onedrive import upload_and_embed


def _do_onedrive_upload(module_id, user_id, filename):
    """Perform the OneDrive upload in a background thread.

    Multi-MB PPTX/DOCX uploads to Microsoft Graph can take 10–60+ seconds
    depending on size and network. Running them in the request thread
    blocks the create/update POST for that entire time. We re-fetch the
    module + user inside the thread (passing PKs across threads is safe;
    passing model instances is not — connections can be reused/closed)."""
    try:
        User = get_user_model()
        module = Module.objects.filter(pk=module_id).first()
        user = User.objects.filter(pk=user_id).first()
        if not module or not user or not module.file:
            print(f"[OneDrive] aborting thread: module={module_id} user={user_id} file_present={bool(module and module.file)}")
            return

        try:
            module.file.open("rb")
            print(f"[OneDrive] uploading module={module_id} filename={filename}")
            result = upload_and_embed(user, module.file, filename=filename)
        except Exception as exc:
            print(f"[OneDrive] exception during upload_and_embed: {exc!r}")
            result = None
        finally:
            try:
                module.file.close()
            except Exception:
                pass

        if result:
            module.onedrive_item_id = result["item_id"]
            module.onedrive_embed_url = result["embed_url"]
            module.save(update_fields=["onedrive_item_id", "onedrive_embed_url"])
            print(f"[OneDrive] saved embed_url to module {module_id}: {result['embed_url']}")
        else:
            print(f"[OneDrive] no result — module {module_id} onedrive_embed_url stays empty")
    finally:
        close_old_connections()


def _mirror_to_onedrive(module, user):
    """Queue an OneDrive mirror for an uploaded Office file.

    Returns immediately. The actual upload (which can take tens of
    seconds for large PPTX/DOCX files) runs in a daemon thread after the
    current transaction commits. If the upload fails, the local file
    remains the source of truth — the embed URL just stays empty and
    the lesson preview falls back to the PDF.js viewer for PDFs, or
    plain download for Office files."""
    if not module.file:
        print(f"[OneDrive] _mirror_to_onedrive: no file on module {module.pk} — skipping")
        return
    ext = os.path.splitext(module.file.name)[1].lower()
    preview_exts = getattr(settings, "ONEDRIVE_PREVIEW_EXTS", set())
    if ext not in preview_exts:
        print(f"[OneDrive] _mirror_to_onedrive: ext {ext!r} not in preview list — skipping")
        return

    module_id = module.pk
    user_id = user.id
    filename = os.path.basename(module.file.name)

    def _start_thread():
        threading.Thread(
            target=_do_onedrive_upload,
            args=(module_id, user_id, filename),
            daemon=True,
        ).start()

    # on_commit guarantees the row is visible to the worker thread; if
    # no atomic block is active, it fires immediately.
    transaction.on_commit(_start_thread)
    print(f"[OneDrive] queued background upload for module={module_id} ({filename})")


@login_required
@permission_required('module.delete_module', raise_exception=True)
def delete_material(request, pk):
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject_id

    if request.method == 'POST':
        name = module.file_name
        try:
            module.delete()
            messages.success(request, f'Lesson “{name}” has been deleted.')
        except ProtectedError:
            try:
                refs = module.studentprogress_set.count()
            except Exception as e:
                refs = 0
            msg = (
                f'Cannot delete “{name}” because it is referenced by '
                f'{refs} student progress record{"s" if refs != 1 else ""}. '
                'Remove those records first (or archive the lesson) and try again.'
            )
            messages.error(request, msg)

        # Stay in whichever list the user came from (classroom mode vs normal).
        referer = request.META.get('HTTP_REFERER') or ''
        if 'classroom' in referer or 'material-list-cm' in referer:
            return redirect(reverse('material-list-cm', args=[subject_id]))
        return redirect('material-list', id=subject_id)

    messages.info(request, 'Nothing was deleted.')
    return redirect(reverse('material-list-cm', args=[subject_id]))


# Create a file-based lesson
@login_required
@permission_required('module.add_module', raise_exception=True)
def create_material(request, subject_id):
    """Create a file-based lesson"""
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = moduleForm(request.POST, request.FILES, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()
            _mirror_to_onedrive(module, request.user)

            messages.success(request, 'Lesson created successfully!')
            return redirect('material-list', id=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = moduleForm(current_semester=current_semester, subject=subject)

    return render(request, 'material/create-material.html', {'form': form, 'subject': subject})


@login_required
@permission_required('module.add_module', raise_exception=True)
def create_material_url(request, subject_id):
    """Create a URL-based lesson"""
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = ModuleURLForm(request.POST, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()

            messages.success(request, 'URL lesson created successfully!')
            return redirect('material-list', id=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = ModuleURLForm(current_semester=current_semester, subject=subject)

    return render(request, 'material/create-material-url.html', {'form': form, 'subject': subject})


CONFERENCE_PROVIDERS = {
    'msteams':         ('teams.microsoft.com', 'Microsoft Teams'),
    'googlemeet':      ('meet.google.com',     'Google Meet'),
    'googleclassroom': ('classroom.google.com','Google Classroom'),
    'zoom':            ('zoom.us',             'Zoom'),
    'webex':           ('webex.com',           'Webex'),
    'other':           ('',                    'Other'),
}


@login_required
@permission_required('module.add_module', raise_exception=True)
def create_conference(request, subject_id):
    """Create a video-conferencing lesson — saves the link as a URL-backed Module."""
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method != 'POST':
        return redirect('material-list', id=subject_id)

    provider = (request.POST.get('provider') or '').strip().lower()
    title = (request.POST.get('title') or '').strip()
    url = (request.POST.get('url') or '').strip()
    description = (request.POST.get('description') or '').strip()

    if provider not in CONFERENCE_PROVIDERS:
        messages.error(request, 'Please choose a conferencing provider.')
        return redirect('material-list', id=subject_id)
    if not title:
        messages.error(request, 'Please give the conference a name.')
        return redirect('material-list', id=subject_id)
    if not url:
        messages.error(request, 'Please paste the meeting link.')
        return redirect('material-list', id=subject_id)

    # Light provider-vs-domain check — warn but don't reject if it doesn't match.
    expected_domain, label = CONFERENCE_PROVIDERS[provider]
    if expected_domain and expected_domain not in url.lower():
        messages.warning(
            request,
            f'The link doesn\'t look like a {label} URL — saved anyway.'
        )

    Module.objects.create(
        subject=subject,
        file_name=title,
        url=url,
        description=description or None,
        allow_download=True,
    )
    messages.success(request, f'{label} conference “{title}” added.')
    return redirect('material-list', id=subject_id)


@login_required
@permission_required('module.add_module', raise_exception=True)
def create_material_embed(request, subject_id):
    """Create an embed/iframe-based lesson"""
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = ModuleEmbedForm(request.POST, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()

            messages.success(request, 'Embed lesson created successfully!')
            return redirect('material-list', id=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = ModuleEmbedForm(current_semester=current_semester, subject=subject)

    return render(request, 'material/create-material-embed.html', {'form': form, 'subject': subject})

# Create a file-based lesson CM
@login_required
@permission_required('module.add_module', raise_exception=True)
def create_material_cm(request, subject_id):
    """Create a file-based lesson"""
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = moduleForm(request.POST, request.FILES, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()
            _mirror_to_onedrive(module, request.user)

            messages.success(request, 'Lesson created successfully!')
            return redirect('classroom_mode', pk=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = moduleForm(current_semester=current_semester, subject=subject)

    return render(request, 'material-cm/create-material-cm.html', {'form': form, 'subject': subject})


@login_required
@permission_required('module.add_module', raise_exception=True)
def create_material_url_cm(request, subject_id):
    """Create a URL-based lesson"""
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = ModuleURLForm(request.POST, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()

            messages.success(request, 'URL lesson created successfully!')
            return redirect('classroom_mode', pk=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = ModuleURLForm(current_semester=current_semester, subject=subject)

    return render(request, 'material-cm/create-material-url-cm.html', {'form': form, 'subject': subject})


@login_required
@permission_required('module.add_module', raise_exception=True)
def create_material_embed_cm(request, subject_id):
    """Create an embed/iframe-based lesson"""
    subject = get_object_or_404(Subject, id=subject_id)

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = ModuleEmbedForm(request.POST, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()

            messages.success(request, 'Embed lesson created successfully!')
            return redirect('classroom_mode', pk=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = ModuleEmbedForm(current_semester=current_semester, subject=subject)

    return render(request, 'material-cm/create-material-embed-cm.html', {'form': form, 'subject': subject})


@login_required
@permission_required('module.change_module', raise_exception=True)
def update_material(request, pk):
    """Update a lesson — dispatches by type (URL / embed / file).

    The Edit button on material-list always links here, so we detect what
    kind of lesson this is and pick the matching form + template. Mirrors
    update_material_cm's dispatch.
    """
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject.id
    subject = module.subject

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    is_url = bool(getattr(module, 'url', None))
    is_embed = bool(getattr(module, 'iframe_code', None))

    if is_url:
        form_cls = UpdateModuleURLForm
        template = 'material/update-material-url.html'
        accepts_files = False
    elif is_embed:
        form_cls = UpdateModuleEmbedForm
        template = 'material/update-material-embed.html'
        accepts_files = False
    else:
        form_cls = updatemoduleForm
        template = 'material/update-material.html'
        accepts_files = True

    if request.method == 'POST':
        if accepts_files:
            form = form_cls(request.POST, request.FILES, instance=module, current_semester=current_semester, subject=subject)
        else:
            form = form_cls(request.POST, instance=module, current_semester=current_semester, subject=subject)

        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()
            if accepts_files and 'file' in request.FILES:
                # A new file was uploaded — re-mirror to OneDrive.
                module.onedrive_item_id = None
                module.onedrive_embed_url = None
                _mirror_to_onedrive(module, request.user)

            messages.success(request, 'Lesson updated successfully!')
            return redirect('material-list', id=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = form_cls(instance=module, current_semester=current_semester, subject=subject)

    return render(request, template, {'form': form, 'module': module, 'subject': subject})


@login_required
@permission_required('module.change_module', raise_exception=True)
def update_material_url(request, pk):
    """Update a URL-based lesson"""
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject.id
    subject = module.subject

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = UpdateModuleURLForm(request.POST, instance=module, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()
            
            messages.success(request, 'Lesson updated successfully!')
            return redirect('material-list', id=subject_id)
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = UpdateModuleURLForm(instance=module, current_semester=current_semester, subject=subject)

    return render(request, 'material/update-material-url.html', {'form': form, 'module': module, 'subject': subject})


@login_required
@permission_required('module.change_module', raise_exception=True)
def update_material_embed(request, pk):
    """Update an embed/iframe-based lesson"""
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject.id
    subject = module.subject

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    if request.method == 'POST':
        form = UpdateModuleEmbedForm(request.POST, instance=module, current_semester=current_semester, subject=subject)
        
        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()
            
            messages.success(request, 'Lesson updated successfully!')
            return redirect('material-list', id=subject_id)
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = UpdateModuleEmbedForm(instance=module, current_semester=current_semester, subject=subject)

    return render(request, 'material/update-material-embed.html', {'form': form, 'module': module, 'subject': subject})


@login_required
@permission_required('module.change_module', raise_exception=True)
def update_material_cm(request, pk):
    """Update a lesson in Classroom Mode — dispatches by lesson type (URL / embed / file)."""
    module = get_object_or_404(Module, pk=pk)
    subject_id = module.subject.id
    subject = module.subject

    now = timezone.localtime(timezone.now())
    current_semester = Semester.objects.filter(start_date__lte=now, end_date__gte=now).first()

    is_url = bool(getattr(module, 'url', None))
    is_embed = bool(getattr(module, 'iframe_code', None))

    if is_url:
        form_cls = UpdateModuleURLForm
        template = 'material-cm/update-material-url-cm.html'
        accepts_files = False
    elif is_embed:
        form_cls = UpdateModuleEmbedForm
        template = 'material-cm/update-material-embed-cm.html'
        accepts_files = False
    else:
        form_cls = updatemoduleForm
        template = 'material-cm/update-material-cm.html'
        accepts_files = True

    if request.method == 'POST':
        if accepts_files:
            form = form_cls(request.POST, request.FILES, instance=module, current_semester=current_semester, subject=subject)
        else:
            form = form_cls(request.POST, instance=module, current_semester=current_semester, subject=subject)

        if form.is_valid():
            module = form.save(commit=False)
            module.subject = subject
            module.save()
            form.save_m2m()

            messages.success(request, 'Lesson updated successfully!')
            return redirect('classroom_mode', pk=subject_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        field_label = form.fields.get(field, {}).label or field
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = form_cls(instance=module, current_semester=current_semester, subject=subject)

    return render(request, template, {'form': form, 'module': module, 'subject': subject})



# ─── Click-to-edit endpoint ───────────────────────────────────────────
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from module.models import Module


@login_required
@permission_required('module.change_module', raise_exception=True)
@require_http_methods(["PATCH"])
def rename_module(request, pk):
    module = get_object_or_404(Module, pk=pk)

    # Subject-level ownership check: only the teacher actually assigned to the
    # module's subject (or active substitute) can rename it. The template
    # already hides the edit affordance, but a direct PATCH would otherwise
    # let any user with module.change_module rewrite another teacher's title.
    subject = module.subject
    active_teacher = getattr(subject, "active_teacher", None) if subject is not None else None
    if active_teacher is None or active_teacher.pk != request.user.pk:
        return JsonResponse({'ok': False, 'error': 'Only the assigned teacher can rename this material.'}, status=403)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Malformed request body.'}, status=400)

    new_name = (payload.get('file_name') or '').strip()
    if not new_name:
        return JsonResponse({'ok': False, 'error': 'Material name cannot be empty.'}, status=400)
    if len(new_name) < 2:
        return JsonResponse({'ok': False, 'error': 'Material name must be at least 2 characters.'}, status=400)
    if len(new_name) > 100:
        return JsonResponse({'ok': False, 'error': 'Material name must be at most 100 characters.'}, status=400)

    module.file_name = new_name
    module.save(update_fields=['file_name'])
    return JsonResponse({'ok': True, 'value': new_name})

