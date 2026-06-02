/* cl-tour-teacher-attendance-list.js — walkthrough for the Teacher Attendance
 * subject list (classroom/templates/timesheet/teacher_attendance_list.html).
 *
 * Entry point to teacher attendance: a list of subjects, each opening that
 * subject's attendance details. Legacy Bootstrap DataTable markup.
 *
 * Stable anchors:
 *   .tal-head                          — page header + pill (always)
 *   .teacher-attendance-list-table     — subjects table (always)
 *   .teacher-attendance-list-table .btn-primary — a "View" action (when rows exist)
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

  add('teacher-attendance-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Teacher attendance',
        text:
          'Your starting point for <strong>teacher attendance</strong> — ' +
          'every subject with a teacher, ready to drill into their session ' +
          'records.',
        attachTo: { element: '.tal-head', on: 'bottom' },
      },
      {
        id: 'table',
        title: 'Subjects & teachers',
        text:
          'Each row pairs a <strong>subject</strong> with its assigned ' +
          '<strong>teacher</strong>. Use the search and column sort to find ' +
          'one quickly.',
        attachTo: { element: '.teacher-attendance-list-table', on: 'top' },
        showOn: function () { return present('.teacher-attendance-list-table'); },
      },
      {
        id: 'view',
        title: 'Open the details',
        text:
          '<strong>View</strong> opens that subject\'s attendance — the ' +
          'calendar of sessions and the screenshots captured for each.',
        attachTo: { element: '.teacher-attendance-list-table .btn-primary', on: 'left' },
        showOn: function () { return present('.teacher-attendance-list-table .btn-primary'); },
      },
    ],
  });
})();
