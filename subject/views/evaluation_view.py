from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from course.models import Semester, SubjectEnrollment
from subject.models import EvaluationQuestion, EvaluationAssignment, TeacherEvaluation, TeacherEvaluationResponse, Subject
from subject.forms.evaluation import EvaluationQuestionForm, EvaluationAssignmentForm, TeacherEvaluationForm


@login_required
def list_evaluation_questions(request):
    """[Classedge LMS] Themed evaluation-question bank using the reusable shell."""
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset

    search_query = request.GET.get('search', '').strip()
    qs = EvaluationQuestion.objects.all().order_by('-is_active', 'question_text')
    qs = search_queryset(qs, search_query, ['question_text'])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        'search_query': search_query,
        'title': 'Evaluation Question Bank',
        'icon': 'fa-list-ul',
        'search_placeholder': 'Search questions...',
        'empty_icon': 'fa-list-ul',
        'empty_label': 'questions',
        'columns': [
            {'label': '#', 'width': '60px', 'type': 'index'},
            {'label': 'Question', 'type': 'name', 'name_attr': 'question_text'},
            {'label': 'Status', 'type': 'status', 'attr': 'is_active',
             'map': {True: 'success', False: 'muted'}},
            {'label': 'Action', 'align': 'right', 'type': 'actions', 'items': [
                {'label': 'Update', 'icon': 'fa-edit',
                 'url_name': 'update_evaluation_question', 'url_arg_attr': 'id'},
                {'divider': True},
                {'label': 'Delete', 'icon': 'fa-trash', 'danger': True,
                 'form_post': True, 'url_name': 'delete_evaluation_question', 'url_arg_attr': 'id',
                 'confirm': 'Delete this question? Existing assignments using it will keep their snapshot.'},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get('partial') == '1':
        return render(request, 'includes/_list_table.html', context)
    return render(request, 'teacher_evaluation/list_of_evaluation_question.html', context)


@login_required
def create_evaluation_question(request, question_id=None):
    if question_id:
        question = get_object_or_404(EvaluationQuestion, id=question_id)
    else:
        question = EvaluationQuestion()

    if request.method == 'POST':
        form = EvaluationQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evaluation question saved successfully.')
            return redirect('list_questions')
    else:
        form = EvaluationQuestionForm(instance=question)

    return render(request, 'teacher_evaluation/create_evaluation_question.html', {'form': form, 'question': question})


@login_required
def update_evaluation_question(request, question_id=None):
    if question_id:
        question = get_object_or_404(EvaluationQuestion, id=question_id)
    else:
        question = EvaluationQuestion()

    if request.method == 'POST':
        form = EvaluationQuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, 'Evaluation question saved successfully.')
            return redirect('list_questions')
    else:
        form = EvaluationQuestionForm(instance=question)

    return render(request, 'teacher_evaluation/update_evaluation_question.html', {'form': form, 'question': question})


@login_required
def delete_evaluation_question(request, question_id):
    question = get_object_or_404(EvaluationQuestion, id=question_id)
    question.delete()
    messages.success(request, 'Evaluation question deleted successfully.')
    return redirect('list_questions')


@login_required
def list_evaluation_assignments(request):
    """[Classedge LMS] Themed evaluation-assignment list using the reusable shell."""
    from accounts.utils import get_pagination_context, paginate_queryset, search_queryset

    search_query = request.GET.get('search', '').strip()
    qs = EvaluationAssignment.objects.select_related('teacher', 'subject', 'semester').all()
    qs = search_queryset(qs, search_query, [
        'teacher__first_name', 'teacher__last_name', 'teacher__email',
        'subject__subject_name', 'subject__subject_code',
    ])
    page_obj, _ = paginate_queryset(qs, request, items_per_page=10)

    context = {
        'search_query': search_query,
        'form': EvaluationAssignmentForm(),
        'title': 'Teacher Evaluation Assignments',
        'icon': 'fa-clipboard-question',
        'search_placeholder': 'Search by teacher name or subject...',
        'empty_icon': 'fa-clipboard-question',
        'empty_label': 'evaluation assignments',
        'columns': [
            {'label': '#', 'width': '60px', 'type': 'index'},
            {'label': 'Teacher', 'type': 'name',
             'first_attr': 'teacher.first_name', 'last_attr': 'teacher.last_name'},
            {'label': 'Subject', 'type': 'pill', 'attr': 'subject.subject_name'},
            {'label': 'Semester', 'type': 'pill', 'attr': 'semester.semester_name'},
            {'label': 'Action', 'align': 'right', 'type': 'actions', 'items': [
                {'label': 'Update', 'icon': 'fa-edit',
                 'url_name': 'update_teacher_evaluation', 'url_arg_attr': 'id'},
                {'divider': True},
                {'label': 'Delete', 'icon': 'fa-trash', 'danger': True,
                 'form_post': True,
                 'url_name': 'delete_evaluation_assignment', 'url_arg_attr': 'id',
                 'confirm': 'Delete this evaluation assignment?'},
            ]},
        ],
    }
    context.update(get_pagination_context(page_obj, request))
    if request.GET.get('partial') == '1':
        return render(request, 'includes/_list_table.html', context)
    return render(request, 'teacher_evaluation/list_assignments.html', context)


@login_required
def create_teacher_evaluation(request, assignment_id=None):
    if assignment_id:
        assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    else:
        assignment = EvaluationAssignment()

    if request.method == 'POST':
        form = EvaluationAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = assignment.subject.assign_teacher

            current_semester = Semester.objects.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
            if current_semester:
                assignment.semester = current_semester

            try:
                assignment.save()
            except IntegrityError:
                messages.error(request, 'An error occurred while saving the evaluation assignment.')
                return redirect('create_teacher_evaluation')

            active_questions = EvaluationQuestion.objects.filter(is_active=True)
            assignment.questions.set(active_questions)

            messages.success(request, 'Evaluation assignment saved successfully.')
            return redirect('list_evaluation_assignments')
    else:
        form = EvaluationAssignmentForm(instance=assignment)

    return render(request, 'teacher_evaluation/create_teacher_evaluation.html', {
        'form': form,
        'assignment': assignment
    })


@login_required
def update_teacher_evaluation(request, assignment_id=None):
    if assignment_id:
        assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    else:
        assignment = EvaluationAssignment()

    if request.method == 'POST':
        form = EvaluationAssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = assignment.subject.assign_teacher

            current_semester = Semester.objects.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
            if current_semester:
                assignment.semester = current_semester

            assignment.save()
            active_questions = EvaluationQuestion.objects.filter(is_active=True)
            assignment.questions.set(active_questions)

            messages.success(request, 'Evaluation assignment saved successfully.')
            return redirect('list_evaluation_assignments')
    else:
        form = EvaluationAssignmentForm(instance=assignment)

    return render(request, 'teacher_evaluation/update_teacher_evaluation.html', {'form': form, 'assignment': assignment})


@login_required
def delete_evaluation_assignment(request, assignment_id):
    assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    assignment.delete()
    messages.success(request, 'Evaluation assignment deleted successfully.')
    return redirect('list_evaluation_assignments')


@login_required
def submit_evaluation(request, assignment_id):
    assignment = get_object_or_404(EvaluationAssignment, id=assignment_id)
    student = request.user
    subject_id = assignment.subject.id

    if TeacherEvaluation.objects.filter(student=student, assignment=assignment).exists():
        messages.warning(request, "You have already answered this evaluation.")
        return redirect('list_available_evaluations')

    questions = assignment.questions.all()

    if request.method == 'POST':
        form = TeacherEvaluationForm(request.POST, questions=questions)
        if form.is_valid():
            evaluation = TeacherEvaluation.objects.create(student=student, assignment=assignment)
            for question in questions:
                rating = form.cleaned_data.get(f'rating_{question.id}')
                TeacherEvaluationResponse.objects.create(
                    evaluation=evaluation,
                    question=question,
                    rating=rating
                )

            general_feedback = form.cleaned_data.get('general_feedback')
            if general_feedback:
                evaluation.general_feedback = general_feedback
                evaluation.save()

            messages.success(request, "Evaluation submitted successfully.")
            return redirect('material-list', id=subject_id)
    else:
        form = TeacherEvaluationForm(questions=questions)

    return render(request, 'teacher_evaluation/submit_evaluation.html', {
        'form': form,
        'assignment': assignment
    })


@login_required
def list_evaluation_results(request):
    user_role = request.user.role_name

    if request.user.is_teacher:
        evaluated_assignments = TeacherEvaluation.objects.filter(
            assignment__semester=Semester.objects.filter(
                start_date__lte=timezone.now().date(),
                end_date__gte=timezone.now().date()
            ).first()
        ).values(
            'assignment__teacher', 'assignment__teacher__first_name', 'assignment__teacher__last_name',
            'assignment__subject', 'assignment__subject__subject_name', 'assignment__subject__room_number'
        ).distinct()
    else:
        evaluated_assignments = TeacherEvaluation.objects.values(
            'assignment__teacher', 'assignment__teacher__first_name', 'assignment__teacher__last_name',
            'assignment__subject', 'assignment__subject__subject_name','assignment__subject__room_number'
        ).distinct()

    evaluation_results = [
        {
            'teacher_id': assignment['assignment__teacher'],
            'teacher_name': f"{assignment['assignment__teacher__first_name']} {assignment['assignment__teacher__last_name']}",
            'subject_id': assignment['assignment__subject'],
            'subject_name': assignment['assignment__subject__subject_name'],
            'room_number': assignment['assignment__subject__room_number'],
            'result_url': reverse('view_evaluation_results', args=[assignment['assignment__teacher'], assignment['assignment__subject']])
        }
        for assignment in evaluated_assignments
    ]

    return render(request, 'teacher_evaluation/list_evaluation_results.html', {'evaluation_results': evaluation_results, 'user_role': user_role})


@login_required
def view_evaluation_results(request, teacher_id, subject_id):
    evaluations = TeacherEvaluation.objects.filter(
        assignment__teacher_id=teacher_id,
        assignment__subject_id=subject_id,
        assignment__semester=Semester.objects.filter(
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).first()
    )

    responses = TeacherEvaluationResponse.objects.filter(evaluation__in=evaluations)

    average_ratings = {}
    for question in EvaluationQuestion.objects.filter(assignments__teacher_id=teacher_id):
        question_responses = responses.filter(question=question)
        if question_responses.exists():
            average_ratings[question.question_text] = question_responses.aggregate(Avg('rating'))['rating__avg']

    feedback_with_students = evaluations.filter(general_feedback__isnull=False).values(
        'general_feedback', 'student__first_name', 'student__last_name'
    )

    likert_data = {}
    rating_labels = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    colors = ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#198754']

    for question in EvaluationQuestion.objects.filter(assignments__teacher_id=teacher_id):
        question_responses = responses.filter(question=question)
        if question_responses.exists():
            rating_counts = question_responses.values('rating').annotate(count=Count('rating'))
            rating_dict = {item['rating']: item['count'] for item in rating_counts}
            likert_data[question.question_text] = {
                'ratings': [
                    {'label': label, 'count': rating_dict.get(i, 0)}
                    for i, label in enumerate(rating_labels, start=1)
                ],
                'colors': colors
            }

    is_teacher = request.user.is_teacher

    context = {
        'average_ratings': average_ratings,
        'feedback_with_students': feedback_with_students,
        'likert_data': likert_data,
        'is_teacher': is_teacher,
    }
    return render(request, 'teacher_evaluation/view_results.html', context)


@login_required
def list_available_evaluations(request):
    student = request.user
    current_semester = Semester.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()

    enrolled_subjects = SubjectEnrollment.objects.filter(
        student=student,
        semester=current_semester,
        status='enrolled'
    )
    subject_ids = [enrollment.subject.id for enrollment in enrolled_subjects]

    available_evaluations = EvaluationAssignment.objects.filter(
        subject__id__in=subject_ids,
        semester=current_semester,
        is_visible=True
    ).exclude(
        evaluations__student=student
    ).select_related('teacher', 'subject').distinct()

    context = {
        'available_evaluations': available_evaluations
    }
    return render(request, 'teacher_evaluation/list_of_teacher_to_be_evaluated.html', context)


@login_required
def get_all_teachers_average_ratings_json(request):
    user = request.user
    role_name = user.role_name
    is_teacher = role_name == 'teacher'

    if is_teacher:
        assigned_subjects = Subject.objects.filter(Q(assign_teacher=user) | Q(substitute_teacher=user))
        evaluations = TeacherEvaluation.objects.filter(assignment__subject__in=assigned_subjects)
    else:
        evaluations = TeacherEvaluation.objects.all()

    average_ratings = evaluations.values(
        'assignment__subject__subject_name',
        'assignment__teacher__first_name',
        'assignment__teacher__last_name'
    ).annotate(
        average_rating=Avg('responses__rating')
    )

    ratings_data = [
        {
            'teacher_name': f"{item['assignment__teacher__first_name']} {item['assignment__teacher__last_name']}",
            'subject_name': item['assignment__subject__subject_name'],
            'average_rating': round(item['average_rating'], 2) if item['average_rating'] else 0,
        }
        for item in average_ratings
    ]

    return JsonResponse({'ratings': ratings_data})
