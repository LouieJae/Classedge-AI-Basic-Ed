from datetime import datetime
from django.core.exceptions import ValidationError
from course.models import Semester, Term
from accounts.models import CustomUser

def sync_terms(data, created_by=None):
    term_map = {
        "Prelim": "Prelim",
        "Midterm": "Midterm",
        "Pre-Final": "Pre-Final",
        "PreFinal": "Pre-Final",
        "Final": "Final Term",
        "Final Term": "Final Term",
    }
    
    for item in data:
        try:
            term_name_raw = item.get("term_name", "").strip()
            if not term_name_raw:
                continue
            
            term_name = term_map.get(term_name_raw)
            if not term_name:
                raise ValidationError(f"Unknown term name: {term_name_raw}")

            academic_term = item.get("academic_term")
            if not academic_term:
                raise ValidationError("Missing academic term data.")

            # Get existing semester instead of creating it
            semester_key = academic_term.get("semester")
            semester_name = {
                "1st": "First Semester",
                "2nd": "Second Semester",
                "3rd": "Third Semester",
                "4th": "Fourth Semester",
                "Summer": "Summer",
                
            }.get(semester_key)
            
            if not semester_name:
                raise ValidationError(f"Invalid semester key: {semester_key}")

            # IMPORTANT: Semester must already exist (created by sync_semesters)
            semester_obj = Semester.objects.filter(semester_name=semester_name).first()
            if not semester_obj:
                raise ValidationError(f"Semester '{semester_name}' not found. Run academic_terms sync first.")

            # Only create Term, not Semester
            Term.objects.update_or_create(
                term_name=term_name,
                semester=semester_obj,
                defaults={
                    "start_date": academic_term.get("start_date"),
                    "end_date": academic_term.get("end_date"),
                    "created_by": created_by if isinstance(created_by, CustomUser) else None,
                }
            )

        except ValidationError as e:
            pass
        except Exception as e:
            pass