/* cl-tour-coil-admin.js — walkthrough for the COIL Admin dashboard
 * (templates/operations/coil_admin_dashboard.html).
 *
 * COIL = collaborative online international learning. The dashboard tracks
 * partner-school relationships: what's stuck, who needs a nudge, and how
 * the partnership pipeline is moving.
 *
 * Stable anchors:
 *   .cl-header      — greeting + role tag + as-of (always)
 *   .ca-attn        — "needs your attention" highlight (always)
 *   .ca-kpis        — KPI tile row (always)
 *   .ca-ledger      — partner-schools table (when any partners)
 *   .ca-funnel      — partnership pipeline funnel (when any partners)
 *   .ca-followup    — stale follow-up queue (when any aged 30d+)
 *   .ca-geobar      — partners-by-location spread (when any located partners)
 *   .ca-subj-list   — COIL-flagged subjects (when any flagged)
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

  add('coil-admin', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'COIL partnerships at a glance',
        text:
          'Your command center for <strong>collaborative online ' +
          'international learning</strong> — what\'s stuck, who needs a ' +
          'nudge, and how the partner pipeline is moving. Quick tour?',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'attention',
        title: 'Needs your attention',
        text:
          'The priority panel — <strong>invites to send</strong> and ' +
          '<strong>acceptances awaiting reply</strong>. A flowing pipeline ' +
          'shows a green all-clear; anything stalled surfaces here first.',
        attachTo: { element: '.ca-attn', on: 'bottom' },
        showOn: function () { return present('.ca-attn'); },
      },
      {
        id: 'kpis',
        title: 'Pipeline numbers',
        text:
          'The headline counts for your COIL program — partners, invites, ' +
          'and program activity. Toned tiles flag anything that needs ' +
          'a closer look.',
        attachTo: { element: '.ca-kpis', on: 'bottom' },
        showOn: function () { return present('.ca-kpis'); },
      },
      {
        id: 'partners',
        title: 'Partner schools',
        text:
          'Every school in your network with its <strong>status</strong>, ' +
          'location, and student reach. <strong>All schools</strong> in the ' +
          'header opens the full directory to manage them.',
        attachTo: { element: '.ca-ledger', on: 'top' },
        showOn: function () { return present('.ca-ledger'); },
      },
      {
        id: 'pipeline',
        title: 'Partnership pipeline',
        text:
          'The funnel from <strong>invite sent</strong> → <strong>pending ' +
          'acceptance</strong> → <strong>partner</strong> (and rejected). ' +
          'A fast read on where relationships sit and where they\'re ' +
          'getting stuck.',
        attachTo: { element: '.ca-funnel', on: 'top' },
        showOn: function () { return present('.ca-funnel'); },
      },
      {
        id: 'followups',
        title: 'Follow-up queue',
        text:
          'Invitations that have been <strong>waiting 30+ days</strong> for ' +
          'a reply — your nudge list. Each row links to the school so you ' +
          'can chase it down.',
        attachTo: { element: '.ca-followup', on: 'top' },
        showOn: function () { return present('.ca-followup'); },
      },
      {
        id: 'geo',
        title: 'Geographic spread',
        text:
          'Where your partners are in the world. Useful for spotting ' +
          'over-concentration and finding <strong>regions to expand</strong> ' +
          'into next.',
        attachTo: { element: '.ca-geobar', on: 'top' },
        showOn: function () { return present('.ca-geobar'); },
      },
      {
        id: 'subjects',
        title: 'COIL subjects',
        text:
          'Courses flagged as cross-border COIL, with their teacher and ' +
          'enrollment. Click through to a subject\'s materials. Flag more ' +
          'courses to surface them here.',
        attachTo: { element: '.ca-subj-list', on: 'top' },
        showOn: function () { return present('.ca-subj-list'); },
      },
    ],
  });
})();
