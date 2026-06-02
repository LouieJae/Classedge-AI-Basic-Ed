/* cl-tour-super-admin.js — walkthrough for the Super Admin dashboard
 * (templates/operations/super_admin_dashboard.html).
 *
 * The dashboard answers three questions for a super admin: who has access,
 * what needs attention (security), and which privileged levers exist.
 *
 * Stable anchors:
 *   .cl-header        — greeting + role tag + as-of (always)
 *   .sa-health        — security status highlight (always)
 *   .sa-kpis          — KPI tile row (always)
 *   .sa-tools         — privileged admin tools (always)
 *   .sa-grid-main     — currently-online + users-by-role row (always)
 *   .sa-rolebar       — role breakdown bar (when any roles assigned)
 *   .sa-audit-stats   — audit activity stats (always)
 *   .sa-heatmap       — 7-day activity heatmap (always)
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

  add('super-admin', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Super admin control center',
        text:
          'This is your bird\'s-eye view of the whole system — <strong>who ' +
          'has access</strong>, <strong>what needs attention</strong>, and ' +
          'the levers only a super admin can pull. Let\'s walk through it.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'security',
        title: 'Security status',
        text:
          'The headline panel. It flags <strong>locked accounts</strong>, ' +
          '<strong>failed logins</strong>, and unexpected superusers. Green ' +
          'means all clear; amber means items need a look — each one links ' +
          'straight to the fix.',
        attachTo: { element: '.sa-health', on: 'bottom' },
        showOn: function () { return present('.sa-health'); },
      },
      {
        id: 'kpis',
        title: 'Key numbers',
        text:
          'At-a-glance counts — users <strong>online now</strong>, ' +
          '<strong>total accounts</strong>, <strong>locked</strong>, and ' +
          '<strong>new signups</strong>. Tiles that are clickable jump to a ' +
          'filtered list.',
        attachTo: { element: '.sa-kpis', on: 'bottom' },
        showOn: function () { return present('.sa-kpis'); },
      },
      {
        id: 'tools',
        title: 'Privileged tools',
        text:
          'Admin-only actions live here — role management, account tools, ' +
          'and a shortcut into Django admin. <strong>Red tiles are ' +
          'destructive</strong>, so they\'re flagged on purpose.',
        attachTo: { element: '.sa-tools', on: 'top' },
        showOn: function () { return present('.sa-tools'); },
      },
      {
        id: 'online',
        title: 'Who\'s online',
        text:
          'Live sessions right now — each row shows the person, their ' +
          'role, and when they signed in. <strong>Super</strong> and ' +
          '<strong>You</strong> tags help you spot privileged sessions.',
        attachTo: { element: '.sa-grid-main', on: 'top' },
        showOn: function () { return present('.sa-grid-main'); },
      },
      {
        id: 'roles',
        title: 'Users by role',
        text:
          'How your accounts are distributed across roles. The bar and list ' +
          'update as you assign people, and <strong>Edit roles</strong> ' +
          'takes you to the role manager.',
        attachTo: { element: '.sa-rolebar', on: 'top' },
        showOn: function () { return present('.sa-rolebar'); },
      },
      {
        id: 'audit',
        title: 'Audit activity',
        text:
          'A pulse on system activity — <strong>logins</strong>, ' +
          '<strong>model changes</strong>, and <strong>page views</strong> ' +
          'today and this week. The failed-login tile turns amber when ' +
          'something looks off.',
        attachTo: { element: '.sa-audit-stats', on: 'top' },
        showOn: function () { return present('.sa-audit-stats'); },
      },
      {
        id: 'heatmap',
        title: '7-day activity heatmap',
        text:
          'When your system is busiest, by day and hour. Darker cells mean ' +
          'more events — handy for spotting odd <strong>off-hours ' +
          'activity</strong>. Open the full log for the details.',
        attachTo: { element: '.sa-heatmap', on: 'top' },
        showOn: function () { return present('.sa-heatmap'); },
      },
    ],
  });
})();
