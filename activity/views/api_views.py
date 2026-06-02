from decimal import Decimal
from collections import defaultdict
from django.http import JsonResponse
from django.core.cache import cache
from django.db import models
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from activity.models import StudentActivity
from subject.models import Subject
from course.models import Term, Semester, Attendance, TeacherAttendancePoints
from gradebookcomponent.models import GradeBookComponents, GradeVisibilitySettings
from activity.serializers import StudentActivityScoreSerializer
from activity.utils import get_student_activity_summary, get_consolidated_student_grades
import decimal
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from accounts.utils import CustomPagination
from accounts.utils.security_utils import HasValidAPIKey

class student_score(ModelViewSet):
    serializer_class = StudentActivityScoreSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.serializer_class.Meta.model.objects.all()


class StudentScoreViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")
        user = request.user

        filtered_semester = Semester.objects.filter(id=semester_id).first() if semester_id else None
        filtered_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

        grade_calculation_method = filtered_semester.grade_calculation_method if filtered_semester else "Averaging"

        base_grade = filtered_semester.base_grade if filtered_semester else 0
        passing_grade = filtered_semester.passing_grade if filtered_semester else Decimal(75)

        queryset = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        ).filter(activity__status=True)

        if filtered_semester:
            queryset = queryset.filter(term__semester=filtered_semester)
        if filtered_subject:
            queryset = queryset.filter(activity__subject=filtered_subject)

        if hasattr(user, "profile") and user.profile.role:
            role = user.role_name

            if role == "student":
                queryset = queryset.filter(student=user)
            elif role == "teacher":
                teacher_subjects = Subject.objects.filter(
                    models.Q(assign_teacher=user) | models.Q(substitute_teacher=user)
                )
                queryset = queryset.filter(activity__subject__in=teacher_subjects)

        gradebook_components = GradeBookComponents.objects.select_related(
            "activity_type", "subject", "term"
        )

        gradebook_lookup = {}
        attendance_percentage_lookup = {}
        for component in gradebook_components:
            key = (
                component.activity_type.name if component.activity_type else "Unknown",
                component.subject.id,
                component.term.id,
            )
            gradebook_lookup[key] = Decimal(component.percentage)

            if component.is_attendance:
                attendance_percentage_lookup[component.term.id] = Decimal(component.percentage)

        terms = Term.objects.filter(semester=filtered_semester).order_by("start_date") if filtered_semester else []
        term_names = [term.term_name for term in terms]

        aggregated_data = defaultdict(lambda: {
            "term_scores": defaultdict(Decimal),
            "activities": defaultdict(lambda: defaultdict(lambda: {"total_score": 0, "max_score": 0})),
            "attendance": defaultdict(lambda: {"total_attendance": 0, "max_attendance": 0}),
            "has_remedial": False
        })

        for activity in queryset:
            student_id = activity.student.id
            student_name = f"{activity.student.profile.first_name} {activity.student.profile.last_name}"
            term_name = activity.term.term_name if activity.term else "Unknown Term"
            activity_type = activity.activity.activity_type.name if activity.activity and activity.activity.activity_type else "Unknown Activity Type"
            subject_id = activity.activity.subject.id if activity.activity and activity.activity.subject else None
            term_id = activity.term.id if activity.term else None
            max_score = activity.activity.max_score if activity.activity else 0
            percentage = gradebook_lookup.get((activity_type, subject_id, term_id), 0)

            adjusted_score = Decimal(activity.total_score)
            if adjusted_score == 0 and max_score > 0:
                base_points = (Decimal(base_grade / 100)) * max_score
                adjusted_score = max(adjusted_score, base_points)
                adjusted_score = min(adjusted_score, max_score)

            if activity_type not in aggregated_data[student_name]["activities"][term_name]:
                aggregated_data[student_name]["activities"][term_name][activity_type] = {
                    "total_score": 0,
                    "max_score": 0
                }

            aggregated_data[student_name]["student_id"] = student_id
            aggregated_data[student_name]["activities"][term_name][activity_type]["total_score"] += adjusted_score
            aggregated_data[student_name]["activities"][term_name][activity_type]["max_score"] += max_score

        attendance_records = Attendance.objects.select_related("subject", "student").filter(
            subject=filtered_subject,
            graded=True,
            date__range=(filtered_semester.start_date, filtered_semester.end_date)
        )

        for record in attendance_records:
            student_id = record.student.id
            student_name = f"{record.student.profile.first_name} {record.student.profile.last_name}"

            if student_name not in aggregated_data:
                aggregated_data[student_name]["student_id"] = student_id

            term_name = "Unknown Term"
            term_id = None
            for term in terms:
                if term.start_date <= record.date <= term.end_date:
                    term_name = term.term_name
                    term_id = term.id
                    break

            attendance_percentage = attendance_percentage_lookup.get(term_id, Decimal(0))
            points = TeacherAttendancePoints.objects.filter(teacher=record.teacher, status=record.status).first()
            attendance_points = points.points if points else 0

            aggregated_data[student_name]["attendance"][term_name]["total_attendance"] += attendance_points
            aggregated_data[student_name]["attendance"][term_name]["max_attendance"] += 10

        results = []
        failing_count = 0
        excelling_count = 0

        for student_name, data in aggregated_data.items():
            student_id = data["student_id"]
            term_scores = data["term_scores"]
            term_results = []

            total_final_grade = 0

            for term in terms:
                term_name = term.term_name
                term_score = 0
                activities = []

                for activity_type, scores in data["activities"][term_name].items():
                    total_score = scores["total_score"]
                    max_score = scores["max_score"]
                    percentage = gradebook_lookup.get((activity_type, subject_id, term.id), 0)

                    weighted_score = (total_score / max_score) * percentage if max_score > 0 else 0
                    term_score += weighted_score
                    activities.append({
                        "activity_type": activity_type,
                        "total_score": total_score,
                        "max_score": max_score,
                        "gradebook_percentage": percentage,
                        "weighted_score": round(weighted_score, 2),
                    })

                attendance_data = data["attendance"][term_name]
                if attendance_data["max_attendance"] > 0:
                    attendance_percentage = attendance_percentage_lookup.get(term.id, Decimal(0))
                    attendance_score = (attendance_data["total_attendance"] / attendance_data["max_attendance"]) * attendance_percentage

                    term_score += attendance_score
                    activities.append({
                        "activity_type": "Attendance",
                        "total_score": attendance_data["total_attendance"],
                        "max_score": attendance_data["max_attendance"],
                        "gradebook_percentage": attendance_percentage,
                        "weighted_score": round(attendance_score, 2),
                    })

                term_results.append({
                    "term_name": term_name,
                    "term_score": round(term_score, 2),
                    "activities": activities,
                })
                if grade_calculation_method == "Averaging":
                    total_final_grade += term_score
                elif grade_calculation_method == "Term Percentage":
                    term_percentage = term_percentage_lookup.get(term.id, Decimal(0)) / 100  # noqa: F821 (mirrors original)
                    total_final_grade += term_score * term_percentage

            if grade_calculation_method == "Averaging":
                total_final_grade = round(total_final_grade / len(terms), 2) if terms else 0

            has_remedial = data.get("has_remedial", False)
            if has_remedial:
                if passing_grade <= total_final_grade < passing_grade + 0.5:
                    total_final_grade = passing_grade
                else:
                    total_final_grade = round(total_final_grade, 2)
            else:
                total_final_grade = round(total_final_grade, 2)

            if total_final_grade < passing_grade:
                failing_count += 1
            elif total_final_grade >= 90:
                excelling_count += 1

            results.append({
                "student_full_name": student_name,
                "student_id": student_id,
                "final_grade": total_final_grade,
                "terms": term_results,
            })

        grades_visible = True
        if hasattr(user, "profile") and user.profile.role:
            role = user.role_name
            if role == "student":
                visibility_setting = GradeVisibilitySettings.objects.filter(
                    subject=filtered_subject,
                    term=None,
                ).first()
                grades_visible = visibility_setting.is_visible if visibility_setting else False

        response_data = {
            "results": results,
            "terms": term_names,
            "failing_count": failing_count,
            "excelling_count": excelling_count,
            "grades_visible": grades_visible,
        }

        return Response(response_data)

    def activity_type_summary(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")
        user = request.user

        filtered_semester = Semester.objects.filter(id=semester_id).first() if semester_id else None
        filtered_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

        if not filtered_semester or not filtered_subject:
            return Response({"error": "Semester and subject are required parameters"}, status=400)

        terms = Term.objects.filter(semester=filtered_semester).order_by("start_date")
        term_names = [term.term_name for term in terms]

        queryset = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        ).filter(
            activity__status=True,
            term__semester=filtered_semester,
            activity__subject=filtered_subject
        )

        if hasattr(user, "profile") and user.profile.role:
            role = user.role_name

            if role == "student":
                queryset = queryset.filter(student=user)
            elif role == "teacher":
                teacher_subjects = Subject.objects.filter(
                    models.Q(assign_teacher=user) | models.Q(substitute_teacher=user)
                )
                queryset = queryset.filter(activity__subject__in=teacher_subjects)

        gradebook_components = GradeBookComponents.objects.select_related(
            "activity_type", "subject", "term"
        ).filter(
            subject=filtered_subject,
            term__in=terms
        )

        gradebook_lookup = {}
        for component in gradebook_components:
            key = (
                component.activity_type.name if component.activity_type else "Unknown",
                component.subject.id,
                component.term.id,
            )
            gradebook_lookup[key] = Decimal(component.percentage)

        activity_type_summary = {
            "by_term": {term.term_name: {} for term in terms},
            "overall": {}
        }

        for activity in queryset:
            term_name = activity.term.term_name if activity.term else "Unknown Term"
            activity_type = activity.activity.activity_type.name if activity.activity and activity.activity.activity_type else "Unknown Activity Type"
            subject_id = activity.activity.subject.id if activity.activity and activity.activity.subject else None
            term_id = activity.term.id if activity.term else None
            max_score = activity.activity.max_score if activity.activity else 0
            total_score = activity.total_score

            if activity_type not in activity_type_summary["by_term"][term_name]:
                activity_type_summary["by_term"][term_name][activity_type] = {
                    "total_score": 0,
                    "max_score": 0,
                    "percentage": gradebook_lookup.get((activity_type, subject_id, term_id), 0),
                    "activity_count": 0
                }

            if activity_type not in activity_type_summary["overall"]:
                activity_type_summary["overall"][activity_type] = {
                    "total_score": 0,
                    "max_score": 0,
                    "activity_count": 0
                }

            activity_type_summary["by_term"][term_name][activity_type]["total_score"] += total_score
            activity_type_summary["by_term"][term_name][activity_type]["max_score"] += max_score
            activity_type_summary["by_term"][term_name][activity_type]["activity_count"] += 1

            activity_type_summary["overall"][activity_type]["total_score"] += total_score
            activity_type_summary["overall"][activity_type]["max_score"] += max_score
            activity_type_summary["overall"][activity_type]["activity_count"] += 1

        for term_name in activity_type_summary["by_term"]:
            for activity_type in activity_type_summary["by_term"][term_name]:
                data = activity_type_summary["by_term"][term_name][activity_type]
                if data["max_score"] > 0:
                    data["performance_percentage"] = round((data["total_score"] / data["max_score"]) * 100, 2)
                    data["weighted_score"] = round((data["total_score"] / data["max_score"]) * data["percentage"], 2)
                else:
                    data["performance_percentage"] = 0
                    data["weighted_score"] = 0

        for activity_type in activity_type_summary["overall"]:
            data = activity_type_summary["overall"][activity_type]
            if data["max_score"] > 0:
                data["performance_percentage"] = round((data["total_score"] / data["max_score"]) * 100, 2)
            else:
                data["performance_percentage"] = 0

        attendance_records = Attendance.objects.select_related("subject", "student").filter(
            subject=filtered_subject,
            graded=True,
            date__range=(filtered_semester.start_date, filtered_semester.end_date)
        )

        if attendance_records.exists():
            for term in terms:
                term_name = term.term_name
                term_attendance = attendance_records.filter(date__range=(term.start_date, term.end_date))

                if term_attendance.exists():
                    attendance_component = gradebook_components.filter(
                        term=term,
                        is_attendance=True
                    ).first()

                    attendance_percentage = Decimal(attendance_component.percentage) if attendance_component else Decimal(0)

                    if "Attendance" not in activity_type_summary["by_term"][term_name]:
                        activity_type_summary["by_term"][term_name]["Attendance"] = {
                            "total_score": 0,
                            "max_score": 0,
                            "percentage": attendance_percentage,
                            "activity_count": 0
                        }

                    total_attendance = 0
                    max_attendance = 0
                    for record in term_attendance:
                        points = TeacherAttendancePoints.objects.filter(
                            teacher=record.teacher,
                            status=record.status
                        ).first()
                        attendance_points = points.points if points else 0
                        total_attendance += attendance_points
                        max_attendance += 10

                    activity_type_summary["by_term"][term_name]["Attendance"]["total_score"] = total_attendance
                    activity_type_summary["by_term"][term_name]["Attendance"]["max_score"] = max_attendance
                    activity_type_summary["by_term"][term_name]["Attendance"]["activity_count"] = term_attendance.count()

                    if max_attendance > 0:
                        performance_percentage = round((total_attendance / max_attendance) * 100, 2)
                        weighted_score = round((total_attendance / max_attendance) * attendance_percentage, 2)
                        activity_type_summary["by_term"][term_name]["Attendance"]["performance_percentage"] = performance_percentage
                        activity_type_summary["by_term"][term_name]["Attendance"]["weighted_score"] = weighted_score

        grades_visible = True
        if hasattr(user, "profile") and user.profile.role:
            role = user.role_name
            if role == "student":
                visibility_setting = GradeVisibilitySettings.objects.filter(
                    subject=filtered_subject,
                    term=None,
                ).first()
                grades_visible = visibility_setting.is_visible if visibility_setting else False

        response_data = {
            "subject": filtered_subject.subject_name if filtered_subject else None,
            "semester": filtered_semester.semester_name if filtered_semester else None,
            "terms": term_names,
            "activity_type_summary": activity_type_summary,
            "grades_visible": grades_visible,
        }

        return Response(response_data)

