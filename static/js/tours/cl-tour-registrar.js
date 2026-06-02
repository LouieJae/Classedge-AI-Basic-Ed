/* cl-tour-registrar.js — walkthrough for the Registrar dashboard
 * (templates/operations/registrar_dashboard.html).
 *
 * The dashboard is the records desk: what needs handling, how full the
 * term is, capacity/enrollment numbers, and the most recent transactions.
 *
 * Stable anchors:
 *   .cl-header     — greeting + role tag + as-of (always)
 *   .rg-attn       — "needs your attention" highlight (always)
 *   .rg-term       — term progress strip (when a term is active)
 *   .rg-kpis       — KPI tile row (always)
 *   .rg-mix-bar    — enrollment status mix (when enrollment activity exists)
 *   .rg-tx-list    — recent transactions feed (when any in last 7 days)
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

  add('registrar', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your records desk',
        text:
          'Everything the registrar tracks in one place — <strong>what needs ' +
          'handling</strong>, how the <strong>term</strong> is progressing, ' +
          'and the enrollments moving today. Quick tour?',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'attention',
        title: 'Needs your attention',
        text:
          'The priority panel. It surfaces <strong>over-capacity</strong> ' +
          'sections, urgent <strong>drops</strong>, and anything that needs ' +
          'a registrar decision. A clear desk shows a green all-clear.',
        attachTo: { element: '.rg-attn', on: 'bottom' },
        showOn: function () { return present('.rg-attn'); },
      },
      {
        id: 'term',
        title: 'Term clock',
        text:
          'Where you are in the current term — the <strong>week</strong>, ' +
          'the date range, and how many <strong>days are left</strong>. A ' +
          'fast read on how much runway remains before term-end.',
        attachTo: { element: '.rg-term', on: 'bottom' },
        showOn: function () { return present('.rg-term'); },
      },
      {
        id: 'kpis',
        title: 'Enrollment numbers',
        text:
          'The headline counts — <strong>active enrollments</strong>, ' +
          '<strong>new today</strong>, the trend versus the past period, and ' +
          '<strong>drops</strong>. Your daily pulse on the records desk.',
        attachTo: { element: '.rg-kpis', on: 'bottom' },
        showOn: function () { return present('.rg-kpis'); },
      },
      {
        id: 'mix',
        title: 'Enrollment mix',
        text:
          'How this semester\'s enrollments break down by ' +
          '<strong>status</strong> — enrolled, completed, dropped — as a ' +
          'proportion bar plus exact counts.',
        attachTo: { element: '.rg-mix-bar', on: 'top' },
        showOn: function () { return present('.rg-mix-bar'); },
      },
      {
        id: 'transactions',
        title: 'Recent transactions',
        text:
          'The live feed of enrollment changes from the last 7 days — who, ' +
          'which subject, the <strong>status</strong>, and when. Dropped ' +
          'records are flagged so nothing slips past you.',
        attachTo: { element: '.rg-tx-list', on: 'top' },
        showOn: function () { return present('.rg-tx-list'); },
      },
    ],
  });
})();
