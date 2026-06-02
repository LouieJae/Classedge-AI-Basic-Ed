/* cl-tour-material-list.js — walkthrough for the per-course Materials
 * & Assessments list (module/templates/material/material-list.html),
 * reached when teachers click any course card from course-list.
 *
 * The page hosts two views in one URL (toggled by the .ll-tabs row):
 *   • Materials view  (?view=lessons)    — lessons + sort/filter
 *   • Assessments view (?view=assessments) — assessment cards + status chips
 *
 * Some anchors only exist in one view. Shepherd centers steps whose
 * anchor isn't found, so the narration plays in either view.
 *
 * Stable anchors:
 *   .ll-header               — title + sub + (action row when teacher)
 *   .ll-actions              — Add material / New assessment / Import dropdown
 *   .ll-tabs                 — Materials / Assessments tab switcher
 *   .ll-filters              — Materials-view filters (search/sort/per-page)
 *   .ta-filters              — Assessments-view status chips
 *   .ta-card                 — first assessment card (only in Assessments view)
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

  add('material-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Materials &amp; Assessments',
        text:
          'This page holds every <strong>material</strong> and every ' +
          '<strong>assessment</strong> for one course. Two views sit ' +
          'behind the tabs below — switch between them depending on ' +
          'what you\'re working on.',
        attachTo: { element: '.ll-header', on: 'bottom' },
      },
      {
        id: 'tabs',
        title: 'Materials vs Assessments',
        text:
          'The tab counters show how many of each you have. ' +
          '<strong>Materials</strong> = lesson content (PDFs, videos, ' +
          'links). <strong>Assessments</strong> = quizzes, exams, ' +
          'assignments. The URL updates so the browser back button ' +
          'returns you to whichever tab you came from.',
        attachTo: { element: '.ll-tabs', on: 'bottom' },
      },
      {
        id: 'actions',
        title: 'Add or import',
        text:
          'On the Materials tab: <strong>Add material</strong> for a ' +
          'fresh upload, or <strong>Import</strong> to copy lessons from ' +
          'a previous semester or another course. On the Assessments ' +
          'tab: <strong>New assessment</strong> opens a dropdown to pick ' +
          'the type (quiz, exam, assignment, etc.).',
        attachTo: { element: '.ll-actions', on: 'bottom' },
      },
      {
        id: 'filters-materials',
        title: 'Materials filters',
        text:
          'In the Materials view: <strong>search</strong> by name or term, ' +
          'pick a <strong>sort order</strong> (newest, alphabetical, by ' +
          'date), and decide how many to show <strong>per page</strong>. ' +
          'Apply to commit.',
        attachTo: { element: '.ll-filters', on: 'top' },
      },
      {
        id: 'filters-assessments',
        title: 'Assessments status chips',
        text:
          'In the Assessments view: chip filters slice the list by ' +
          'status — <strong>Open</strong> (live now), ' +
          '<strong>Upcoming</strong> (scheduled to start), ' +
          '<strong>Closed</strong> (past their deadline), and ' +
          '<strong>Draft</strong> (not yet published).',
        attachTo: { element: '.ta-filters', on: 'top' },
      },
      {
        id: 'card',
        title: 'Cards open the detail page',
        text:
          'Each card represents one item. <strong>Color and icon match ' +
          'the type</strong> (e.g. quiz vs exam vs coding). Click ' +
          'anywhere on a card to open its details — that\'s where you ' +
          'edit, view results, or start grading.',
        attachTo: { element: '.ta-card', on: 'top' },
      },
    ],
  });
})();
