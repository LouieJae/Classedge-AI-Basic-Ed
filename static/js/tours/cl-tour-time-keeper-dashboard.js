/* cl-tour-time-keeper-dashboard.js — walkthrough for the Time Keeper dashboard
 * (templates/operations/time_keeper_dashboard.html).
 *
 * Tracks the teaching day in real time — who's in class, who hasn't
 * started, today's sessions, and how the school's time is being spent.
 *
 * Stable anchors:
 *   .cl-header        — greeting + role tag + as-of (always)
 *   .tk-kpis          — KPI tile row (always)
 *   .tk-attn          — "needs your attention" highlight (always)
 *   .tk-card-head     — "Active right now" card header (always; first match)
 *   .tk-roster        — today's sessions table (when any sessions)
 *   .tk-bars          — most-hours-this-week bars (when any data)
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

  add('time-keeper-dashboard', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'The teaching day, live',
        text:
          'Track the school day in real time — <strong>who\'s in ' +
          'class</strong>, who hasn\'t started, and how the school\'s time ' +
          'is being spent. Quick tour?',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'kpis',
        title: 'Today\'s pulse',
        text:
          'The headline counts for the teaching day — sessions running, ' +
          'completed, and any that haven\'t started on time.',
        attachTo: { element: '.tk-kpis', on: 'bottom' },
        showOn: function () { return present('.tk-kpis'); },
      },
      {
        id: 'attention',
        title: 'Needs your attention',
        text:
          'Flags <strong>sessions running unusually long</strong> or ' +
          '<strong>missed start times</strong> — the things a time keeper ' +
          'chases down. A quiet day shows an all-clear.',
        attachTo: { element: '.tk-attn', on: 'bottom' },
        showOn: function () { return present('.tk-attn'); },
      },
      {
        id: 'active',
        title: 'Active right now',
        text:
          'Teachers <strong>currently in a class session</strong>, with how ' +
          'long they\'ve been live. <strong>See all sessions</strong> opens ' +
          'the full attendance list.',
        attachTo: { element: '.tk-card-head', on: 'top' },
        showOn: function () { return present('.tk-card-head'); },
      },
      {
        id: 'sessions',
        title: 'Today\'s sessions',
        text:
          'Every session so far today — teacher, time range, and ' +
          '<strong>duration</strong>. Jump to the timesheet report for the ' +
          'full breakdown.',
        attachTo: { element: '.tk-roster', on: 'top' },
        showOn: function () { return present('.tk-roster'); },
      },
      {
        id: 'hours',
        title: 'Most hours this week',
        text:
          'Who\'s logged the most teaching time this week, as a bar ' +
          'ranking — a quick read on workload across the faculty.',
        attachTo: { element: '.tk-bars', on: 'top' },
        showOn: function () { return present('.tk-bars'); },
      },
    ],
  });
})();
