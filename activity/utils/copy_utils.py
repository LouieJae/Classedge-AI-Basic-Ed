from django.shortcuts import get_object_or_404
from activity.models import Activity, ActivityQuestion
from logs.models import SubjectLog
from subject.models import Subject
from module.models import Module


def copy_activities_from_subject(source_subject_id, target_subject_id, selected_activity_ids, start_time=None, end_time=None, term=None, target_modules=None):
    """
    Copy selected activities from one subject to another.
    
    Args:
        source_subject_id: ID of the source subject
        target_subject_id: ID of the target subject
        selected_activity_ids: List of activity IDs to copy
        start_time: Optional custom start time for copied activities
        end_time: Optional custom end time for copied activities
        term: Optional custom term for copied activities
        target_modules: Optional list of modules to anchor the copied activities to
    """
    source_subject = get_object_or_404(Subject, id=source_subject_id)
    target_subject = get_object_or_404(Subject, id=target_subject_id)

    activities = Activity.objects.filter(subject=source_subject, pk__in=selected_activity_ids)

    copied_count = 0
    for activity in activities:
        if Activity.objects.filter(
                subject=target_subject,
                activity_name=activity.activity_name,
                activity_type=activity.activity_type
        ).exists():
            continue

        # Use custom dates/term if provided, otherwise use original
        final_start_time = start_time if start_time is not None else activity.start_time
        final_end_time = end_time if end_time is not None else activity.end_time
        final_term = term if term is not None else activity.term

        new_activity = Activity.objects.create(
            activity_name=activity.activity_name,
            activity_type=activity.activity_type,
            subject=target_subject,
            term=final_term,
            start_time=final_start_time,
            end_time=final_end_time,
            show_score=activity.show_score,
            remedial=False,
            max_retake=activity.max_retake,
            time_duration=activity.time_duration,
            max_score=activity.max_score,
            status=activity.status,
            passing_score=activity.passing_score,
            passing_score_type=activity.passing_score_type,
            retake_method=activity.retake_method,
            activity_instruction=activity.activity_instruction,
            classroom_mode=activity.classroom_mode,
            shuffle_questions=activity.shuffle_questions
        )

        # Build list of modules to associate with the activity
        modules_to_add = []
        
        # If specific target modules were provided, use them
        if target_modules and len(target_modules) > 0:
            modules_to_add = list(target_modules)
        else:
            # Otherwise, try to find matching modules from source activity
            source_modules = list(activity.additional_modules.all())

            for source_module in source_modules:
                matching_module = Module.objects.filter(
                    subject=target_subject,
                    file_name=source_module.file_name
                ).first()

                if matching_module and matching_module not in modules_to_add:
                    modules_to_add.append(matching_module)

        # Add all modules to additional_modules
        if modules_to_add:
            new_activity.additional_modules.add(*modules_to_add)

        questions = ActivityQuestion.objects.filter(activity=activity)
        for question in questions:
            new_question = ActivityQuestion.objects.create(
                activity=new_activity,
                subject=new_activity.subject,
                question_text=question.question_text,
                correct_answer=question.correct_answer,
                quiz_type=question.quiz_type,
                score=question.score
            )

            for choice in question.choices.all():
                new_question.choices.create(choice_text=choice.choice_text, is_left_side=choice.is_left_side)

        SubjectLog.objects.create(
            subject=target_subject,
            activity=True,
            message=f"Copied activity '{activity.activity_name}' from subject {source_subject.subject_name}."
        )
        copied_count += 1

    return copied_count
