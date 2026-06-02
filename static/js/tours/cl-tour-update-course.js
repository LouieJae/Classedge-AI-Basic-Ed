/* cl-tour-update-course.js — per-step walkthrough for the Update
 * Course form. Same 4-step stepper as create-course; copy is tuned
 * for editing an existing course rather than first-time setup.
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

  var FAMILY = 'update-course';

  add('update-course-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Update this course',
        text:
          'Four steps: <strong>Basics → Teaching → Program → Review</strong>. ' +
          'Renaming a course is safe — students and the gradebook follow ' +
          'the new name automatically.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Course name',
        text: 'Rename if needed — students see the new name on their next page load.',
        attachTo: { element: '#id_subject_name', on: 'bottom' },
      },
      {
        id: 'short-name',
        title: 'Short name',
        text:
          'Used in tight UI spaces (sidebar, breadcrumbs). Keep it under ' +
          '~20 characters.',
        attachTo: { element: '#id_subject_short_name', on: 'bottom' },
      },
      {
        id: 'code',
        title: 'Course code',
        text:
          'Be careful changing this — the gradebook, schedule, and ' +
          'analytics cross-reference by code.',
        attachTo: { element: '#id_subject_code', on: 'bottom' },
      },
      {
        id: 'type',
        title: 'Type',
        text:
          'Course category. Switching types <em>may</em> change the ' +
          'gradebook template — review before saving.',
        attachTo: { element: '#id_subject_type', on: 'bottom' },
      },
      {
        id: 'unit',
        title: 'Units',
        text:
          'Credit units. Changing this <strong>after grades exist</strong> ' +
          'can shift GPA calculations — do this only between semesters.',
        attachTo: { element: '#id_unit', on: 'bottom' },
      },
      {
        id: 'room',
        title: 'Room number',
        text:
          'Default room. Update this when classroom assignments change.',
        attachTo: { element: '#id_room_number', on: 'bottom' },
      },
      {
        id: 'photo',
        title: 'Course photo',
        text:
          'Upload a new image, or use the <strong>Remove</strong> button ' +
          'on the current-photo card to clear it.',
        attachTo: { element: '#id_subject_photo', on: 'top' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'Update topics covered, prerequisites, or learning outcomes.',
        attachTo: { element: '#id_subject_description', on: 'top' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text: 'Click <strong>Next</strong> to manage teacher assignments.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-course-teaching', {
    tourFamily: FAMILY,
    formStepKey: 'teaching',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'assign-teacher',
        title: 'Assigned teacher',
        text:
          'Re-assign the primary teacher. The new teacher gets full ' +
          'access immediately; the previous one loses access on save.',
        attachTo: { element: '#id_assign_teacher', on: 'bottom' },
      },
      {
        id: 'substitute',
        title: 'Substitute teacher',
        text:
          'Update or set a backup teacher. Doesn\'t grant access on its ' +
          'own — flip the toggle below when you actually need them in.',
        attachTo: { element: '#id_substitute_teacher', on: 'bottom' },
      },
      {
        id: 'allow-substitute',
        title: 'Allow substitute teacher',
        text:
          'Toggle <strong>on</strong> to hand off access; toggle ' +
          '<strong>off</strong> when the main teacher is back.',
        attachTo: { element: '#id_allow_substitute_teacher', on: 'right' },
      },
      {
        id: 'done-teaching',
        title: 'Step 2 done',
        text: 'Click <strong>Next</strong> to review program classification.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-course-program', {
    tourFamily: FAMILY,
    formStepKey: 'program',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'program-intro',
        title: 'Program type',
        text:
          'Switch the course\'s program classification — COIL, HALI, ' +
          'CTE — or pick none for a standard course. Selecting a ' +
          'program reveals (or hides) the partner-institution fields ' +
          'below.',
        attachTo: { element: '[data-mutex="program"]', on: 'bottom' },
      },
      {
        id: 'done-program',
        title: 'Step 3 done',
        text: 'Click <strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('update-course-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'Summary of the changes you\'re about to save. Click any step ' +
          'dot above to fix something — your edits are preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Save changes',
        text:
          'Click <strong>Update course</strong>. Students and assigned ' +
          'teachers see the updates on their next page load.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