@login_required
def get_subjects(request):
    semester_id = request.GET.get("semester")
    user = request.user
    
    subjects = Subject.objects.none()
    user_role = (user.role_name or 'unknown')

    if user_role == "student":
        subjects = Subject.objects.filter(
            subjectenrollment__student=user,
            subjectenrollment__semester_id=semester_id,
            subjectenrollment__status="enrolled"
        ).distinct()
    elif user_role == "teacher":
        subjects = Subject.objects.filter(
            models.Q(assign_teacher=user) | models.Q(substitute_teacher=user),
            subjectenrollment__semester_id=semester_id
        ).distinct()

    data = [{"id": subject.id, "subject_name": subject.subject_name, "subject_type": subject.subject_type} for subject in subjects]
    return JsonResponse(data, safe=False)


class dashboard_student_grade(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")
        user = request.user

        cache_key = f"student_scores_user_{user.id}_semester_{semester_id}_subject_{subject_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        filtered_semester = Semester.objects.filter(id=semester_id).first() if semester_id else None
        filtered_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

        base_grade = filtered_semester.base_grade if filtered_semester else 0
        passing_grade = filtered_semester.passing_grade if filtered_semester else Decimal(75)

        queryset = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        )

        if filtered_semester:
            queryset = queryset.filter(term__semester=filtered_semester)
        if filtered_subject:
            queryset = queryset.filter(activity__subject=filtered_subject)

        if hasattr(user, "profile") and user.profile.role:
            role = user.role_name

            if role == "student":
                queryset = queryset.filter(student=user)
            elif role == "teacher":
                teacher_subjects = Subject.objects.filter(
                    models.Q(assign_teacher=user) | models.Q(substitute_teacher=user)
                )
                queryset = queryset.filter(activity__subject__in=teacher_subjects)

        gradebook_components = GradeBookComponents.objects.select_related(
            "activity_type", "subject", "term"
        )

        gradebook_lookup = {}
        attendance_percentage_lookup = {}
        for component in gradebook_components:
            key = (
                component.activity_type.name if component.activity_type else "Unknown",
                component.subject.id,
                component.term.id,
            )
            gradebook_lookup[key] = Decimal(component.percentage)
            if component.is_attendance:
                attendance_percentage_lookup[component.term.id] = Decimal(component.percentage)

        terms = Term.objects.filter(semester=filtered_semester).order_by("start_date") if filtered_semester else []
        term_names = [term.term_name for term in terms]

        aggregated_data = defaultdict(lambda: {
            "term_scores": defaultdict(Decimal),
            "activities": defaultdict(lambda: defaultdict(lambda: {"total_score": 0, "max_score": 0})),
            "attendance": defaultdict(lambda: {"total_attendance": 0, "max_attendance": 0}),
            "has_remedial": False
        })

        for activity in queryset:
            student_id = activity.student.id
            student_name = f"{activity.student.profile.first_name} {activity.student.profile.last_name}"
            term_name = activity.term.term_name if activity.term else "Unknown Term"
            activity_type = activity.activity.activity_type.name if activity.activity and activity.activity.activity_type else "Unknown Activity Type"
            subject_id = activity.activity.subject.id if activity.activity and activity.activity.subject else None
            term_id = activity.term.id if activity.term else None
            max_score = activity.activity.max_score if activity.activity else 0
            percentage = gradebook_lookup.get((activity_type, subject_id, term_id), 0)

            adjusted_score = Decimal(activity.total_score)
            if adjusted_score == 0 and max_score > 0:
                base_points = (Decimal(base_grade / 100)) * max_score
                adjusted_score = max(adjusted_score, base_points)
                adjusted_score = min(adjusted_score, max_score)

            if activity_type not in aggregated_data[student_name]["activities"][term_name]:
                aggregated_data[student_name]["activities"][term_name][activity_type] = {
                    "total_score": 0,
                    "max_score": 0
                }

            aggregated_data[student_name]["student_id"] = student_id
            aggregated_data[student_name]["activities"][term_name][activity_type]["total_score"] += adjusted_score
            aggregated_data[student_name]["activities"][term_name][activity_type]["max_score"] += max_score

        attendance_records = Attendance.objects.select_related("subject", "student").filter(
            subject=filtered_subject,
            graded=True,
            date__range=(filtered_semester.start_date, filtered_semester.end_date)
        )

        for record in attendance_records:
            student_id = record.student.id
            student_name = f"{record.student.profile.first_name} {record.student.profile.last_name}"

            if student_name not in aggregated_data:
                aggregated_data[student_name]["student_id"] = student_id

            term_name = "Unknown Term"
            term_id = None
            for term in terms:
                if term.start_date <= record.date <= term.end_date:
                    term_name = term.term_name
                    term_id = term.id
                    break

            attendance_percentage = attendance_percentage_lookup.get(term_id, Decimal(0))
            points = TeacherAttendancePoints.objects.filter(teacher=record.teacher, status=record.status).first()
            attendance_points = points.points if points else 0

            aggregated_data[student_name]["attendance"][term_name]["total_attendance"] += attendance_points
            aggregated_data[student_name]["attendance"][term_name]["max_attendance"] += 10

        results = []
        failing_count = 0
        excelling_count = 0

        for student_name, data in aggregated_data.items():
            student_id = data["student_id"]
            term_scores = data["term_scores"]
            term_results = []

            total_final_grade = 0

            for term in terms:
                term_name = term.term_name
                term_score = 0
                activities = []

                for activity_type, scores in data["activities"][term_name].items():
                    total_score = scores["total_score"]
                    max_score = scores["max_score"]
                    percentage = gradebook_lookup.get((activity_type, subject_id, term.id), 0)

                    weighted_score = (total_score / max_score) * percentage if max_score > 0 else 0
                    term_score += weighted_score
                    activities.append({
                        "activity_type": activity_type,
                        "total_score": total_score,
                        "max_score": max_score,
                        "gradebook_percentage": percentage,
                        "weighted_score": round(weighted_score, 2),
                    })

                attendance_data = data["attendance"][term_name]
                if attendance_data["max_attendance"] > 0:
                    attendance_percentage = attendance_percentage_lookup.get(term.id, Decimal(0))
                    attendance_score = (attendance_data["total_attendance"] / attendance_data["max_attendance"]) * attendance_percentage

                    term_score += attendance_score
                    activities.append({
                        "activity_type": "Attendance",
                        "total_score": attendance_data["total_attendance"],
                        "max_score": attendance_data["max_attendance"],
                        "gradebook_percentage": attendance_percentage,
                        "weighted_score": round(attendance_score, 2),
                    })

                term_results.append({
                    "term_name": term_name,
                    "term_score": round(term_score, 2),
                    "activities": activities,
                })
                if grade_calculation_method == "Averaging":
                    total_final_grade += term_score
                elif grade_calculation_method == "Term Percentage":
                    term_percentage = term_percentage_lookup.get(term.id, Decimal(0)) / 100  # noqa: F821 (mirrors original)
                    total_final_grade += term_score * term_percentage

            if grade_calculation_method == "Averaging":
                total_final_grade = round(total_final_grade / len(terms), 2) if terms else 0

            has_remedial = data.get("has_remedial", False)
            if has_remedial:
                if passing_grade <= total_final_grade < passing_grade + 0.5:
                    total_final_grade = passing_grade
                else:
                    total_final_grade = round(total_final_grade, 2)
            else:
                total_final_grade = round(total_final_grade, 2)

            if total_final_grade < passing_grade:
                failing_count += 1
            elif total_final_grade >= 90:
                excelling_count += 1

            results.append({
                "student_full_name": student_name,
                "student_id": student_id,
                "final_grade": total_final_grade,
                "terms": term_results,
            })

        grades_visible = True
        if hasattr(user, "profile") and user.profile.role:
            role = user.role_name
            if role == "student":
                visibility_setting = GradeVisibilitySettings.objects.filter(
                    subject=filtered_subject,
                    term=None,
                ).first()
                grades_visible = visibility_setting.is_visible if visibility_setting else False

        response_data = {
            "results": results,
            "terms": term_names,
            "failing_count": failing_count,
            "excelling_count": excelling_count,
            "grades_visible": grades_visible,
        }

        return Response(response_data)

