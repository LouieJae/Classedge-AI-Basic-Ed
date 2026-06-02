/* cl-tour-create-assessment-cm.js — single-page walkthrough for the
 * Classroom Mode Create Assessment form. Streamlined (no stepper —
 * CM hides retake/time/shuffle behind sensible defaults).
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

  add('create-assessment-cm', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Classroom Mode — create an assessment',
        text:
          'Streamlined form for live class use. Fewer fields than the ' +
          'full editor — perfect for spinning up a quick quiz mid-lesson.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Assessment name',
        text:
          'A name students will recognize at a glance — e.g. ' +
          '<em>"Quick check — variables"</em>.',
        attachTo: { element: '#activity_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text: 'Which grading period this counts toward.',
        attachTo: { element: '#term', on: 'bottom' },
      },
      {
        id: 'instructions',
        title: 'Instructions',
        text:
          'A short briefing students read before starting. Tell them ' +
          'what\'s being assessed and any rules (open book, no calculators).',
        attachTo: { element: '#activity_instruction', on: 'bottom' },
      },
      {
        id: 'passing',
        title: 'Passing score',
        text:
          'Minimum passing score. Used by the gradebook and class ' +
          'analytics to flag at-risk students.',
        attachTo: { element: '#passing_score', on: 'top' },
      },
      {
        id: 'window',
        title: 'Open / close window',
        text:
          '<strong>Opens at</strong> is when students can begin. ' +
          '<strong>Closes at</strong> is the deadline. Set both for live ' +
          'class use.',
        attachTo: { element: '#start_time', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Save assessment',
        text:
          'Click <strong>Save assessment</strong>. The next screen is the ' +
          'question editor — add the actual questions there.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
