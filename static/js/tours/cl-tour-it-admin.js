/* cl-tour-it-admin.js — walkthrough for the IT Admin dashboard
 * (templates/operations/it_admin_dashboard.html).
 *
 * The IT admin view is about account hygiene and access: who's online,
 * what's locked, role distribution, and the accounts moving through the
 * system (sign-ups and sign-ins).
 *
 * Stable anchors:
 *   .cl-header     — greeting + role tag + as-of (always)
 *   .it-attn       — "needs your attention" hygiene highlight (always)
 *   .it-kpis       — KPI tile row (always)
 *   .it-grid       — currently-online + users-by-role row (always)
 *   .it-rolebar    — role breakdown bar (when any active roles)
 *   #itAccounts    — recent sign-ups + latest sign-ins row (always)
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

  add('it-admin', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'IT admin dashboard',
        text:
          'Your view of <strong>account health and access</strong> — who\'s ' +
          'online, what\'s locked, and the accounts moving through the ' +
          'system. Let\'s walk through it.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'attention',
        title: 'Account hygiene',
        text:
          'The cleanup panel — it flags <strong>locked</strong>, ' +
          '<strong>role-less</strong>, and <strong>dormant</strong> ' +
          'accounts so nothing lingers unnoticed. A clean slate shows a ' +
          'green all-clear.',
        attachTo: { element: '.it-attn', on: 'bottom' },
        showOn: function () { return present('.it-attn'); },
      },
      {
        id: 'kpis',
        title: 'Access numbers',
        text:
          'Headline counts — total accounts, <strong>online now</strong>, ' +
          '<strong>locked</strong>, and <strong>new today</strong>. Your ' +
          'daily pulse on the user base.',
        attachTo: { element: '.it-kpis', on: 'bottom' },
        showOn: function () { return present('.it-kpis'); },
      },
      {
        id: 'online',
        title: 'Who\'s online',
        text:
          'Live sessions right now — person, role, and sign-in time. The ' +
          '<strong>You</strong> tag marks your own session so it\'s easy to ' +
          'spot.',
        attachTo: { element: '.it-grid', on: 'top' },
        showOn: function () { return present('.it-grid'); },
      },
      {
        id: 'roles',
        title: 'Users by role',
        text:
          'How active accounts split across roles. <strong>Manage ' +
          'roles</strong> jumps to the role manager to reassign or add ' +
          'permissions.',
        attachTo: { element: '.it-rolebar', on: 'top' },
        showOn: function () { return present('.it-rolebar'); },
      },
      {
        id: 'accounts',
        title: 'Sign-ups & sign-ins',
        text:
          'The newest <strong>accounts created</strong> and the latest ' +
          '<strong>logins</strong>. Header links take you to account ' +
          'management and the login audit for the full picture.',
        attachTo: { element: '#itAccounts', on: 'top' },
        showOn: function () { return present('#itAccounts'); },
      },
    ],
  });
})();
