/* cl-tour-student-list.js — walkthrough for the Student Master Data directory
 * (accounts/templates/accounts/user_list/student-list.html).
 *
 * Registrar/admin view of every student account, built on the shared async
 * list-table (includes/_list_table.html) loaded into #cl-student-wrapper.
 * This script is only included on the student-list template, so it never
 * registers on the other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-toolbar       — search box + rows-per-page (always)
 *   .cl-table         — the student table (always)
 *   .cl-action-btn    — per-row action menu (when rows exist)
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

  add('student-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Student master data',
        text:
          'The registrar\'s record of <strong>every student</strong> — ' +
          'profiles, courses, year levels, and enrollments, all in one ' +
          'searchable directory.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Find a student',
        text:
          '<strong>Search</strong> by name, ID, or email, and choose how ' +
          'many <strong>rows per page</strong> to show. Results filter as ' +
          'you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The student records',
        text:
          'Each row is a student with their course, year, and status. ' +
          'Fields with a dotted underline are <strong>editable inline</strong> ' +
          '— click to correct a record on the spot.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Per-student actions',
        text:
          'The <strong>action menu</strong> opens the full profile editor, ' +
          'where you can update registrar-managed details or remove the ' +
          'account.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through the roll',
        text:
          'Step through the full student body here — the header badge tells ' +
          'you exactly which records you\'re looking at.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
