/* cl-tour-teacher-progress-report.js — walkthrough for the Teacher Progress Report
 * (accounts/templates/accounts/reports/teacher_progress_report.html).
 *
 * Module-completion progress for each teacher's subjects. The table
 * (#dataTable) is filled via AJAX after load.
 *
 * Stable anchors:
 *   .cl-header     — title + description (always)
 *   .cl-toolbar    — search box + teacher filter (always)
 *   .cl-table      — module-progress table (always)
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

  add('teacher-progress-report', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Teacher progress report',
        text:
          'How far each teacher\'s subjects have progressed through their ' +
          '<strong>module completion</strong> — a fast read on which ' +
          'classes are on pace and which are lagging.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'filters',
        title: 'Search & filter',
        text:
          '<strong>Search</strong> by subject or teacher, or narrow to a ' +
          'single <strong>teacher</strong> with the filter to focus on one ' +
          'person\'s load.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Progress by subject',
        text:
          'Each row pairs a subject with its teacher and a <strong>total ' +
          'progress bar</strong>. The data loads in a moment after the page ' +
          'opens.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
    ],
  });
})();
