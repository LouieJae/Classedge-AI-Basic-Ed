/* cl-tour-update-material-cm.js — Classroom Mode version of the
 * Update Material walkthrough. Same 4-step stepper as the ops variant.
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

  var FAMILY = 'update-material-cm';

  add('update-material-cm-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Update material · Classroom Mode',
        text:
          'Same 4-step layout as the ops editor: ' +
          '<strong>Basics → Content → Schedule → Review</strong>. ' +
          'Material type is locked once created.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      { id: 'name', title: 'Material name', text: 'Rename if needed.', attachTo: { element: '#id_file_name', on: 'bottom' } },
      { id: 'term', title: 'Term', text: 'Move to a different grading period.', attachTo: { element: '#id_term', on: 'bottom' } },
      { id: 'description', title: 'Description', text: 'Update topic / scope.', attachTo: { element: '#id_description', on: 'top' } },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text: 'Click <strong>Next</strong> to manage file or content.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-material-cm-content', {
    tourFamily: FAMILY,
    formStepKey: 'content',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'dropzone',
        title: 'Replace file',
        text:
          'Drop a new file to swap. Leave the dropzone alone to keep the ' +
          'existing file in place. Max <strong>30 MB</strong>.',
        attachTo: { element: '#dropzone', on: 'bottom' },
      },
      {
        id: 'allow-download',
        title: 'Allow downloads',
        text: 'On = students can download; off = view-in-browser only.',
        attachTo: { element: '#id_allow_download', on: 'right' },
      },
      {
        id: 'done-content',
        title: 'Step 2 done',
        text: 'Click <strong>Next</strong> for scheduling and audience.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-material-cm-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      { id: 'start', title: 'Start date', text: 'When students first see it.', attachTo: { element: '#id_start_date', on: 'bottom' } },
      { id: 'end', title: 'End date', text: 'When it disappears. Leave empty for indefinite.', attachTo: { element: '#id_end_date', on: 'bottom' } },
      { id: 'audience', title: 'Audience', text: 'Restrict to specific students. Empty = everyone.', attachTo: { element: '#id_display_lesson_for_selected_users', on: 'top' } },
      {
        id: 'done-schedule',
        title: 'Step 3 done',
        text: 'Click <strong>Next</strong> for the review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-material-cm-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      { id: 'review', title: 'Read-through', text: 'Summary of edits. Click any dot to fix.', attachTo: { element: '[data-step-review]', on: 'top' } },
      {
        id: 'submit',
        title: 'Save changes',
        text: 'Click <strong>Save changes</strong>. Students see the update on next load.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