def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    return obj



class StudentAssessmentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")
        
        if not semester_id or not subject_id:
            return Response({"error": "Missing semester or subject ID"}, status=400)

        semester = Semester.objects.filter(id=semester_id).first()
        subject = Subject.objects.filter(id=subject_id).first()
                
        if not semester:
            return Response({"error": f"Semester with ID {semester_id} not found"}, status=404)
        
        if not subject:
            return Response({"error": f"Subject with ID {subject_id} not found"}, status=404)
        
        terms = Term.objects.filter(semester=semester).order_by("start_date")

        activities = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        ).filter(
            term__semester=semester,
            activity__subject=subject,
            activity__status=True
        )

        attendance = Attendance.objects.select_related("subject", "student").filter(
            subject=subject,
            graded=True,
            date__range=(semester.start_date, semester.end_date)
        )
        
        # Check for any students enrolled in this subject/semester
        from course.models import SubjectEnrollment
        enrollments = SubjectEnrollment.objects.filter(
            subject=subject,
            semester=semester,
            status="enrolled"
        )        
        # Check for any activities in this subject
        from activity.models import Activity
        all_activities = Activity.objects.filter(subject=subject, status=True)

        summary = get_student_activity_summary(semester, subject, terms, activities, attendance, request.user)

        summary = convert_decimals(summary)

        return Response(summary)


