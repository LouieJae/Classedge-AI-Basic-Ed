/* cl-tour-staff-admin-list.js — walkthrough for the Admin & Staff list
 * (accounts/templates/accounts/user_list/staff-and-admin-list.html).
 *
 * All non-teaching, non-student accounts (registrars, IT admins,
 * evaluators, etc.). The page is built on the shared async list-table
 * (includes/_list_table.html) loaded into #cl-staff-wrapper — search,
 * per-page, inline-editable cells, per-row action menu, and pagination.
 *
 * This tour script is only included on the staff/admin template, so it
 * never registers on the other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-toolbar       — search box + rows-per-page (always)
 *   .cl-table         — the accounts table (always)
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

  add('staff-admin-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Admin & staff accounts',
        text:
          'Every <strong>non-teaching, non-student</strong> account lives ' +
          'here — registrars, IT admins, evaluators, and more. This is your ' +
          'roster for the people who run the system.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Find anyone fast',
        text:
          '<strong>Search</strong> by name or email, and set how many ' +
          '<strong>rows per page</strong> you want to see. The list filters ' +
          'live as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The accounts table',
        text:
          'Each row is one account with its role and status. Fields with a ' +
          'dotted underline are <strong>editable inline</strong> — click to ' +
          'change them without leaving the page.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Per-row actions',
        text:
          'The <strong>action menu</strong> on each row lets you edit the ' +
          'full profile, reset access, or remove the account — everything ' +
          'you need to manage a single person.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through the roster',
        text:
          'When there are more accounts than fit on one page, step through ' +
          'them here. The header badge always tells you which slice you\'re ' +
          'viewing.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
