/* cl-tour-coil-school-list.js — walkthrough for the Partner Schools directory
 * (coil/templates/coil/coil_school_list.html).
 *
 * The COIL school directory: every institution in the partnership pipeline
 * with its status, student reach, and per-row invite action.
 *
 * Stable anchors:
 *   .cl-header     — title + description (always)
 *   .cl-actions    — Send invite button (always)
 *   .csl-stats     — total / partners / pending / rejected stat strip (always)
 *   .csl-toolbar   — search box + status filter chips (always)
 *   #cslTable      — the school directory table (when any schools)
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

  add('coil-school-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Partner schools directory',
        text:
          'Every institution in your <strong>COIL pipeline</strong> in one ' +
          'list — track invitations, confirmed partners, and the student ' +
          'counts behind each one.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'invite',
        title: 'Invite a new school',
        text:
          '<strong>Send invite</strong> kicks off a new partnership — enter ' +
          'the school\'s details and ClassEdge emails them an invitation to ' +
          'join your COIL program.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions'); },
      },
      {
        id: 'stats',
        title: 'Pipeline at a glance',
        text:
          'Live counts across the pipeline — <strong>total</strong>, ' +
          '<strong>partners</strong>, <strong>pending</strong>, and ' +
          '<strong>rejected</strong>. A quick read on the health of your ' +
          'network.',
        attachTo: { element: '.csl-stats', on: 'bottom' },
        showOn: function () { return present('.csl-stats'); },
      },
      {
        id: 'toolbar',
        title: 'Find & filter',
        text:
          '<strong>Search</strong> by name or domain, or tap a ' +
          '<strong>status chip</strong> to narrow to partners, pending ' +
          'invites, drafts, or rejected schools.',
        attachTo: { element: '.csl-toolbar', on: 'bottom' },
        showOn: function () { return present('.csl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The directory',
        text:
          'Each row shows the school, its <strong>status</strong>, and ' +
          'student reach. Draft rows expose a <strong>Send invite</strong> ' +
          'button so you can move them forward right from the table.',
        attachTo: { element: '#cslTable', on: 'top' },
        showOn: function () { return present('#cslTable'); },
      },
    ],
  });
})();
