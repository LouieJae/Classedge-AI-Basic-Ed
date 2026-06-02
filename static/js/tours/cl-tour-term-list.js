/* cl-tour-term-list.js — walkthrough for the Term Catalog
 * (course/templates/course/term/term-list.html).
 *
 * Grading periods that segment a semester. Built on the shared async
 * list-table loaded into #cl-term-wrapper. This script is only included on
 * the term template, so it never registers on the other pages that share
 * the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-actions       — New Term button (when permitted)
 *   .cl-toolbar       — search box + rows-per-page (always)
 *   .cl-table         — the terms table (always)
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

  add('term-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Term catalog',
        text:
          'Define the <strong>grading periods</strong> that segment a ' +
          'semester (e.g. prelim, midterm, finals). The list defaults to ' +
          'the active semester — switch the scope filter to see all.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Add a term',
        text:
          '<strong>New Term</strong> creates a grading period inside a ' +
          'semester — name it and set its date window.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions .cl-btn'); },
      },
      {
        id: 'search',
        title: 'Find a term',
        text:
          '<strong>Search</strong> and set the <strong>rows per page</strong>. ' +
          'Use the scope filter in the toolbar to widen beyond the active ' +
          'semester.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Your terms',
        text:
          'Each row is a term with its parent semester and date window. ' +
          'Fields with a dotted underline are <strong>editable inline</strong>.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Manage a term',
        text:
          'The <strong>action menu</strong> edits the term\'s dates or ' +
          'removes it.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through terms',
        text:
          'Step through every term here when the catalog runs past one ' +
          'page.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
