/* cl-tour-score-sheet.js — walkthrough for the per-assessment score
 * sheet (gradebookcomponent/templates/gradebookcomponent/activityGrade/
 * score-sheet.html, opened from the assessment-details page or from
 * the teacher dashboard's "Needs grading" list).
 *
 * Stable anchors:
 *   .ss-header               — page title + back link + action buttons
 *   .ss-stats                — 6-card summary grid
 *   .ss-stat-card--gold      — Passing Score card (always the 2nd one)
 *   .ss-toolbar              — search + filter chips row
 *   .ss-search               — search input
 *   .ss-filters              — All / Passed / Failed / Pending chips
 *   .ss-table tbody .ss-row  — first student row
 *   .ss-bar                  — progress bar inside score column
 *   .ss-grade-pill           — final result pill (pass/fail/pending)
 *   .ss-header-actions       — Print + Export CSV
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

  add('score-sheet', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Score sheet',
        text:
          'Every student\'s result for <strong>this one assessment</strong>, ' +
          'all on a single screen. Sortable, searchable, and printable ' +
          'as an official record.',
        attachTo: { element: '.ss-header', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'Summary at a glance',
        text:
          'Six numbers describing the class\'s performance: ' +
          '<strong>max score</strong> on this activity, the ' +
          '<strong>passing threshold</strong>, total <strong>students</strong>, ' +
          '<strong>class average</strong>, the <strong>pass rate</strong>, ' +
          'and how many have <strong>submitted</strong> so far.',
        attachTo: { element: '.ss-stats', on: 'bottom' },
      },
      {
        id: 'search-filter',
        title: 'Search &amp; filter',
        text:
          '<strong>Search</strong> by student name or email — type and ' +
          'the table filters live. The chips on the right narrow the ' +
          'list to <strong>Passed</strong>, <strong>Failed</strong>, or ' +
          '<strong>Pending</strong> submissions only.',
        attachTo: { element: '.ss-toolbar', on: 'bottom' },
      },
      {
        id: 'row',
        title: 'A student row',
        text:
          'Each row shows the student\'s avatar + name + email, ' +
          'submission status, the timestamp they submitted (if any), ' +
          'their raw score, and the percentage / result.',
        attachTo: { element: '.ss-table tbody .ss-row', on: 'top' },
      },
      {
        id: 'bar',
        title: 'Progress bar visualization',
        text:
          'The bar fills up to the student\'s score. The marker at the ' +
          '<strong>passing threshold</strong> makes it easy to see at a ' +
          'glance whether the score cleared the bar.',
        attachTo: { element: '.ss-bar', on: 'top' },
      },
      {
        id: 'result-pill',
        title: 'Result pill — color decoded',
        text:
          'The final result pill is color-coded: ' +
          '<strong>green = passed</strong>, ' +
          '<strong>rose = failed</strong>, ' +
          '<strong>gold = pending</strong> (no submission yet). The pill ' +
          'mirrors the status badge for at-a-glance reading.',
        attachTo: { element: '.ss-grade-pill', on: 'top' },
      },
      {
        id: 'export',
        title: 'Print or export',
        text:
          'Use <strong>Print</strong> to generate an official score sheet ' +
          'with masthead, summary line, and signature blocks — ready to ' +
          'sign and file. <strong>Export CSV</strong> dumps the same data ' +
          'as a spreadsheet for further analysis.',
        attachTo: { element: '.ss-header-actions', on: 'bottom' },
      },
    ],
  });
})();
