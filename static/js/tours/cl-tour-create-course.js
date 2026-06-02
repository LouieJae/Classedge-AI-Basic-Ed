/* cl-tour-create-course.js — per-step walkthrough for the
 * Create Course (subject) form. 4-step stepper: basics → teaching →
 * program → review.
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

  var FAMILY = 'create-course';

  // ─── Step 1: Basics ─────────────────────────────────────────────────
  add('create-course-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Welcome — let\'s set up a course',
        text:
          'Four steps: <strong>Basics → Teaching → Program → Review</strong>. ' +
          'You can jump between them anytime via the dots above. Nothing ' +
          'is saved until you click <em>Create course</em> on the last step.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Course name',
        text:
          'The full name students see. E.g. <em>"Introduction to ' +
          'Computer Science"</em>.',
        attachTo: { element: '#id_subject_name', on: 'bottom' },
      },
      {
        id: 'short-name',
        title: 'Short name',
        text:
          'An abbreviated name used in tight UI spaces (sidebar, ' +
          'breadcrumbs). Keep it under ~20 characters — e.g. ' +
          '<em>"Intro to CS"</em>.',
        attachTo: { element: '#id_subject_short_name', on: 'bottom' },
      },
      {
        id: 'code',
        title: 'Course code',
        text:
          'Your institution\'s canonical code — e.g. ' +
          '<em>"CS-101"</em>. Used by the gradebook, schedule, and ' +
          'analytics for cross-referencing.',
        attachTo: { element: '#id_subject_code', on: 'bottom' },
      },
      {
        id: 'type',
        title: 'Type',
        text:
          'Categorize the course — lecture, lab, seminar, etc. ' +
          'Different types may have different gradebook templates.',
        attachTo: { element: '#id_subject_type', on: 'bottom' },
      },
      {
        id: 'unit',
        title: 'Units',
        text:
          'Credit units for the course. This factors into GPA / weighted ' +
          'gradebook calculations.',
        attachTo: { element: '#id_unit', on: 'bottom' },
      },
      {
        id: 'room',
        title: 'Room number',
        text:
          'Default room where this course meets. Used by the schedule ' +
          'view and attendance reports.',
        attachTo: { element: '#id_room_number', on: 'bottom' },
      },
      {
        id: 'photo',
        title: 'Course photo',
        text:
          'Optional banner image for the course card. Square images work ' +
          'best; the system crops to a 16:9 thumbnail.',
        attachTo: { element: '#id_subject_photo', on: 'top' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'A short paragraph students see when previewing the course — ' +
          'topics covered, prerequisites, expected outcomes.',
        attachTo: { element: '#id_subject_description', on: 'top' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text:
          'Click <strong>Next</strong> to assign teachers.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 2: Teaching ───────────────────────────────────────────────
  add('create-course-teaching', {
    tourFamily: FAMILY,
    formStepKey: 'teaching',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'assign-teacher',
        title: 'Assigned teacher',
        text:
          'The primary teacher for this course. Gets full editing access ' +
          'to the course, gradebook, and roster.',
        attachTo: { element: '#id_assign_teacher', on: 'bottom' },
      },
      {
        id: 'substitute',
        title: 'Substitute teacher',
        text:
          'Optional backup teacher. Doesn\'t see the course by default — ' +
          'flip the toggle below to grant access only when needed.',
        attachTo: { element: '#id_substitute_teacher', on: 'bottom' },
      },
      {
        id: 'allow-substitute',
        title: 'Allow substitute teacher',
        text:
          'Toggling this <strong>on</strong> grants the substitute full ' +
          'access — useful when the main teacher is out. Toggle it back ' +
          'off when they return.',
        attachTo: { element: '#id_allow_substitute_teacher', on: 'right' },
      },
      {
        id: 'done-teaching',
        title: 'Step 2 done',
        text:
          'Click <strong>Next</strong> to optionally classify this as a ' +
          'special program.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 3: Program type ───────────────────────────────────────────
  add('create-course-program', {
    tourFamily: FAMILY,
    formStepKey: 'program',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'program-intro',
        title: 'Program type — usually leave blank',
        text:
          'Most courses don\'t need a program type. Pick one only if ' +
          'the course is part of <strong>COIL</strong>, <strong>HALI</strong>, ' +
          'or <strong>CTE</strong> — they unlock extra fields below for ' +
          'industry partners, target SDGs, etc.',
        attachTo: { element: '[data-mutex="program"]', on: 'bottom' },
      },
      {
        id: 'coil',
        title: 'COIL',
        text:
          '<strong>Collaborative Online International Learning</strong> — ' +
          'co-taught with a partner institution abroad. Reveals fields ' +
          'for partner country, SDGs, and enrollee caps.',
        attachTo: { element: '.coil-input', on: 'bottom' },
      },
      {
        id: 'hali',
        title: 'HALI',
        text:
          '<strong>Higher Asian Learning Initiative</strong> — regional ' +
          'partnership program. Shares the same extended fields as COIL.',
        attachTo: { element: '.hali-input', on: 'bottom' },
      },
      {
        id: 'cte',
        title: 'CTE',
        text:
          '<strong>Career &amp; Technical Education</strong> — vocational ' +
          'or industry-aligned course. Flags it for CTE reporting.',
        attachTo: { element: '.cte-input', on: 'bottom' },
      },
      {
        id: 'done-program',
        title: 'Step 3 done',
        text:
          'Click <strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 4: Review &amp; submit ────────────────────────────────────
  add('create-course-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'Summary of everything you entered. Click any step dot above ' +
          'to fix something — your data is preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Create the course',
        text:
          'Click <strong>Create course</strong>. You\'ll land on the new ' +
          'course\'s page, where you can start enrolling students and ' +
          'adding materials.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
