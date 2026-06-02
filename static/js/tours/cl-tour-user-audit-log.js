/* cl-tour-user-audit-log.js — walkthrough for the User Audit Log
 * (templates/operations/user_audit_log.html).
 *
 * Login events and model changes captured by the audit middleware, with
 * type/action/user/search filters and pagination.
 *
 * Stable anchors:
 *   .ual-header           — title + event-count stats (always)
 *   .ual-stats            — login / CRUD / navigation totals (always)
 *   .ual-filters          — type / action / user / search filter form (always)
 *   .ual-table-wrap       — the events table (always)
 *   .ual-pagination-bar   — per-page + page navigation (always)
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

  add('user-audit-log', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'The audit trail',
        text:
          'Every <strong>login</strong> and <strong>model change</strong> ' +
          'captured by the audit middleware. This is your forensic record — ' +
          'who did what, when, and from where.',
        attachTo: { element: '.ual-header', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'Event totals',
        text:
          'A running count of <strong>login</strong>, <strong>CRUD</strong> ' +
          '(create / update / delete), and <strong>navigation</strong> ' +
          'events in the current view.',
        attachTo: { element: '.ual-stats', on: 'bottom' },
        showOn: function () { return present('.ual-stats'); },
      },
      {
        id: 'filters',
        title: 'Narrow it down',
        text:
          'Filter by <strong>type</strong>, a specific <strong>action</strong>, ' +
          'a <strong>username</strong>, or free-text search across object, ' +
          'model, and IP. Hit <strong>Apply</strong> to run the query.',
        attachTo: { element: '.ual-filters', on: 'bottom' },
        showOn: function () { return present('.ual-filters'); },
      },
      {
        id: 'table',
        title: 'The event log',
        text:
          'Each row is one event — <strong>when</strong>, the type pill, the ' +
          '<strong>user</strong>, the action, and the affected target with ' +
          'details. Hover a row to highlight it.',
        attachTo: { element: '.ual-table-wrap', on: 'top' },
        showOn: function () { return present('.ual-table-wrap'); },
      },
      {
        id: 'pagination',
        title: 'Page through history',
        text:
          'Adjust <strong>rows per page</strong> and step through the full ' +
          'history. The meta line tells you exactly which slice of events ' +
          'you\'re viewing.',
        attachTo: { element: '.ual-pagination-bar', on: 'top' },
        showOn: function () { return present('.ual-pagination-bar'); },
      },
    ],
  });
})();
