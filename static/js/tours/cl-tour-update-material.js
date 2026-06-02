/* cl-tour-update-material.js — per-form-step walkthroughs for the
 * Update Material form. Mirrors cl-tour-create-material.js since the
 * field IDs are identical, but with update-flavored copy and a
 * different Step 2 (the existing file is shown above the dropzone and
 * the allow_download toggle lives here instead of in Schedule).
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

  var FAMILY = 'update-material';

  // ─── Step 1: Basics ─────────────────────────────────────────────────
  add('update-material-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Update this material',
        text:
          'Same 4-step layout as creation: <strong>Basics → Content → ' +
          'Schedule → Review</strong>. The material type (file / URL / ' +
          'embed) is locked here — if you need to change it, create a new ' +
          'material instead.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Material name',
        text:
          'Rename it if needed — students see the new name on their next ' +
          'page load. No need to re-publish.',
        attachTo: { element: '#id_file_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text:
          'Move the material to a different grading period. Useful if you ' +
          'pulled in a resource from last semester and want it filed under ' +
          'the current term.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'A short paragraph explaining <em>what the material is</em> and ' +
          '<em>why students should read it</em>. Update this to reflect ' +
          'any changes in scope or context.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text:
          'Click <strong>Next</strong> to review or replace the uploaded file.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 2: Content (replace file + allow_download) ────────────────
  add('update-material-content', {
    tourFamily: FAMILY,
    formStepKey: 'content',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'current-file',
        title: 'Current file',
        text:
          'The file currently attached. If you don\'t drop a new one, this ' +
          'stays in place — leave the dropzone untouched to keep the ' +
          'existing material.',
        attachTo: { element: '.current-file-note', on: 'bottom' },
      },
      {
        id: 'dropzone',
        title: 'Replace the file',
        text:
          'Drop a new file here to swap it out. Supported: <strong>PDF, ' +
          'images, video, PowerPoint, Word, Excel</strong>. Max ' +
          '<strong>30 MB</strong>. Students will see the new file on their ' +
          'next page load.',
        attachTo: { element: '#dropzone', on: 'bottom' },
      },
      {
        id: 'allow-download',
        title: 'Allow downloads',
        text:
          'When on, students can download the file. When off, they can ' +
          'only view it in-browser. Toggle this to protect copyrighted ' +
          'material that was previously downloadable.',
        attachTo: { element: '#id_allow_download', on: 'right' },
      },
      {
        id: 'done-content',
        title: 'Step 2 done',
        text:
          'Click <strong>Next</strong> to update scheduling and audience.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 3: Schedule &amp; audience ────────────────────────────────
  add('update-material-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'start-date',
        title: 'Start date',
        text:
          'When students can first see this material. Pushing it earlier ' +
          'opens the material immediately; later hides it again until that ' +
          'date.',
        attachTo: { element: '#id_start_date', on: 'bottom' },
      },
      {
        id: 'end-date',
        title: 'End date',
        text:
          'When the material disappears from students\' view. Extend this ' +
          'to keep the material available longer; clear it to keep the ' +
          'material visible indefinitely.',
        attachTo: { element: '#id_end_date', on: 'bottom' },
      },
      {
        id: 'audience',
        title: 'Audience',
        text:
          'Restrict this material to <strong>specific students</strong>. ' +
          'Use <em>Select all</em> to start with everyone, then remove. ' +
          '<strong>Leave empty</strong> to show it to every enrolled student.',
        attachTo: { element: '#id_display_lesson_for_selected_users', on: 'top' },
      },
      {
        id: 'done-schedule',
        title: 'Step 3 done',
        text:
          'Click <strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 4: Review &amp; save ──────────────────────────────────────
  add('update-material-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'This panel summarizes the changes you\'re about to save. Spot ' +
          'something wrong? Click any step dot above (or ' +
          '<strong>Back</strong>) to fix it — your edits are preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Save changes',
        text:
          'When the review looks right, click <strong>Save changes</strong>. ' +
          'Students will see the updated material on their next page load.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
