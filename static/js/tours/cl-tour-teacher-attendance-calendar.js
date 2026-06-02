/* cl-tour-teacher-attendance-calendar.js — walkthrough for the per-subject
 * attendance calendar (classroom/templates/timesheet/teacher_attendance_calendar.html).
 *
 * FullCalendar of a teacher's class sessions for one subject, with a date
 * filter, PDF export, and click-through to per-date screenshots.
 *
 * Stable anchors:
 *   .tac-head        — page header + pill (always)
 *   .tac-info        — teacher / subject banner + screenshots link (always)
 *   #tac-filter      — date range filter + Export PDF (always)
 *   #calendar        — the FullCalendar grid (always)
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

  add('teacher-attendance-calendar', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Attendance calendar',
        text:
          'A month view of one teacher\'s <strong>class sessions</strong> ' +
          'for this subject. Days with recorded attendance are marked and ' +
          'clickable.',
        attachTo: { element: '.tac-head', on: 'bottom' },
      },
      {
        id: 'info',
        title: 'Who & what',
        text:
          'This banner confirms the <strong>teacher</strong> and ' +
          '<strong>subject</strong> in view. <strong>View All ' +
          'Screenshots</strong> jumps to the full session list for them.',
        attachTo: { element: '.tac-info', on: 'bottom' },
        showOn: function () { return present('.tac-info'); },
      },
      {
        id: 'filter',
        title: 'Narrow & export',
        text:
          'Set a <strong>start and end date</strong> to focus the calendar ' +
          'on a period, then <strong>Export PDF</strong> to save a snapshot ' +
          'of exactly what\'s shown.',
        attachTo: { element: '#tac-filter', on: 'bottom' },
        showOn: function () { return present('#tac-filter'); },
      },
      {
        id: 'calendar',
        title: 'Click a day',
        text:
          'Each marked day is a session. <strong>Click it</strong> to open ' +
          'the screenshots captured on that date — your evidence that class ' +
          'actually ran.',
        attachTo: { element: '#calendar', on: 'top' },
        showOn: function () { return present('#calendar'); },
      },
    ],
  });
})();
