/* cl-tour-enrollment-list.js — walkthrough for the Enrolled Students view
 * (course/templates/course/subjectEnrollment/enrollment-list.html).
 *
 * Browse student enrollment by subject for a semester, with filters, an
 * expandable per-subject accordion, in-table search, and bulk actions.
 *
 * Stable anchors:
 *   .topbar            — title + semester pill (always)
 *   .enr-filters       — semester / teacher / subject / per-page filters (always)
 *   .enr-toolbar       — subject search + enroll / import actions (always)
 *   .enr-subject       — first subject group (when any subjects)
 *   .enrollment-table  — students in a subject (when any subjects)
 *   .enr-pagination    — subject page navigation (when more than one page)
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

  // True only when the element is actually rendered (has a layout box).
  // Targets inside a collapsed accordion are present in the DOM but
  // display:none — spotlighting one breaks Shepherd's overlay cutout and
  // leaves the backdrop stuck dark, so those steps must be skipped.
  function visible(sel) {
    var el = document.querySelector(sel);
    return !!(el && el.getClientRects().length);
  }

  add('enrollment-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Enrolled students',
        text:
          'Browse <strong>who\'s enrolled in what</strong>, grouped by ' +
          'subject for the active semester. The pill on the right shows ' +
          'which term you\'re viewing.',
        attachTo: { element: '.topbar', on: 'bottom' },
      },
      {
        id: 'filters',
        title: 'Filter the view',
        text:
          'Narrow by <strong>semester</strong>, <strong>teacher</strong>, or ' +
          'a single <strong>subject</strong>, and set how many subjects show ' +
          'per page. The page refreshes as you choose.',
        attachTo: { element: '.enr-filters', on: 'bottom' },
        showOn: function () { return present('.enr-filters'); },
      },
      {
        id: 'toolbar',
        title: 'Search & add students',
        text:
          '<strong>Search subjects</strong> by name. When you\'re on the ' +
          'current term, <strong>Manual enrollment</strong> and ' +
          '<strong>Import</strong> let you add students one-by-one or in ' +
          'bulk.',
        attachTo: { element: '.enr-toolbar', on: 'bottom' },
        showOn: function () { return present('.enr-toolbar'); },
      },
      {
        id: 'subject',
        title: 'A subject\'s roster',
        text:
          'Each row is a subject with its teacher and a <strong>student ' +
          'count</strong>. <strong>Click the header to expand</strong> it ' +
          'and the enrolled students appear — each with their ' +
          '<strong>status</strong> (enrolled / completed / dropped), an ' +
          'in-table search, and checkboxes for <strong>bulk actions</strong>.',
        attachTo: { element: '.enr-subject', on: 'top' },
        showOn: function () { return present('.enr-subject'); },
      },
      {
        id: 'table',
        title: 'Students & bulk actions',
        text:
          'Now that a subject is open, each student shows their ' +
          '<strong>status</strong>. Tick rows to act on several at once, ' +
          'and use the in-table search to find someone fast.',
        attachTo: { element: '.enrollment-table', on: 'top' },
        // Visibility, not presence — only show once a roster is expanded.
        showOn: function () { return visible('.enrollment-table'); },
      },
      {
        id: 'pagination',
        title: 'Page through subjects',
        text:
          'When more subjects exist than fit on one page, step through them ' +
          'here.',
        attachTo: { element: '.enr-pagination', on: 'top' },
        showOn: function () { return present('.enr-pagination'); },
      },
    ],
  });
})();
