from subject.models.sdg_models import SDG
from activity.models.activity_model import ActivityType


def get_or_create_sdg(name="Quality Education"):
    obj, _ = SDG.objects.get_or_create(name=name)
    return obj


def get_or_create_activity_type(name="Quiz"):
    obj, _ = ActivityType.objects.get_or_create(name=name)
    return obj


def make_received_subject(central_id=42, central_version=1, **kwargs):
    from received_central_content.models import ReceivedCentralSubject
    defaults = dict(
        central_id=central_id,
        central_version=central_version,
        subject_name="Algebra 1",
        subject_descriptive_title="Foundations of Algebra",
        subject_short_name="ALG1",
        subject_description="Central description",
        subject_code="ALG101",
        subject_type="Lec",
        unit=3,
        target_grade_level="Grade 7",
        target_curriculum="K-12",
    )
    defaults.update(kwargs)
    return ReceivedCentralSubject.objects.create(**defaults)


def make_received_module(received_subject=None, central_id=101, **kwargs):
    from received_central_content.models import ReceivedCentralModule
    if received_subject is None:
        received_subject = make_received_subject()
    defaults = dict(
        received_subject=received_subject,
        central_id=central_id,
        file_name="Module 1",
        description="Intro",
        order=0,
        url="",
        iframe_code="",
    )
    defaults.update(kwargs)
    return ReceivedCentralModule.objects.create(**defaults)


def make_received_activity(received_subject=None, central_id=201, **kwargs):
    from received_central_content.models import ReceivedCentralActivity
    if received_subject is None:
        received_subject = make_received_subject()
    activity_type = kwargs.pop("activity_type", None) or get_or_create_activity_type()
    defaults = dict(
        received_subject=received_subject,
        central_id=central_id,
        activity_name="Quiz 1",
        activity_instruction="Answer all",
        activity_type=activity_type,
        max_score=100,
        time_duration=30,
        passing_score=75,
        passing_score_type="percentage",
        max_retake=2,
        retake_method="highest",
        shuffle_questions=True,
        is_graded=True,
    )
    defaults.update(kwargs)
    return ReceivedCentralActivity.objects.create(**defaults)
