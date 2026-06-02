/* cl-tour-teacher-attendance-details.js — walkthrough for the per-subject
 * attendance details (classroom/templates/timesheet/teacher_attendance_details.html).
 *
 * A table of a teacher's recorded sessions for one subject, each linking to
 * its captured screenshots. Legacy Bootstrap DataTable markup.
 *
 * Stable anchors:
 *   .tad-head                     — page header + pill (always)
 *   .tad-back                     — "Back to Calendar" link (always)
 *   .teacher-attendance-table     — sessions table (always)
 *   .teacher-attendance-table .btn-primary — a "View Screenshot" action (when rows exist)
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

  add('teacher-attendance-details', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Attendance details',
        text:
          'Every recorded <strong>session</strong> for this teacher and ' +
          'subject — start and end times, total duration, and the ' +
          'screenshots captured during class.',
        attachTo: { element: '.tad-head', on: 'bottom' },
      },
      {
        id: 'table',
        title: 'The session log',
        text:
          'Each row is one session — the <strong>date</strong>, the ' +
          'scheduled window, when the teacher actually <strong>started and ' +
          'ended</strong>, and the <strong>total time</strong> logged.',
        attachTo: { element: '.teacher-attendance-table', on: 'top' },
        showOn: function () { return present('.teacher-attendance-table'); },
      },
      {
        id: 'screenshot',
        title: 'See the evidence',
        text:
          '<strong>View Screenshot</strong> opens the captures taken during ' +
          'that session — proof the class was actually conducted.',
        attachTo: { element: '.teacher-attendance-table .btn-primary', on: 'left' },
        showOn: function () { return present('.teacher-attendance-table .btn-primary'); },
      },
      {
        id: 'back',
        title: 'Back to the calendar',
        text:
          'Use <strong>Back to Calendar</strong> to return to the month ' +
          'view and pick a different date.',
        attachTo: { element: '.tad-back', on: 'bottom' },
        showOn: function () { return present('.tad-back'); },
      },
    ],
  });
})();
