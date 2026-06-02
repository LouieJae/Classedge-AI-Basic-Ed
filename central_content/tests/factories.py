# central_content/tests/factories.py
"""Plain helper functions for building test fixtures.

No external factory library — just thin constructors with sane defaults.
"""
import secrets

from central_content.models import (
    CentralStaff,
    CentralSubject,
    CentralModule,
    CentralActivity,
)


_COUNTER = {"n": 0}


def _next():
    _COUNTER["n"] += 1
    return _COUNTER["n"]


def make_staff(role=CentralStaff.Role.EDITOR, email=None, password="testpass"):
    n = _next()
    email = email or f"user{n}@example.com"
    return CentralStaff.objects.create_user(
        email=email,
        full_name=f"User {n}",
        password=password,
        role=role,
    )


def make_editor(**kw):
    return make_staff(role=CentralStaff.Role.EDITOR, **kw)


def make_reviewer(**kw):
    return make_staff(role=CentralStaff.Role.REVIEWER, **kw)


def make_publisher(**kw):
    return make_staff(role=CentralStaff.Role.PUBLISHER, **kw)


def make_subject(created_by=None, state=CentralSubject.State.DRAFT, **kw):
    created_by = created_by or make_editor()
    defaults = {
        "subject_name": f"Subject {_next()}",
        "target_grade_level": "Grade 7",
        "target_curriculum": "K-12 DepEd",
        "created_by": created_by,
        "state": state,
    }
    defaults.update(kw)
    return CentralSubject.objects.create(**defaults)


def make_module(central_subject=None, created_by=None,
                state=CentralModule.State.DRAFT, **kw):
    created_by = created_by or make_editor()
    central_subject = central_subject or make_subject(created_by=created_by)
    defaults = {
        "central_subject": central_subject,
        "file_name": f"Lesson {_next()}",
        "created_by": created_by,
        "state": state,
    }
    defaults.update(kw)
    return CentralModule.objects.create(**defaults)


def make_activity(central_subject=None, created_by=None,
                  state=CentralActivity.State.DRAFT, **kw):
    from activity.models.activity_model import ActivityType
    atype, _ = ActivityType.objects.get_or_create(name="Quiz")
    created_by = created_by or make_editor()
    central_subject = central_subject or make_subject(created_by=created_by)
    defaults = {
        "central_subject": central_subject,
        "activity_name": f"Activity {_next()}",
        "activity_type": atype,
        "created_by": created_by,
        "state": state,
    }
    defaults.update(kw)
    return CentralActivity.objects.create(**defaults)


def make_binding(
    central_subject=None,
    target_school=None,
    school_subject_id=17,
    school_subject_name="Math 101",
    school_subject_code="MATH101",
    pushed_version=None,
    bound_by=None,
):
    from central_content.models import SchoolSubjectBinding
    if central_subject is None:
        central_subject = make_subject()
    if target_school is None:
        target_school = make_school()
    if bound_by is None:
        bound_by = make_publisher()
    return SchoolSubjectBinding.objects.create(
        central_subject=central_subject,
        target_school=target_school,
        school_subject_id=school_subject_id,
        school_subject_name=school_subject_name,
        school_subject_code=school_subject_code,
        pushed_version=pushed_version,
        bound_by=bound_by,
    )


def make_school(
    name="HCCCI",
    base_url="https://classedge.hccci.edu.ph",
    api_token=None,
    is_active=True,
    notes="",
    created_by=None,
):
    from central_content.models import School
    if created_by is None:
        created_by = make_publisher()
    return School.objects.create(
        name=name,
        base_url=base_url,
        api_token=api_token or secrets.token_hex(20),
        is_active=is_active,
        notes=notes,
        created_by=created_by,
    )


def make_textbook(central_subject=None, uploaded_by=None, status=None, num_chapters=5, **kw):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from central_content.models import ParsedTextbook, ParsedChapter

    if status is None:
        from central_content.models import ParsedTextbook as PT
        status = PT.Status.TOC_READY
    if uploaded_by is None:
        uploaded_by = make_editor()
    if central_subject is None:
        central_subject = make_subject(created_by=uploaded_by)
    defaults = {
        "central_subject": central_subject,
        "title": f"Textbook {_next()}",
        "original_file": SimpleUploadedFile("test.pdf", b"%PDF-fake", content_type="application/pdf"),
        "uploaded_by": uploaded_by,
        "status": status,
    }
    defaults.update(kw)
    tb = ParsedTextbook.objects.create(**defaults)
    for i in range(1, num_chapters + 1):
        ParsedChapter.objects.create(
            textbook=tb,
            chapter_number=i,
            title=f"Chapter {i}",
            start_page=i * 10,
            end_page=i * 10 + 9,
        )
    return tb


def make_curriculum_plan(textbook=None, generated_by=None, plan_data=None, **kw):
    from central_content.models import CurriculumPlan
    if generated_by is None:
        generated_by = make_publisher()
    if textbook is None:
        textbook = make_textbook(uploaded_by=make_editor())
    if plan_data is None:
        chapter_numbers = list(
            textbook.chapters.values_list("chapter_number", flat=True)
        )
        mid = len(chapter_numbers) // 2
        plan_data = [
            {"week": 1, "chapters": chapter_numbers[:mid] or chapter_numbers, "title": "Part A", "description": "First half"},
            {"week": 2, "chapters": chapter_numbers[mid:], "title": "Part B", "description": "Second half"},
        ]
        if not chapter_numbers[mid:]:
            plan_data = [plan_data[0]]
    defaults = {
        "textbook": textbook,
        "school_subject_id": 42,
        "session_count": 30,
        "minutes_per_session": 90,
        "model_key": "haiku",
        "plan_data": plan_data,
        "generated_by": generated_by,
    }
    defaults.update(kw)
    return CurriculumPlan.objects.create(**defaults)


def make_content_generation_job(curriculum_plan=None, triggered_by=None, **kw):
    from central_content.models import ContentGenerationJob
    if triggered_by is None:
        triggered_by = make_publisher()
    if curriculum_plan is None:
        curriculum_plan = make_curriculum_plan()
    defaults = {
        "curriculum_plan": curriculum_plan,
        "model_key": "haiku",
        "total_weeks": len(curriculum_plan.plan_data),
        "week_results": [
            {"week": entry["week"], "status": "pending"}
            for entry in curriculum_plan.plan_data
        ],
        "triggered_by": triggered_by,
    }
    defaults.update(kw)
    return ContentGenerationJob.objects.create(**defaults)
