/* cl-tour-program-head-dashboard.js — walkthrough for the Program Head dashboard
 * (templates/operations/program_head_dashboard.html).
 *
 * Scoped to the head's own program/department: what needs attention, term
 * progress, headline numbers, today's classes, the subject roster, faculty,
 * and attendance hot-spots.
 *
 * Stable anchors:
 *   .cl-header        — greeting + role tag + as-of (always)
 *   .ph-attn          — "needs your attention" highlight (always)
 *   .ph-term          — term progress strip (when a term is active)
 *   .ph-kpis          — KPI tile row (always)
 *   .ph-sched-card    — today's class schedule (always)
 *   .ph-ledger        — department subjects table (when any subjects)
 *   .ph-grid          — faculty + attendance row (always)
 *   .ph-att-list      — lowest-attendance list (when any attendance)
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

  add('program-head-dashboard', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your department at a glance',
        text:
          'Everything here is scoped to <strong>your program</strong> — ' +
          'what needs attention, how the term is tracking, your subjects, ' +
          'faculty, and attendance. Quick tour?',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'attention',
        title: 'Needs your attention',
        text:
          'The priority panel surfaces what needs a program head\'s eye — ' +
          'expand a row to jump straight to the subject behind it. A clear ' +
          'department shows a green all-clear.',
        attachTo: { element: '.ph-attn', on: 'bottom' },
        showOn: function () { return present('.ph-attn'); },
      },
      {
        id: 'term',
        title: 'Term clock',
        text:
          'Where you are in the current term — the week, the date range, ' +
          'and how many <strong>days are left</strong> before term-end.',
        attachTo: { element: '.ph-term', on: 'bottom' },
        showOn: function () { return present('.ph-term'); },
      },
      {
        id: 'kpis',
        title: 'Department numbers',
        text:
          'Headline counts across your program — <strong>subjects</strong>, ' +
          '<strong>students</strong>, active learners, and anyone needing ' +
          'outreach this week.',
        attachTo: { element: '.ph-kpis', on: 'bottom' },
        showOn: function () { return present('.ph-kpis'); },
      },
      {
        id: 'schedule',
        title: 'Today\'s classes',
        text:
          'Your department\'s meetings for today with their status, so you ' +
          'can see what\'s <strong>live now</strong> and what\'s coming up.',
        attachTo: { element: '.ph-sched-card', on: 'top' },
        showOn: function () { return present('.ph-sched-card'); },
      },
      {
        id: 'subjects',
        title: 'Your subjects',
        text:
          'Every subject in your program with a <strong>progress ' +
          'meter</strong>. <strong>All subjects</strong> in the header opens ' +
          'the full course list.',
        attachTo: { element: '.ph-ledger', on: 'top' },
        showOn: function () { return present('.ph-ledger'); },
      },
      {
        id: 'faculty',
        title: 'Your faculty',
        text:
          'The teachers in your department and how many subjects each ' +
          'carries — a quick read on workload distribution.',
        attachTo: { element: '.ph-grid', on: 'top' },
        showOn: function () { return present('.ph-grid'); },
      },
      {
        id: 'attendance',
        title: 'Attendance hot-spots',
        text:
          'Subjects with the <strong>lowest attendance</strong> first, so ' +
          'the classes that need intervention surface to the top.',
        attachTo: { element: '.ph-att-list', on: 'top' },
        showOn: function () { return present('.ph-att-list'); },
      },
    ],
  });
})();
