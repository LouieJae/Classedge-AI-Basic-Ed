/* cl-tour-enrollment-report.js — walkthrough for a student's Enrolment report
 * (accounts/templates/accounts/reports/enrollment_report.html).
 *
 * A single student's subjects and semester load — name, key stats, and the
 * grid of enrolled subjects.
 *
 * Stable anchors:
 *   .topbar      — student name, meta, and stat strip (always)
 *   .er-stats    — subjects / units / semester stats (always)
 *   .er-card     — enrolled-subjects card (always)
 *   .er-grid     — the subject grid (when any enrolments)
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

  function present(sel) { return !!document.querySelector(sel); }

  add('enrollment-report', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Enrolment report',
        text:
          'A single student\'s <strong>subjects and semester load</strong> ' +
          'at a glance — their identity and program are summarized up top.',
        attachTo: { element: '.topbar', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'Load at a glance',
        text:
          'The quick stats — how many <strong>subjects</strong> they\'re ' +
          'taking, units per subject, and which <strong>semester</strong> ' +
          'this reflects.',
        attachTo: { element: '.er-stats', on: 'bottom' },
        showOn: function () { return present('.er-stats'); },
      },
      {
        id: 'subjects',
        title: 'Enrolled subjects',
        text:
          'Every subject the student is enrolled in this term, each with ' +
          'its code and <strong>status</strong>. An empty card means no ' +
          'active enrolments yet.',
        attachTo: { element: '.er-card', on: 'top' },
        showOn: function () { return present('.er-card'); },
      },
    ],
  });
})();
