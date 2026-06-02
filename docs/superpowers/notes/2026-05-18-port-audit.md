# Pre-port audit — Retake PK swap + source-of-truth port

**Date:** 2026-05-18
**Plan:** docs/superpowers/plans/2026-05-18-port-retake-pk-and-source-of-truth.md

## Prerequisites
- cuid version: `cuid==0.4` (requirements.txt line 27)

## Writers
```
activity/student_import_utils.py:286:        StudentQuestion.objects.bulk_create(new_student_questions, batch_size=1000)
activity/tasks.py:300:        StudentQuestion.objects.bulk_create(new_student_questions, batch_size=1000)
activity/views/activity_crud_views.py:524:                            StudentQuestion.objects.create(
activity/views/activity_crud_views.py:617:                        StudentQuestion.objects.get_or_create(
activity/views/answer_views.py:47:        sq, _ = StudentQuestion.objects.get_or_create(
activity/views/answer_views.py:566:            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)
activity/views/answer_views.py:621:            student_question, _ = StudentQuestion.objects.get_or_create(
activity/views/answer_views.py:731:            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)
activity/views/answer_views.py:913:            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)
activity/views/answer_views.py:1043:            sq, _ = StudentQuestion.objects.get_or_create(
activity/views/question_views.py:141:                    StudentQuestion.objects.bulk_create(new_rows, batch_size=200)
activity/views/question_views.py:425:                    StudentQuestion.objects.bulk_create(new_rows, batch_size=200)
activity/views/question_views.py:981:                StudentQuestion.objects.bulk_create(student_questions, batch_size=100)
activity/views/question_views.py:1036:                        StudentQuestion.objects.create(
activity/views/question_views.py:1085:                        StudentQuestion.objects.create(student=student, activity=activity, activity_question=question)
gradebookcomponent/tests/helpers.py:116:    StudentQuestion.objects.create(
mobile/views/activity_question_views.py:103:            student_question, created = StudentQuestion.objects.get_or_create(
mobile/views/student_activity_views.py:123:                    student_question = StudentQuestion.objects.create(
```

