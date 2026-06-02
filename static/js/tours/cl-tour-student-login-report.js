/* cl-tour-student-login-report.js — walkthrough for the Student Login Report
 * (accounts/templates/accounts/reports/student_login_report.html).
 *
 * Online status and last-login timestamps for every student account, built
 * on the shared async list-table loaded into #cl-student-login-wrapper.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-actions       — "active now" live badge (always)
 *   .cl-toolbar       — search + rows-per-page (always)
 *   .cl-table         — the login table (always)
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

  add('student-login-report', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Student login report',
        text:
          '<strong>Who\'s online</strong> and when each student last signed ' +
          'in — useful for spotting inactive accounts and confirming ' +
          'access issues.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'active-now',
        title: 'Live activity count',
        text:
          'This badge shows how many students are <strong>active right ' +
          'now</strong> — a real-time pulse on engagement.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions'); },
      },
      {
        id: 'search',
        title: 'Find a student',
        text:
          '<strong>Search</strong> by name or email and set the ' +
          '<strong>rows per page</strong>. The list filters as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Status & last login',
        text:
          'Each row shows a student\'s <strong>online status</strong> and ' +
          'their <strong>last-login timestamp</strong>. Sort by last login ' +
          'to surface dormant accounts.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'pagination',
        title: 'Page through students',
        text:
          'Step through every student account here when the list runs past ' +
          'one page.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
