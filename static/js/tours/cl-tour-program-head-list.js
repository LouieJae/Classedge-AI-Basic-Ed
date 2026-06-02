/* cl-tour-program-head-list.js — walkthrough for the Program Heads directory
 * (accounts/templates/accounts/user_list/program-head-list.html).
 *
 * Registrar/admin view of every program-head account, built on the shared
 * async list-table (includes/_list_table.html) loaded into #cl-ph-wrapper.
 * This script is only included on the program-head-list template, so it
 * never registers on the other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-toolbar       — search box + rows-per-page (always)
 *   .cl-table         — the program-head table (always)
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

  add('program-head-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Program heads',
        text:
          'The registrar\'s record of <strong>program heads</strong> — the ' +
          'people who oversee programs and departments, in one searchable ' +
          'directory.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Find a program head',
        text:
          '<strong>Search</strong> by name, ID, or email and set the ' +
          '<strong>rows per page</strong>. Results filter as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The program-head records',
        text:
          'Each row is a program head with their program and status. Fields ' +
          'with a dotted underline are <strong>editable inline</strong> — ' +
          'click to update a record on the spot.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Per-record actions',
        text:
          'The <strong>action menu</strong> opens the full profile editor ' +
          'or lets you remove the account.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through the list',
        text:
          'Step through every program head here — the header badge shows ' +
          'which records you\'re viewing.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
