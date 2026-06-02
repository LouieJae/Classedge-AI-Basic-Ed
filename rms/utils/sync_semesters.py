from datetime import datetime
from django.core.exceptions import ValidationError
from course.models import Semester

def sync_semesters(data):
    semester_map = {
        "1st": "First Semester",
        "2nd": "Second Semester",
        "3rd": "Third Semester",
        "4th": "Fourth Semester",
        "Summer": "Summer",
    }

    grouped = {}
    for item in data:
        semester_key = item.get("semester")
        if not semester_key:
            continue
        grouped.setdefault(semester_key, item)

    for sem, item in grouped.items():
        try:
            if not item.get("start_date") or not item.get("end_date"):
                raise ValidationError("Missing start or end date.")

            semester_name = semester_map.get(item.get("semester"))
            if not semester_name:
                raise ValidationError(f"Invalid semester key: {item.get('semester')}")

            start_date = datetime.strptime(item["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(item["end_date"], "%Y-%m-%d").date()
            if end_date < start_date:
                raise ValidationError("End date cannot be earlier than start date.")

            Semester.objects.update_or_create(
                semester_name=semester_name,
                start_date=start_date,
                end_date=end_date,
                defaults={
                    "end_semester": not item.get("current_semester", False),
                    "passing_grade": 75,
                    "grade_calculation_method": "Averaging",
                }
            )

        except ValidationError:
            continue
