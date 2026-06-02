from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth.hashers import make_password
from accounts.models import CustomUser, Profile, Course
from roles.models import Role
import csv

@login_required
def import_students(request):
    if request.method == 'POST':
        import_file = request.FILES.get('import_file')
        if not import_file:
            messages.error(request, "No file selected. Please upload a CSV file.")
            return redirect('import_students')

        try:
            content = import_file.read().decode('utf-8-sig')
            
            reader = csv.DictReader(content.splitlines())
            
            with transaction.atomic():
                row_count = 0
                success_count = 0
                skip_count = 0
                
                for row in reader:
                    row_count += 1
                    
                    try:
                        cleaned_row = {}
                        for key, value in row.items():
                            clean_key = key.strip().lstrip('\ufeff\ufeff').strip()
                            cleaned_row[clean_key] = value.strip() if value else ''
                        
                        email = cleaned_row.get('Email', '').strip()
                        if not email:
                            skip_count += 1
                            continue
                            
                        first_name = cleaned_row.get('First Name', '').strip()
                        last_name = cleaned_row.get('Last Name', '').strip()
                        role_name = cleaned_row.get('Role', 'Student').strip()
                        id_number = cleaned_row.get('Identification', '').strip()
                        course_name = cleaned_row.get('Course', '').strip()
                        year_level = cleaned_row.get('Year Level', '').strip()
                        password_raw = cleaned_row.get('Password', '').strip()

                        password = make_password(password_raw) if password_raw else make_password('default123')

                        role, created = Role.objects.get_or_create(name=role_name)

                        course = Course.objects.filter(name__iexact=course_name).first() if course_name else None

                        user, created = CustomUser.objects.get_or_create(
                            email=email,
                            defaults={
                                'username': email.split('@')[0],
                                'first_name': first_name,
                                'last_name': last_name,
                                'password': password,
                            }
                        )
                        
                        profile, profile_created = Profile.objects.get_or_create(
                            user=user,
                            defaults={
                                'first_name': first_name,
                                'last_name': last_name,
                                'role': role,
                                'id_number': id_number,
                                'course': course,
                                'grade_year_level': year_level or None,
                            }
                        )

                        if profile_created:
                            success_count += 1
                        else:
                            profile.first_name = first_name or profile.first_name
                            profile.last_name = last_name or profile.last_name
                            profile.role = role
                            profile.id_number = id_number or profile.id_number
                            profile.course = course or profile.course
                            profile.grade_year_level = year_level or profile.grade_year_level
                            profile.save()
                            success_count += 1

                    except Exception as row_error:
                        messages.warning(request, f"Skipped row {row_count}: {row_error}")
                        skip_count += 1
                
                messages.success(request, f"Import completed: {success_count} users processed successfully")
                
        except UnicodeDecodeError as e:
            messages.error(request, "Invalid file encoding. Please use UTF-8 encoded CSV file.")
        except csv.Error as e:
            messages.error(request, f"CSV format error: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error importing file: {str(e)}")

        return redirect('teacher-list')

    return render(request, 'accounts/import/import_student.html')
