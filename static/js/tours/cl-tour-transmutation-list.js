/* cl-tour-transmutation-list.js — walkthrough for the Transmutation Rules manager
 * (gradebookcomponent/templates/transmutation/transmutation-list.html).
 *
 * Map raw grade ranges to their transmuted values per grading table. Built
 * on the shared async list-table loaded into #cl-trans-wrapper. This script
 * is only included on the transmutation template, so it never registers on
 * the other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-actions       — New Rule button (always)
 *   .cl-toolbar       — search + rows-per-page (always)
 *   .cl-table         — the rules table (always)
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

  add('transmutation-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Transmutation rules',
        text:
          'Define how <strong>raw scores map to transmuted grades</strong> — ' +
          'each rule converts a range of raw values into the final grade ' +
          'for a given grading table.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Add a rule',
        text:
          '<strong>New Rule</strong> opens a form to set a raw range and the ' +
          'transmuted value it produces. Build up a full scale rule by rule.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions .cl-btn'); },
      },
      {
        id: 'search',
        title: 'Find a rule',
        text:
          '<strong>Search</strong> and set the <strong>rows per page</strong>. ' +
          'The table filters as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Your rules',
        text:
          'Each row maps a <strong>raw range</strong> to a <strong>transmuted ' +
          'value</strong> for its grading table. Fields with a dotted ' +
          'underline are editable inline.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Edit or delete',
        text:
          'The <strong>action menu</strong> on each row edits a rule or ' +
          'removes it (with a confirm — deletes can\'t be reverted).',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through rules',
        text:
          'When there are more rules than fit on one page, step through ' +
          'them here.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
