from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.core.files.storage import default_storage
from activity.models import Activity
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import os
import uuid

@method_decorator(login_required, name='dispatch')
class EditParticipationView(View):

    def get(self, request, activity_id):
        questions = request.session.get('questions', {})
        participation_data = None

        for q in questions.get(str(activity_id), []):
            if q.get('quiz_type') == 'Participation':
                participation_data = q.get('participation_data')
                break

        if not participation_data:
            messages.error(request, "No participation data found.")
            return redirect('add_quiz_type', activity_id=activity_id)

        activity = get_object_or_404(Activity, pk=activity_id)
        return render(request, 'activity/question/edit_participation.html', {
            'activity': activity,
            'participation_data': participation_data,
            'max_score': activity.max_score
        })

    def post(self, request, activity_id):
        questions = request.session.get('questions', {})

        if str(activity_id) not in questions:
            messages.error(request, "Activity not found in session.")
            return redirect('add_quiz_type', activity_id=activity_id)

        updated_data = []
        max_score = float(request.POST.get('max_score', 0))

        for key, value in request.POST.items():
            if key.startswith('score_'):
                student_id = key.split('_')[1]
                score = min(float(value or 0), max_score)
                name = request.POST.get(f'name_{student_id}')
                updated_data.append({
                    'student_id': int(student_id),
                    'student_name': name,
                    'score': score
                })

        # Update session data
        for idx, q in enumerate(questions[str(activity_id)]):
            if q.get('quiz_type') == 'Participation':
                questions[str(activity_id)][idx]['participation_data'] = updated_data
                break

        request.session['questions'] = questions
        request.session.modified = True

        messages.success(request, "Participation scores updated.")
        return redirect('add_quiz_type', activity_id=activity_id)


@method_decorator(login_required, name='dispatch')
class EditParticipationViewCM(View):
    def get(self, request, activity_id):
        questions = request.session.get('questions', {})
        participation_data = None

        for q in questions.get(str(activity_id), []):
            if q.get('quiz_type') == 'Participation' or q.get('quiz_type') == 'Direct Score':
                participation_data = q.get('participation_data')
                break

        if not participation_data:
            messages.error(request, "No participation data found.")
            return redirect('add_quiz_typeCM', activity_id=activity_id)

        activity = get_object_or_404(Activity, pk=activity_id)
        return render(request, 'activity/question/edit_participation_CM.html', {
            'activity': activity,
            'participation_data': participation_data,
            'max_score': activity.max_score
        })

    def post(self, request, activity_id):
        questions = request.session.get('questions', {})

        if str(activity_id) not in questions:
            messages.error(request, "Activity not found in session.")
            return redirect('add_quiz_typeCM', activity_id=activity_id)

        # Find the participation data in the session
        participation_data = None
        quiz_idx = -1
        for idx, q in enumerate(questions[str(activity_id)]):
            if q.get('quiz_type') == 'Participation' or q.get('quiz_type') == 'Direct Score':
                participation_data = q.get('participation_data', [])
                quiz_idx = idx
                break
        
        if participation_data is None:
            messages.error(request, "No participation data found.")
            return redirect('add_quiz_typeCM', activity_id=activity_id)
        
        max_score = float(request.POST.get('max_score', 0))
        
        # Process each student score and (optional) file upload from the form.
        # In Classroom Mode the teacher may upload a scan of the student's
        # actual paper test/quiz alongside the score.
        for key, value in request.POST.items():
            if key.startswith('score_'):
                student_id = int(key.split('_')[1])
                score = min(float(value or 0), max_score)

                file_path = None
                uploaded_file = request.FILES.get(f'file_{student_id}')
                if uploaded_file:
                    ext = os.path.splitext(uploaded_file.name)[1]
                    filename = f"{uuid.uuid4()}{ext}"
                    file_path = default_storage.save(
                        os.path.join('student_activity_files', filename),
                        uploaded_file,
                    )

                student_updated = False
                for i, student_data in enumerate(participation_data):
                    if student_data['student_id'] == student_id:
                        participation_data[i]['score'] = score
                        if file_path:
                            participation_data[i]['file_path'] = file_path
                        student_updated = True
                        break

                if not student_updated:
                    name = request.POST.get(f'name_{student_id}')
                    entry = {
                        'student_id': student_id,
                        'student_name': name,
                        'score': score,
                    }
                    if file_path:
                        entry['file_path'] = file_path
                    participation_data.append(entry)
        
        # Update the session with the modified participation data
        questions[str(activity_id)][quiz_idx]['participation_data'] = participation_data
        request.session['questions'] = questions
        request.session.modified = True

        messages.success(request, "Student scores updated.")
        return redirect('add_quiz_typeCM', activity_id=activity_id)
