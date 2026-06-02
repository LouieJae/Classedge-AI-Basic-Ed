/* cl-tour-rubric-list.js — walkthrough for the Rubrics manager
 * (activity/templates/rubrics/rubric-list.html).
 *
 * Reusable scoring criteria for essays, document submissions, and graded
 * activities. Custom .rb-* layout (not the shared list-table).
 *
 * Stable anchors:
 *   .rb-header       — title + New Rubric button (always)
 *   .rb-add-btn      — New Rubric button (when permitted)
 *   .rb-toolbar      — search box + count summary (always)
 *   .rb-table        — the rubrics table (when any rubrics)
 *   .rb-actions-btn  — per-row action menu (when rubrics exist)
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

  add('rubric-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Rubrics',
        text:
          'Reusable <strong>scoring criteria</strong> for essays, document ' +
          'submissions, and graded activities — build a rubric once and ' +
          'apply it wherever you grade.',
        attachTo: { element: '.rb-header', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Create a rubric',
        text:
          '<strong>New Rubric</strong> opens a builder where you define the ' +
          'criteria and point levels that make up the scoring guide.',
        attachTo: { element: '.rb-add-btn', on: 'bottom' },
        showOn: function () { return present('.rb-add-btn'); },
      },
      {
        id: 'search',
        title: 'Find a rubric',
        text:
          '<strong>Search</strong> by rubric name or course; the count on ' +
          'the right tells you how many you have.',
        attachTo: { element: '.rb-toolbar', on: 'bottom' },
        showOn: function () { return present('.rb-toolbar'); },
      },
      {
        id: 'table',
        title: 'Your rubrics',
        text:
          'Each row shows the <strong>course</strong>, rubric name, and a ' +
          'short description — a quick scan of every scoring guide you\'ve ' +
          'built.',
        attachTo: { element: '.rb-table', on: 'top' },
        showOn: function () { return present('.rb-table'); },
      },
      {
        id: 'actions',
        title: 'Edit or delete',
        text:
          'The <strong>action menu</strong> on each row opens the rubric to ' +
          'edit or removes it.',
        attachTo: { element: '.rb-actions-btn', on: 'left' },
        showOn: function () { return present('.rb-actions-btn'); },
      },
    ],
  });
})();
