/* cl-tour-course-report.js — walkthrough for the Students-Per-Program report
 * (accounts/templates/accounts/reports/course_report.html).
 *
 * Enrollment headcount by program and year level for the active semester.
 * Built on the shared async list-table loaded into #cl-course-report-wrapper.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-toolbar       — search + rows-per-page (always)
 *   .cl-table         — the headcount table (always)
 *   .cl-pagination    — page navigation (when more than one page)
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

  add('course-report', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Students per program',
        text:
          'A headcount of <strong>enrollment by program and year ' +
          'level</strong> for the active semester — your quick read on how ' +
          'students are distributed across the school.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Find a program',
        text:
          '<strong>Search</strong> by program and set the <strong>rows per ' +
          'page</strong>. The table filters as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The headcounts',
        text:
          'Each row is a program with its enrollment numbers broken down by ' +
          'year level. Sort a column to rank programs by size.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'pagination',
        title: 'Page through programs',
        text:
          'When there are more programs than fit on one page, step through ' +
          'them here.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
