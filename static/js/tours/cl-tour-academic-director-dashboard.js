/* cl-tour-academic-director-dashboard.js — walkthrough for the Academic
 * Director dashboard (templates/operations/academic_director_dashboard.html).
 *
 * A school-wide academic view: what needs a decision, headline numbers,
 * per-program performance, and the teachers driving results.
 *
 * Stable anchors:
 *   .cl-header     — greeting + role tag + as-of (always)
 *   .ad-attn       — "needs your attention" highlight (always)
 *   .ad-kpis       — KPI tile row (always)
 *   .ad-ledger     — program performance table (when any programs)
 *   .ad-feed       — top teachers feed (when any)
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

  add('academic-director-dashboard', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Academic oversight',
        text:
          'Your school-wide academic view — <strong>what needs a ' +
          'decision</strong>, how each program is performing, and the ' +
          'teachers behind the results. Quick tour?',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'attention',
        title: 'Needs your attention',
        text:
          'The priority panel surfaces decisions and issues that need a ' +
          'director\'s eye — expand a row to jump straight to the subject. ' +
          'A clear slate shows a green all-clear.',
        attachTo: { element: '.ad-attn', on: 'bottom' },
        showOn: function () { return present('.ad-attn'); },
      },
      {
        id: 'kpis',
        title: 'School-wide numbers',
        text:
          'The headline academic metrics across every program — your ' +
          'fastest read on how the institution is tracking.',
        attachTo: { element: '.ad-kpis', on: 'bottom' },
        showOn: function () { return present('.ad-kpis'); },
      },
      {
        id: 'programs',
        title: 'Program performance',
        text:
          'Each program with an <strong>active-students meter</strong> and ' +
          'totals. <strong>All programs</strong> in the header opens the ' +
          'full list; the table paginates when there are many.',
        attachTo: { element: '.ad-ledger', on: 'top' },
        showOn: function () { return present('.ad-ledger'); },
      },
      {
        id: 'teachers',
        title: 'Top teachers',
        text:
          'The teachers driving the most activity this semester, each with ' +
          'a performance meter — useful for recognition and for spotting ' +
          'who to learn from.',
        attachTo: { element: '.ad-feed', on: 'top' },
        showOn: function () { return present('.ad-feed'); },
      },
    ],
  });
})();