## Readers
```
activity/management/commands/seed_activity_questions.py:217:            sq_count = StudentQuestion.objects.filter(
activity/models/activity_model.py:304:                old = StudentQuestion.objects.get(pk=self.pk)
activity/student_export_utils.py:68:        questions = StudentQuestion.objects.filter(
activity/student_import_utils.py:263:                    sq = StudentQuestion.objects.get(student=student, activity_question=activity_question)
activity/tasks.py:277:                    sq = StudentQuestion.objects.get(student=student, activity_question=activity_question)
activity/tasks.py:370:            questions = StudentQuestion.objects.filter(
activity/views/activity_crud_views.py:517:                        existing_question = StudentQuestion.objects.filter(
activity/views/activity_crud_views.py:617:                        StudentQuestion.objects.get_or_create(
activity/views/answer_views.py:47:        sq, _ = StudentQuestion.objects.get_or_create(
activity/views/answer_views.py:210:            student_questions = StudentQuestion.objects.filter(student=user, activity_question__activity=activity)
activity/views/answer_views.py:322:                for sq in StudentQuestion.objects.filter(student=user, activity=activity)
activity/views/answer_views.py:460:            student_questions = StudentQuestion.objects.filter(student=user, activity_question__activity=activity)
activity/views/answer_views.py:566:            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)
activity/views/answer_views.py:621:            student_question, _ = StudentQuestion.objects.get_or_create(
activity/views/answer_views.py:731:            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)
activity/views/answer_views.py:853:            student_question = StudentQuestion.objects.get(student=student, activity_question=question)
activity/views/answer_views.py:913:            student_question, created = StudentQuestion.objects.get_or_create(student=student, activity_question=question)
activity/views/answer_views.py:953:            StudentQuestion.objects.filter(student=student, activity_question__activity=activity).update(
activity/views/answer_views.py:1043:            sq, _ = StudentQuestion.objects.get_or_create(
activity/views/grading_views.py:34:        student_questions = StudentQuestion.objects.filter(
activity/views/grading_views.py:59:        student_questions = StudentQuestion.objects.filter(
activity/views/question_admin_views.py:31:        and StudentQuestion.objects.filter(activity=activity, is_participation=True).exists()
activity/views/question_admin_views.py:41:            for sq in StudentQuestion.objects.filter(activity=activity, is_participation=True)
activity/views/question_views.py:101:                StudentQuestion.objects.filter(activity=activity, is_participation=True).delete()
activity/views/question_views.py:385:                StudentQuestion.objects.filter(activity=activity, is_participation=True).delete()
calendars/views.py:133:        answered_activity_ids = StudentQuestion.objects.filter(student=user).values_list('activity_question__activity_id', flat=True).distinct()
calendars/views.py:171:                answered_activity_ids = StudentQuestion.objects.filter(student=user).values_list(
course/views/classroom_views.py:110:        completed_activities = StudentQuestion.objects.filter(
course/views/classroom_views.py:116:        answered_essays = StudentQuestion.objects.filter(
course/views/classroom_views.py:123:        answered_documents = StudentQuestion.objects.filter(
course/views/classroom_views.py:150:            pk__in=StudentQuestion.objects.filter(
course/views/classroom_views.py:155:            pk__in=StudentQuestion.objects.filter(
course/views/classroom_views.py:190:            pk__in=StudentQuestion.objects.filter(
course/views/classroom_views.py:196:            pk__in=StudentQuestion.objects.filter(
course/views/classroom_views.py:225:            ungraded_items = StudentQuestion.objects.filter(
course/views/subject_details_views.py:108:        completed_activities = StudentQuestion.objects.filter(
course/views/subject_details_views.py:114:        answered_essays = StudentQuestion.objects.filter(
course/views/subject_details_views.py:121:        answered_documents = StudentQuestion.objects.filter(
course/views/subject_details_views.py:146:            pk__in=StudentQuestion.objects.filter(
course/views/subject_details_views.py:151:            pk__in=StudentQuestion.objects.filter(
course/views/subject_details_views.py:182:            pk__in=StudentQuestion.objects.filter(
course/views/subject_details_views.py:188:            pk__in=StudentQuestion.objects.filter(
course/views/subject_details_views.py:214:            ungraded_items = StudentQuestion.objects.filter(
course/views/subject_details_views.py:367:        completed_activities = StudentQuestion.objects.filter(
course/views/subject_details_views.py:373:        answered_essays = StudentQuestion.objects.filter(
course/views/subject_details_views.py:380:        answered_documents = StudentQuestion.objects.filter(
course/views/subject_details_views.py:402:            pk__in=StudentQuestion.objects.filter(is_participation=True).values_list('activity_id', flat=True)
course/views/subject_details_views.py:407:            pk__in=StudentQuestion.objects.filter(is_participation=True).values_list('activity_id', flat=True)
course/views/subject_details_views.py:436:            pk__in=StudentQuestion.objects.filter(is_participation=True).values_list('activity_id', flat=True)
course/views/subject_details_views.py:441:            pk__in=StudentQuestion.objects.filter(is_participation=True).values_list('activity_id', flat=True)
course/views/subject_details_views.py:463:            ungraded_items = StudentQuestion.objects.filter(
course/views/subject_details_views.py:585:        student_activities = StudentQuestion.objects.filter(
course/views/subject_details_views.py:601:            pk__in=StudentQuestion.objects.values_list('activity_question__activity_id', flat=True).distinct()
gradebookcomponent/services/queue.py:62:    submitted_subq = StudentQuestion.objects.filter(
gradebookcomponent/tests/test_queue_service.py:41:        StudentQuestion.objects.filter(
gradebookcomponent/views/activity_details_view.py:29:        sq_submission = StudentQuestion.objects.filter(
gradebookcomponent/views/activity_details_view.py:70:        submission_date = StudentQuestion.objects.filter(
gradebookcomponent/views/activity_details_view.py:124:        student_questions = StudentQuestion.objects.filter(student=student, activity=activity)
gradebookcomponent/views/instructor_grading.py:351:        StudentQuestion.objects.filter(student=sa.student, activity=sa.activity)
gradebookcomponent/views/utility_view.py:80:                    total_score = StudentQuestion.objects.filter(
gradebookcomponent/views/utility_view.py:1216:                    total_score = StudentQuestion.objects.filter(activity=activity, student=student).aggregate(total_score=Sum('score'))['total_score'] or 0
mobile/views/activity_question_views.py:103:            student_question, created = StudentQuestion.objects.get_or_create(
mobile/views/student_activity_views.py:109:                student_question = StudentQuestion.objects.filter(
mobile/views/student_activity_views.py:135:                duplicates = StudentQuestion.objects.filter(
mobile/views/student_question_views.py:16:        return StudentQuestion.objects.filter(activity_question_id=question_id)
module/views/display_views.py:171:        ungraded_items = StudentQuestion.objects.filter(
```

