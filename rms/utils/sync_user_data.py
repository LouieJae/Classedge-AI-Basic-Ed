from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, Profile
from course.models import Semester, SubjectEnrollment
from subject.models import Subject
from accounts.utils.signal_utils import _thread_locals
from django.utils import timezone
from accounts.models import Department


def get_or_create_department(department_name):
    """
    Get or create a department by name.
    If the department doesn't exist, it will be created automatically.
    
    Args:
        department_name (str): The full name of the department
    
    Returns:
        Department: The department object (existing or newly created)
    """
    if not department_name:
        return None
    
    # Try to find existing department
    department = Department.objects.filter(name=department_name).first()
    
    if department:
        return department
    
    # Create new department if not found
    department = Department.objects.create(
        name=department_name,
    )
    
    return department


@transaction.atomic
def sync_user_data(data):
    """
    Sync user data from RMS API.
    Creates new user/profile if doesn't exist, updates if exists.
    
    Args:
        data (dict): User data from RMS API
    
    Returns:
        CustomUser: The created or updated user object
    """
    # Extract and validate school email only (skip if missing)
    student_email = (data.get("school_email") or "").strip().lower()
    if not student_email:
        # Skip records without school_email
        return None

    # Extract personal information
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    gender = (data.get("sex") or "").strip()
    nationality = (data.get("nationality") or "").strip()
    phone_number = (data.get("contact_no") or "").strip()
    place_of_birth = (data.get("place_of_birth") or "").strip()
    street = (data.get("permanent_address_street") or "").strip()
    barangay = (data.get("permanent_address_barangay") or "").strip()
    city = (data.get("permanent_address_city") or "").strip()
    province = (data.get("permanent_address_province") or "").strip()

    address = street + ", " + barangay + ", " + city + ", " + province
    
    
    # Parse date of birth
    date_of_birth = None
    if date_of_birth_str := (data.get("date_of_birth") or "").strip():
        try:
            date_of_birth = datetime.strptime(date_of_birth_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            pass
    
    # Get or create department
    department_obj = None
    if department_name := (data.get("department_name") or "").strip():
        department_obj = get_or_create_department(department_name)

    # Set flag to tell signal this is an RMS student creation
    _thread_locals.creating_rms_student = True
    
    try:
        # Get or create user with optimized update
        student_user, created_user = CustomUser.objects.get_or_create(
            email=student_email,
            defaults={
                "username": student_email.split("@")[0],
                "first_name": first_name,
                "last_name": last_name,
                "needs_password_setup": False,
                "needs_onboarding": False,
            }
        )
        
        if created_user:
            pass
        else:
            # Update user only if name changed
            user_updated_fields = []
            if student_user.first_name != first_name:
                student_user.first_name = first_name
                user_updated_fields.append('first_name')
            if student_user.last_name != last_name:
                student_user.last_name = last_name
                user_updated_fields.append('last_name')
            
            if user_updated_fields:
                student_user.save(update_fields=user_updated_fields)
        
        # Get or create profile
        profile, created_profile = Profile.objects.get_or_create(
            user=student_user,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "date_of_birth": date_of_birth,
                "gender": gender,
                "nationality": nationality,
                "address": address,
                "phone_number": phone_number,
                "department_fields": department_obj,
            }
        )
        
        if created_profile:
            print(f"      [SYNC] ✓ Created profile: {student_email}")
            if department_obj:
                print(f"      [SYNC]   → Department: {department_obj.name}")
        else:
            # Build list of fields to update
            updated_fields = []
            
            # Check and update each field
            field_updates = [
                ('first_name', first_name, first_name),
                ('last_name', last_name, last_name),
                ('date_of_birth', date_of_birth, date_of_birth),
                ('gender', gender, gender),
                ('nationality', nationality, nationality),
                ('address', address, address),
                ('phone_number', phone_number, phone_number),
                ('department_fields_id', department_obj.id if department_obj else None, department_obj),
            ]
            
            for field_name, new_value, condition in field_updates:
                current_value = getattr(profile, field_name)
                # Update if value changed and new value is not empty/None
                if current_value != new_value and condition:
                    setattr(profile, field_name, new_value)
                    updated_fields.append(field_name)
            
            # Save only if there are changes, using update_fields for efficiency
            if updated_fields:
                profile.save(update_fields=updated_fields)
        
    finally:
        # Always clean up the flag
        _thread_locals.creating_rms_student = False

    return student_user