/* cl-tour-semester-list.js — walkthrough for the Semester Catalog
 * (course/templates/course/semester/semester-list.html).
 *
 * Academic semesters that anchor terms, schedules, and enrollments. Built
 * on the shared async list-table loaded into #cl-sem-wrapper. This script
 * is only included on the semester template, so it never registers on the
 * other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-actions       — New Semester button (when permitted)
 *   .cl-toolbar       — search box + rows-per-page (always)
 *   .cl-table         — the semesters table (always)
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

  add('semester-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Semester catalog',
        text:
          'Define the <strong>academic semesters</strong> that anchor ' +
          'everything else — terms, schedules, and enrollments all hang off ' +
          'a semester.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Add a semester',
        text:
          '<strong>New Semester</strong> creates one — set its name and ' +
          'start/end dates. Once saved, you can attach terms and schedules ' +
          'to it.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions .cl-btn'); },
      },
      {
        id: 'search',
        title: 'Find a semester',
        text:
          '<strong>Search</strong> and set the <strong>rows per page</strong>. ' +
          'The catalog filters as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Your semesters',
        text:
          'Each row is a semester with its date range and status. Fields ' +
          'with a dotted underline are <strong>editable inline</strong>.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Manage a semester',
        text:
          'The <strong>action menu</strong> edits the semester\'s dates and ' +
          'settings, or removes it.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through semesters',
        text:
          'Step through every semester here when the catalog grows past one ' +
          'page.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