## total_score mutations
```
activity/services/auto_grader.py:115:        student_activity.total_score = new_total
activity/student_import_utils.py:222:                total_score=float(row.get("total_score") or 0),
activity/tasks.py:236:                total_score=float(row.get("total_score") or 0),
activity/views/answer_views.py:79:    student_activity.total_score = total
activity/views/answer_views.py:578:        student_activity.total_score = total_score
activity/views/answer_views.py:673:        student_activity.total_score = total_score
activity/views/answer_views.py:867:            student_activity.total_score = highest_score if highest_score is not None else 0
activity/views/answer_views.py:871:            student_activity.total_score = latest_record.score if latest_record else 0
activity/views/answer_views.py:875:            student_activity.total_score = avg_score if avg_score is not None else 0
activity/views/answer_views.py:879:            student_activity.total_score = first_record.score if first_record else 0
activity/views/answer_views.py:891:                student_activity.total_score = (
activity/views/answer_views.py:925:        student_activity.total_score = total_score
activity/views/answer_views.py:1080:            sa.total_score = running_total
activity/views/grading_views.py:128:            student_activity.total_score -= previous_score
activity/views/grading_views.py:136:            student_activity.total_score += score
activity/views/grading_views.py:208:            student_activity.total_score += score
activity/views/grading_views.py:263:                    student_activity.total_score = score
activity/views/grading_views.py:327:                    student_activity.total_score = score
activity/views/question_views.py:133:                    sa.total_score = score
activity/views/question_views.py:417:                    sa.total_score = score
activity/views/question_views.py:909:                            student_activity.total_score += participation['score']
activity/views/question_views.py:1050:                        student_activity.total_score += participation['score']
activity/views/score_admin_views.py:40:                student_activity.total_score = float(new_score)
gradebookcomponent/services/override.py:11:        student_activity.total_score = new_score
gradebookcomponent/views/instructor_grading.py:330:        sa.total_score = score
```

## PK-int casts to remove
none — safe to swap

(grep for `int\(retake_record_(id|detail_id)` across all `.py`, `.html`, `.js` returned zero hits)

## Cross-app FKs (record_details)
```
mobile/models/attachment.py:11:    record_details = models.ForeignKey('activity.RetakeRecordDetail', related_name='attachments', on_delete=models.PROTECT, null=True, blank=True)
```

Exactly one hit, in the expected location.

---

## Summary
- Total writer hits: 18
- Total reader hits: 66
- Files needing changes by app:
  - activity/views/: answer_views.py, question_views.py, activity_crud_views.py, grading_views.py, question_admin_views.py, score_admin_views.py
  - activity/ (non-views): student_import_utils.py, student_export_utils.py, tasks.py, services/auto_grader.py, models/activity_model.py, management/commands/seed_activity_questions.py
  - mobile/views/: activity_question_views.py, student_activity_views.py, student_question_views.py
  - gradebookcomponent/views/: utility_view.py, activity_details_view.py, instructor_grading.py
  - gradebookcomponent/services/: queue.py, override.py
  - course/views/: classroom_views.py, subject_details_views.py
  - calendars/views.py: yes (lines 133, 171)
  - module/views/: display_views.py

## Surprises / deviations from the LMS audit doc

### Files mentioned in the LMS audit that DO NOT exist in this (web) repo
- `simulation/generators/submissions.py` — no `simulation/` app in this repo
- `simulation/generators/single_date.py` — same
- `simulation/management/commands/generate_module_quizzes.py` — same
- `simulation/management/commands/generate_simulation_data.py` — same
- `simulation/tests/test_single_date_generator.py` — same
- `course/views/term_views.py` — LMS audit flags an import there; this file does not appear in the web grep results (either no `StudentQuestion` import or file absent)
- `module/views/progress_views.py` — LMS audit lists an import; not found in web grep results (either no usage or file absent)

### Files found in THIS repo not prominently called out in the LMS audit
- `activity/models/activity_model.py:304` — model-level `StudentQuestion.objects.get` (signal/save logic); not listed in LMS audit as a separate concern
- `gradebookcomponent/services/queue.py` — reader only in LMS audit notes; confirmed present here too
- `gradebookcomponent/views/instructor_grading.py` — both a reader (line 351) and a `total_score` writer (line 330); LMS audit did not break this out explicitly
- `activity/views/score_admin_views.py` — `total_score` mutation writer; not explicitly listed in LMS audit
- `mobile/views/student_question_views.py` — pure reader not mentioned separately in LMS audit

### Structural agreement with LMS audit
The LMS audit's key finding — that `mobile/views/student_activity_views.py` is an **external writer** creating both `RetakeRecordDetail` AND `StudentQuestion` rows — is confirmed here (lines 109, 123, 135). The dual-source problem is present in this repo too and the mobile writer must be migrated as part of the cutover.

The `gradebookcomponent/views/utility_view.py` pattern of recomputing `total_score` from `StudentQuestion.aggregate(Sum('score'))` (bypassing `StudentActivity.total_score`) is also confirmed at lines 80–82 and 1216.
