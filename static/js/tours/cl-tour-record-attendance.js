/* cl-tour-record-attendance.js — walkthrough for the per-class
 * roll-call screen (course/templates/course/attendance/record-attendance.html),
 * reached from the attendance-report's Take Attendance button or
 * from any "Take attendance" link on a course.
 *
 * Stable anchors:
 *   .ta-header              — page title + self-attendance toggle
 *   .ta-self-toggle         — students-self-mark toggle
 *   .ta-toolbar             — date input + graded checkbox + quick chips
 *   #id_date                — date picker
 *   #graded                 — graded checkbox
 *   .ta-quick               — quick-mark-all chips row
 *   .ta-search              — student name filter
 *   .ta-summary             — running marked-count
 *   .ta-table               — roster table
 *   .ta-row                 — first student row
 *   .ta-status-pill         — first status pill (when rows exist)
 *   .ta-remark              — first remarks textarea
 *   #submitAttendance       — Submit button (sticky footer)
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

  add('record-attendance', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Take attendance',
        text:
          'Per-class roll call. <strong>Click each student\'s status</strong> ' +
          'in the table below, optionally add remarks, then hit Submit. ' +
          'Saves the whole class\'s attendance in one transaction.',
        attachTo: { element: '.ta-header', on: 'bottom' },
      },
      {
        id: 'self-attendance',
        title: 'Self-attendance toggle',
        text:
          'Flip this <strong>on</strong> to let students mark themselves ' +
          'present from their own devices (during the class window). ' +
          'Useful for large classes — you skim the marks after instead ' +
          'of clicking each row.',
        attachTo: { element: '.ta-self-toggle', on: 'bottom' },
      },
      {
        id: 'toolbar',
        title: 'Date, graded, and quick-mark',
        text:
          '<strong>Date</strong> defaults to today — change it for ' +
          'backfilling a missed class. <strong>Mark as Graded</strong> ' +
          'controls whether this attendance counts toward the gradebook. ' +
          'The <strong>Quick mark all as</strong> chips bulk-set every ' +
          'student to the chosen status (handy when most students are ' +
          'present and you only need to flip a few).',
        attachTo: { element: '.ta-toolbar', on: 'bottom' },
      },
      {
        id: 'search-summary',
        title: 'Filter &amp; track progress',
        text:
          '<strong>Search</strong> the roster by student name when you ' +
          'have a long class list. The <strong>marked count</strong> on ' +
          'the right shows how many students you\'ve set a status for — ' +
          'use it as a checklist so you don\'t miss anyone.',
        attachTo: { element: '.ta-search', on: 'bottom' },
      },
      {
        id: 'status-pills',
        title: 'Status pills',
        text:
          'Each pill shows the <strong>status name</strong> and the ' +
          '<strong>point value</strong> it contributes (e.g. Present = 1pt, ' +
          'Absent = 0pt). Click the pill to mark — it visually fills in ' +
          'so you can tell at a glance who\'s done.',
        attachTo: { element: '.ta-status-pill', on: 'top' },
      },
      {
        id: 'remarks',
        title: 'Remarks (optional)',
        text:
          'Per-student notes — "late by 10 min", "medical excuse", ' +
          '"left early for clinic". These show up in the attendance ' +
          'report\'s edit modal and on the student\'s detail page.',
        attachTo: { element: '.ta-remark', on: 'left' },
      },
      {
        id: 'submit',
        title: 'Submit when everyone\'s marked',
        text:
          'Submit saves all marks in one go. <strong>Validation kicks in</strong> ' +
          'if any student is still unmarked — the alert at the top of ' +
          'the table lights up and the submit button waits until you\'ve ' +
          'set a status for everyone.',
        attachTo: { element: '#submitAttendance', on: 'top' },
      },
    ],
  });
})();
