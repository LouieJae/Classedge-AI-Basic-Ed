/* cl-tour-attendance-report.js — walkthrough for the Attendance
 * Report (course/templates/course/attendance/attendance-report.html),
 * reached from the teacher dashboard's quick-action strip.
 *
 * Stable anchors:
 *   .att-hero               — title + Take Attendance CTA
 *   #attTakeBtn             — Take Attendance button (opens subject picker modal)
 *   .att-summary            — total + bar + chip legend
 *   .att-summary-bar        — stacked percent bar
 *   .att-summary-legend     — Present / Late / Excused / Absent chips
 *   .att-today              — Today's classes collapsible (only if today_classes exists)
 *   .att-today-toggle       — self-attendance toggle per class
 *   .att-toolbar            — filter row (course / subject / status / dates)
 *   .att-search             — search input
 *   .att-table              — records table
 *   .att-status             — color-coded status badges
 *   [data-att-edit]         — inline-edit button per row
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

  add('attendance-report', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Attendance report',
        text:
          'A <strong>per-course log</strong> of who was present, who ' +
          'wasn\'t, and why. Filter, search, edit inline, and export — ' +
          'everything about attendance lives here.',
        attachTo: { element: '.att-hero', on: 'bottom' },
      },
      {
        id: 'take-attendance',
        title: 'Take attendance',
        text:
          'Opens a <strong>subject picker modal</strong>. Pick the course ' +
          'you\'re teaching right now, and you\'ll go to the roll-call ' +
          'screen for that class — the fastest way to start a new ' +
          'attendance session.',
        attachTo: { element: '#attTakeBtn', on: 'bottom' },
      },
      {
        id: 'summary',
        title: 'Summary at a glance',
        text:
          'Total record count up top, then a <strong>stacked percentage ' +
          'bar</strong>: <span style="color:var(--brand-primary)"><strong>green = Present</strong></span>, ' +
          'gold = Late, blue = Excused, rose = Absent. The chips below ' +
          'give exact counts and percentages.',
        attachTo: { element: '.att-summary', on: 'bottom' },
      },
      {
        id: 'today-classes',
        title: 'Today\'s classes',
        text:
          'A collapsible list of <strong>classes scheduled for today</strong>. ' +
          'Toggle <strong>Open</strong> to let students mark themselves ' +
          'present (self-attendance) during the class window — closes ' +
          'automatically when class ends.',
        attachTo: { element: '.att-today', on: 'bottom' },
      },
      {
        id: 'filters',
        title: 'Filter the records',
        text:
          'Narrow the list by <strong>program</strong>, <strong>course</strong>, ' +
          'specific <strong>status</strong> (e.g. Absent only), or a ' +
          '<strong>date range</strong>. Hit <em>Reset</em> to clear all ' +
          'at once.',
        attachTo: { element: '.att-toolbar', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Live search',
        text:
          'Type to filter by <strong>student name, subject, or status</strong>. ' +
          'Search runs as you type (debounced); Esc clears it. Use the ' +
          '<strong>Show … per page</strong> selector to set how many ' +
          'rows you see at once.',
        attachTo: { element: '.att-search', on: 'top' },
      },
      {
        id: 'table',
        title: 'Records table',
        text:
          'Each row is one attendance record. The <strong>color-coded ' +
          'status badge</strong> mirrors the chip palette: green = ' +
          'present, gold = late, blue = excused, rose = absent. Click a ' +
          'student\'s name to open their per-course calendar view.',
        attachTo: { element: '.att-table', on: 'top' },
      },
      {
        id: 'inline-edit',
        title: 'Inline edit',
        text:
          'The <strong>Edit</strong> button opens a small modal where ' +
          'you can change the status or add a remark — no page ' +
          'navigation needed. The row updates in place when you save.',
        attachTo: { element: '[data-att-edit]', on: 'left' },
      },
    ],
  });
})();