class StudentAssessmentConsolidatedSummaryView(APIView):
    authentication_classes = []  # Bypass JWT - use API key instead
    permission_classes = [HasValidAPIKey]
    pagination_class = CustomPagination

    def get(self, request):
        """Return consolidated grades for all subjects the student is enrolled in.

        - If ?semester=<id> is provided, use that semester.
        - Otherwise, use the current active semester based on today's date.
        - For each enrolled subject in that semester, compute consolidated grades
          using existing get_student_activity_summary + get_consolidated_student_grades.
        - Only returns subjects where grades have been finalized, unless force=True is provided.
        """
        user = request.user
        
        # Check for force parameter
        force_all = request.GET.get("force", "false").lower() == "true"

        # Determine semester
        semester_id = request.GET.get("semester")
        if semester_id:
            semester = Semester.objects.filter(id=semester_id).first()
        else:
            today = timezone.localdate()
            semester = Semester.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
            ).first()

        if not semester:
            return Response({"error": "No active semester found"}, status=400)

        # Get subjects based on force parameter
        if force_all:
            # Get all subjects with enrolled students in this semester
            subjects_qs = Subject.objects.filter(
                subjectenrollment__semester=semester,
                subjectenrollment__status="enrolled"
            ).distinct()
        else:
            # Get finalized subject IDs for this semester
            from subject.models import SubjectGradeFinalization
            finalized_subject_ids = SubjectGradeFinalization.get_finalized_subject_ids(semester)

            # Get all subjects with enrolled students in this semester that are finalized
            subjects_qs = Subject.objects.filter(
                subjectenrollment__semester=semester,
                subjectenrollment__status="enrolled",
                id__in=finalized_subject_ids
            ).distinct()

        paginator = self.pagination_class()
        page_subjects = paginator.paginate_queryset(subjects_qs, request)

        results = []

        terms = Term.objects.filter(semester=semester).order_by("start_date")

        for subject in page_subjects:
            activities = StudentActivity.objects.select_related(
                "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
            ).filter(
                term__semester=semester,
                activity__subject=subject,
                activity__status=True,
            )

            attendance = Attendance.objects.select_related("subject", "student").filter(
                subject=subject,
                graded=True,
                date__range=(semester.start_date, semester.end_date),
            )

            summary = get_student_activity_summary(
                semester, subject, terms, activities, attendance, None
            )

            consolidated = get_consolidated_student_grades(summary)
            consolidated = convert_decimals(consolidated)

            # Split subject_sync_id into subject_sync_id and schedule_sync_id
            sync_id = subject.subject_sync_id or ""
            if "_" in sync_id:
                subject_sync_part, schedule_sync_part = sync_id.split("_", 1)
            else:
                subject_sync_part = sync_id
                schedule_sync_part = None

            results.append({
                "subject_id": subject.id,
                "subject_name": getattr(subject, "subject_name", None),
                "subject_sync_id": subject_sync_part,
                "schedule_sync_id": schedule_sync_part,
                "grades": consolidated,
            })

        # Format semester name to short form (e.g., "First Semester" -> "1st", "Second Semester" -> "2nd")
        semester_short = None
        if semester:
            semester_name = semester.semester_name
            if semester_name == "First Semester":
                semester_short = "1st"
            elif semester_name == "Second Semester":
                semester_short = "2nd"
            elif semester_name == "Third Semester":
                semester_short = "3rd"
            elif semester_name == "Fourth Semester":
                semester_short = "4th"
            elif semester_name == "Summer":
                semester_short = "Summer"

        response_data = {
            "semester_name": getattr(semester, "semester_name", None) if semester else None,
            "academic_term_code": semester.get_academic_year() if semester else None,
            "semester": semester_short,
            "subjects": results,
        }
        
        return paginator.get_paginated_response(response_data)


class StudentAssessmentSummaryMobileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        semester_id = request.GET.get("semester")
        subject_id = request.GET.get("subject")

        if not semester_id or not subject_id:
            return Response({"error": "Missing semester or subject ID"}, status=400)

        semester = Semester.objects.filter(id=semester_id).first()
        subject = Subject.objects.filter(id=subject_id).first()
        terms = Term.objects.filter(semester=semester).order_by("start_date")

        activities = StudentActivity.objects.select_related(
            "activity", "activity__activity_type", "activity__subject", "term", "student__profile"
        ).filter(
            term__semester=semester,
            activity__subject=subject,
            activity__status=True
        )

        attendance = Attendance.objects.select_related("subject", "student").filter(
            subject=subject,
            graded=True,
            date__range=(semester.start_date, semester.end_date)
        )

        # Get full summary from the utility function
        full_summary = get_student_activity_summary(semester, subject, terms, activities, attendance, request.user)

        # Simplify the data structure for mobile
        simplified_summary = {}
        for student_name, data in full_summary.items():
            simplified_summary[student_name] = {
                "student_id": data.get("student_id"),
                "term_grades": {},
                "final_grade": float(data.get("final_grade", 0))
            }
            
            # Extract only term grades with category breakdowns
            term_grades = data.get("term_grades", {})
            for term_name, grades in term_grades.items():
                simplified_summary[student_name]["term_grades"][term_name] = {
                    "total_grade": float(grades.get("total_grade", 0))
                }

        return Response(simplified_summary)
