/* cl-tour-grading-queue.js — walkthrough for the grading queue
 * (gradebookcomponent/templates/gradebookcomponent/grading_queue.html).
 *
 * This is the central inbox of submissions waiting for the teacher's
 * attention across every course they teach. The tour decodes the two
 * different "states" a submission can be in (Needs grading vs Review
 * auto-grade), explains the search/filter affordances, and points to
 * the Grade button that opens the per-submission grading screen.
 *
 * Stable anchors:
 *   .gq-header           — title + sub
 *   .gq-stats            — 4-card stats strip
 *   .gq-stat--gold       — "Needs Grading" stat
 *   .gq-stat--rose       — "Review Auto-grade" stat
 *   .gq-toolbar          — search + chip filters
 *   .gq-table            — submissions table
 *   .gq-row              — first row (when rows exist)
 *   .gq-grade-btn        — Grade button on a row
 *   .gq-filter-ctx       — visible when scoped to one activity
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

  add('grading-queue', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Grading queue',
        text:
          'Your <strong>central inbox</strong> of submissions waiting on ' +
          'your attention — across every course you teach. New entries ' +
          'appear here as students submit; cleared entries disappear ' +
          'after you grade them.',
        attachTo: { element: '.gq-header', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'Workload at a glance',
        text:
          'Four numbers: total <strong>pending</strong>, how many ' +
          '<strong>need your grading</strong> (manual), how many auto-' +
          'graded results <strong>need review</strong>, and across how ' +
          'many <strong>subjects</strong> the work spans.',
        attachTo: { element: '.gq-stats', on: 'bottom' },
      },
      {
        id: 'needs-vs-review',
        title: 'Needs grading vs Review auto-grade',
        text:
          '<strong>Needs grading</strong> (gold badge) = essay or ' +
          'document submissions waiting for you to score manually. ' +
          '<strong>Review auto-grade</strong> (rose badge) = the system ' +
          'auto-graded these but flagged them for human verification ' +
          '(e.g. an ambiguous answer).',
        attachTo: { element: '.gq-stat--gold', on: 'bottom' },
      },
      {
        id: 'search-filter',
        title: 'Search &amp; filter',
        text:
          '<strong>Search</strong> by student name, subject, or ' +
          'assessment name — the table filters live. The ' +
          '<strong>chips</strong> on the right narrow the queue to one ' +
          'status — useful when you want to plow through all your ' +
          'essay grading in one session.',
        attachTo: { element: '.gq-toolbar', on: 'bottom' },
      },
      {
        id: 'row',
        title: 'A row of the queue',
        text:
          'Each row shows the <strong>student</strong> (avatar + name), ' +
          'the <strong>assessment</strong> and its subject, the ' +
          '<strong>question type</strong> being graded, and a ' +
          '<strong>status badge</strong> matching one of the two states ' +
          'above.',
        attachTo: { element: '.gq-row', on: 'top' },
      },
      {
        id: 'grade-btn',
        title: 'Open the grading screen',
        text:
          'Click <strong>Grade</strong> to open the per-submission ' +
          'view — student answers on one side, your scoring controls ' +
          'on the other. Save and you\'ll return here with that row ' +
          'cleared from the queue.',
        attachTo: { element: '.gq-grade-btn', on: 'left' },
      },
    ],
  });
})();
