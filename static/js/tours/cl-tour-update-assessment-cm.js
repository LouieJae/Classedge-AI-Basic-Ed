/* cl-tour-update-assessment-cm.js — Classroom Mode version of the
 * Update Assessment walkthrough. Same 4-step stepper as the ops
 * variant; family id is distinct so dismissal on one page doesn't
 * suppress the other.
 */
(function () {
  'use strict';

  function add(id, config) {
    if (window.ClTour && typeof window.ClTour.register === 'function') {
      window.ClTour.register(id, config);
    } else {
      (window.__clTourPending = window.__clTourPending || []).push([id, config]);
    }
  }

  var FAMILY = 'update-assessment-cm';

  add('update-assessment-cm-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Update assessment · Classroom Mode',
        text:
          'Same 4-step layout as the ops editor. <strong>If students have ' +
          'submitted</strong>, most fields lock — only schedule remains ' +
          'editable so existing grades stay safe.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      { id: 'name', title: 'Name', text: 'Rename if needed.', attachTo: { element: '#activity_name', on: 'bottom' } },
      { id: 'term', title: 'Term', text: 'Reassign to a different grading period.', attachTo: { element: '#term', on: 'bottom' } },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text: 'Click <strong>Next</strong> to update scheduling.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-assessment-cm-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      { id: 'max-retake', title: 'Max attempts', text: 'How many tries each student gets.', attachTo: { element: '#max_retake', on: 'bottom' } },
      { id: 'retake-method', title: 'Retake method', text: 'Which attempt counts toward the grade.', attachTo: { element: '#retake_method', on: 'bottom' } },
      { id: 'time-duration', title: 'Time limit', text: 'Per-attempt minutes.', attachTo: { element: '#time_duration', on: 'bottom' } },
      { id: 'passing', title: 'Passing score', text: 'Minimum passing score.', attachTo: { element: '#passing_score', on: 'bottom' } },
      { id: 'passing-type', title: 'Score type', text: 'Percentage or number.', attachTo: { element: '#passing_score_type', on: 'bottom' } },
      {
        id: 'start',
        title: 'Opens at',
        text: 'Most common reason teachers come back to this form is to extend or shift the schedule.',
        attachTo: { element: '#start_time', on: 'top' },
      },
      { id: 'end', title: 'Closes at', text: 'The deadline.', attachTo: { element: '#end_time', on: 'top' } },
      {
        id: 'done-schedule',
        title: 'Step 2 done',
        text: 'Click <strong>Next</strong> for behavior toggles.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-assessment-cm-behavior', {
    tourFamily: FAMILY,
    formStepKey: 'behavior',
    form: 'form[data-cl-stepper]',
    steps: [
      { id: 'shuffle', title: 'Shuffle questions', text: 'Randomizes order per student.', attachTo: { element: '#shuffle_questions', on: 'right' } },
      { id: 'graded', title: 'Graded', text: 'Counts toward the gradebook.', attachTo: { element: '#is_graded', on: 'right' } },
      { id: 'remedial', title: 'Remedial', text: 'Assign to specific students only.', attachTo: { element: '#remedial', on: 'right' } },
      { id: 'late', title: 'Allow late submission', text: 'Most common toggle for extending deadlines.', attachTo: { element: '#allow_late_submission', on: 'right' } },
      {
        id: 'done-behavior',
        title: 'Step 3 done',
        text: 'Click <strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-assessment-cm-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      { id: 'review', title: 'Read-through', text: 'Summary of changes. Click any dot to fix.', attachTo: { element: '[data-step-review]', on: 'top' } },
      {
        id: 'submit',
        title: 'Save changes',
        text: 'Click <strong>Update assessment</strong>. Students see changes on next load.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
