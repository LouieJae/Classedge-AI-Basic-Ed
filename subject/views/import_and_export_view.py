import csv
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import models
from accounts.models import CustomUser
from subject.models import Subject, Schedule
from subject.utils import parse_days, TYPE_ALIASES, VALID_TYPES
from django.db.models.functions import Concat
from django.db.models import Value as V

# def find_teacher(teacher_name: str):
def find_teacher(teacher_name: str):
    """
    Robust, whitespace-insensitive, case-insensitive teacher lookup.
    Works when first_name contains tabs/newlines (e.g., 'CHRISTINE\\tVILLARET').
    """
    # Collapse any whitespace in the input (spaces/tabs/newlines -> single spaces)
    normalized = " ".join(str(teacher_name or "").split())
    if not normalized:
        return None

    tokens = normalized.split()  # e.g. ['CHRISTINE','VILLARET','PARCON']

    # Build "full_name" as first_name + ' ' + last_name
    qs = CustomUser.objects.annotate(
        full_name=Concat('first_name', V(' '), 'last_name')
    )

    # Require that every token appears somewhere in the concatenated full name
    for tok in tokens:
        qs = qs.filter(full_name__icontains=tok)

    result = qs.first()
    return result


@login_required
@permission_required('subject.add_subject', raise_exception=True)
def import_subjects_and_schedules(request):
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            messages.error(request, "No file selected. Please upload a CSV file.")
            return redirect('import_and_export_subject_page')

        try:
            content = import_file.read().decode('utf-8-sig')
            reader = csv.DictReader(content.splitlines())
            
            row_success, row_partial, row_skipped = 0, 0, 0

            # Cache teacher lookup results to reduce repeated DB queries
            teacher_cache = {}

            for row_num, row in enumerate(reader, start=2):
                
                try:
                    subject_required_fields = [
                        'Subject Name', 'Room Number', 'Teacher Name'
                    ]
                    missing_subject = []
                    for field in subject_required_fields:
                        value = str(row.get(field, '')).strip()
                        if not value:
                            missing_subject.append(field)
                    if missing_subject:
                        messages.error(request, f"Row {row_num}: missing subject data {', '.join(missing_subject)}. Skipped.")
                        row_skipped += 1
                        continue

                    subject_name = row['Subject Name'].strip()
                    subject_code = row['Subject Code'].strip()
                    subject_short_name = (row.get('Subject Short Name') or '').strip()
                    room_number = str(row['Room Number']).strip()
                    subject_description = (row.get('Subject Description') or '').strip()
                    teacher_name = row['Teacher Name'].strip()

                    schedule_fields = ['Day', 'Start Time', 'AM/PM', 'End Time']
                    schedule_data = {f: str(row.get(f, '')).strip() for f in schedule_fields}
                    has_schedule = all(schedule_data.values())

                    # ✅ use the robust, top-level find_teacher
                    normalized_teacher_name = " ".join(str(teacher_name or "").split())
                    if normalized_teacher_name in teacher_cache:
                        teacher = teacher_cache[normalized_teacher_name]
                    else:
                        teacher = find_teacher(teacher_name)
                        teacher_cache[normalized_teacher_name] = teacher
                    if not teacher:
                        messages.error(request, f"Row {row_num}: Teacher '{teacher_name}' not found. Skipped.")
                        row_skipped += 1
                        continue
                        
                    subject, created = Subject.objects.update_or_create(
                        subject_code=subject_code,
                        defaults={
                            'subject_name': subject_name,
                            'subject_short_name': subject_short_name or None,
                            'subject_description': subject_description or None,
                            'room_number': room_number,
                            'assign_teacher': teacher,
                        }
                    )

                    if not has_schedule:
                        row_partial += 1
                        continue

                    schedule_type_raw = (row.get('Schedule Type') or '').strip()
                    stype_norm = schedule_type_raw.title() if schedule_type_raw else None
                    stype_norm = TYPE_ALIASES.get(stype_norm, stype_norm)
                    validated_type = stype_norm if stype_norm in VALID_TYPES else None

                    days = parse_days(row['Day'])
                    if not days:
                        messages.error(request, f"Row {row_num}: invalid Day '{row['Day']}'. Skipped.")
                        row_skipped += 1
                        continue

                    start_ampm = (row.get('AM/PM') or '').strip()
                    end_ampm = ((row.get('End AM/PM') or row.get('AM/PM-1') or row.get('AM/PM')) or '').strip()
                    start_time_str = f"{row['Start Time'].strip()} {start_ampm}"
                    end_time_str = f"{row['End Time'].strip()} {end_ampm}"
                    
                    try:
                        start_time = datetime.strptime(start_time_str, '%I:%M %p').time()
                        end_time = datetime.strptime(end_time_str, '%I:%M %p').time()
                        if start_time >= end_time:
                            messages.error(request, f"Row {row_num}: Start must be earlier than End. Skipped.")
                            row_skipped += 1
                            continue
                    except ValueError as e:
                        messages.error(request, f"Row {row_num}: invalid time format. Skipped.")
                        row_skipped += 1
                        continue

                    sched, created = Schedule.objects.get_or_create(
                        subject=subject,
                        schedule_start_time=start_time,
                        schedule_end_time=end_time,
                        defaults={'days_of_week': days, 'schedule_type': validated_type}
                    )
                    if not created:
                        merged = list({*sched.days_of_week, *days})
                        sched.days_of_week = merged
                        if validated_type:
                            sched.schedule_type = validated_type
                        sched.save()
                    else:
                        pass

                    row_success += 1

                except Exception as e:
                    messages.error(request, f"Row {row_num}: {e}. Skipped.")
                    row_skipped += 1

            messages.success(
                request,
                f"Import finished: {row_success} with schedule, {row_partial} subjects only, {row_skipped} skipped."
            )
        except UnicodeDecodeError as e:
            messages.error(request, "Invalid file encoding. Please use UTF-8 encoded CSV file.")
        except csv.Error as e:
            messages.error(request, f"CSV format error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error while importing file: {str(e)}")
        return redirect('import_and_export_subject_page')

    return render(request, 'subject/import_subject.html')


@login_required
@permission_required('subject.view_subject', raise_exception=True)
def import_and_export_subject_page(request):
    from accounts.utils.pagination_utils import (
        paginate_queryset,
        search_queryset,
        get_pagination_context,
    )

    search_query = request.GET.get('search', '').strip()

    subjects = Subject.objects.all().select_related('assign_teacher', 'substitute_teacher')

    # Search
    search_fields = [
        'subject_name',
        'subject_short_name',
        'subject_code',
        'assign_teacher__first_name',
        'assign_teacher__last_name',
        'substitute_teacher__first_name',
        'substitute_teacher__last_name',
        'room_number',
    ]
    subjects = search_queryset(subjects, search_query, search_fields)

    # Pagination
    page_obj, paginator = paginate_queryset(subjects, request, items_per_page=10)
    pagination_context = get_pagination_context(page_obj, request)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    context.update(pagination_context)

    return render(request, 'subject/import_and_export_subject_page.html', context)
