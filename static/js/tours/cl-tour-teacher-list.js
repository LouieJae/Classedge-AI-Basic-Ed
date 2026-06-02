/* cl-tour-teacher-list.js — walkthrough for the Teacher Master Data directory
 * (accounts/templates/accounts/user_list/teacher-list.html).
 *
 * Registrar/admin view of every teacher account, built on the shared async
 * list-table (includes/_list_table.html) loaded into #cl-teacher-wrapper,
 * plus a CSV import action. This script is only included on the teacher-list
 * template, so it never registers on the other shared-partial pages.
 *
 * Stable anchors:
 *   .cl-header                              — title + description (always)
 *   [data-bs-target="#importTeachersModal"] — Import users button (always)
 *   .cl-toolbar                             — search box + rows-per-page (always)
 *   .cl-table                               — the teacher table (always)
 *   .cl-action-btn                          — per-row action menu (when rows exist)
 *   .cl-pagination                          — page navigation (when >1 page)
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

  add('teacher-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Teacher master data',
        text:
          'The registrar\'s record of <strong>every teacher</strong> — ' +
          'accounts, profiles, and identifiers in one searchable directory.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'import',
        title: 'Bulk-add via CSV',
        text:
          '<strong>Import users</strong> creates many teacher accounts at ' +
          'once from a CSV — there\'s a downloadable template inside, and ' +
          'existing emails are skipped automatically.',
        attachTo: { element: '[data-bs-target="#importTeachersModal"]', on: 'bottom' },
        showOn: function () { return present('[data-bs-target="#importTeachersModal"]'); },
      },
      {
        id: 'search',
        title: 'Find a teacher',
        text:
          '<strong>Search</strong> by name, ID, or email and set the ' +
          '<strong>rows per page</strong>. The list filters live as you ' +
          'type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The teacher records',
        text:
          'Each row is a teacher with their identifiers and status. Fields ' +
          'with a dotted underline are <strong>editable inline</strong> — ' +
          'click to fix a record without leaving the page.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Per-teacher actions',
        text:
          'The <strong>action menu</strong> opens the full profile editor ' +
          'or lets you remove the account.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through the faculty',
        text:
          'Step through every teacher here — the header badge shows which ' +
          'records you\'re currently viewing.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
