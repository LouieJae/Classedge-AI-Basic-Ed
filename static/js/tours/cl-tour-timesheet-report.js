/* cl-tour-timesheet-report.js — walkthrough for the Teacher Timesheet report
 * (classroom/templates/timesheet/teacher_timesheet_report.html).
 *
 * Punch-in / punch-out review for every teacher × subject — actual time vs
 * the scheduled budget, with filters and Excel exports.
 *
 * Stable anchors:
 *   .cl-header        — title + date-range chip (always)
 *   .ts-summary       — hours / attendance / on-time / no-show tiles (always)
 *   .ts-filter-grid   — date, teacher, semester filters (always)
 *   .ts-exports       — Excel export buttons (always)
 *   .ts-teacher-card  — first teacher × subject card (when records exist)
 *   .ts-table         — daily punch detail table (when records exist)
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

  add('timesheet-report', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Teacher timesheet',
        text:
          'A punch-in / punch-out review for every <strong>teacher × ' +
          'subject</strong> — actual class time measured against the ' +
          'scheduled budget. The chip on the right shows the date range ' +
          'you\'re viewing.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'summary',
        title: 'The numbers that matter',
        text:
          'Four headline tiles — <strong>hours clocked</strong> vs budget, ' +
          '<strong>attendance rate</strong>, <strong>on-time vs late</strong> ' +
          'starts, and <strong>no-shows</strong> (scheduled but never ' +
          'started).',
        attachTo: { element: '.ts-summary', on: 'bottom' },
        showOn: function () { return present('.ts-summary'); },
      },
      {
        id: 'filters',
        title: 'Scope the report',
        text:
          'Narrow by <strong>date range</strong>, a specific ' +
          '<strong>teacher</strong>, or a <strong>semester</strong>. The ' +
          'report refreshes as soon as you change a filter.',
        attachTo: { element: '.ts-filter-grid', on: 'bottom' },
        showOn: function () { return present('.ts-filter-grid'); },
      },
      {
        id: 'exports',
        title: 'Export to Excel',
        text:
          'Pull a <strong>full report</strong>, a <strong>summary</strong>, ' +
          'or a teacher\'s <strong>schedule</strong> — the schedule export ' +
          'unlocks once you\'ve picked a single teacher above.',
        attachTo: { element: '.ts-exports', on: 'top' },
        showOn: function () { return present('.ts-exports'); },
      },
      {
        id: 'card',
        title: 'Per teacher & subject',
        text:
          'Each card rolls up one teacher × subject — <strong>budget vs ' +
          'actual</strong> time and the over/undertime variance. ' +
          '<strong>Screenshots</strong> opens their captured session ' +
          'evidence.',
        attachTo: { element: '.ts-teacher-card', on: 'top' },
        showOn: function () { return present('.ts-teacher-card'); },
      },
      {
        id: 'table',
        title: 'Day-by-day detail',
        text:
          'Inside each card, every scheduled day shows the <strong>punch ' +
          'in/out</strong>, scheduled window, hours, a Present / Late / ' +
          'Absent <strong>status</strong>, and the daily variance.',
        attachTo: { element: '.ts-table', on: 'top' },
        showOn: function () { return present('.ts-table'); },
      },
    ],
  });
})();
