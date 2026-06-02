/* cl-tour-gradebook.js — single-page walkthrough for the Gradebook
 * setup screen (gradebookcomponent/templates/gradebook/grade-book.html).
 *
 * The page has two stacked sections sharing the same .gb-section
 * structure: Termbook (top) and Gradebook (bottom). Both render as
 * subject-grouped accordions; rows are collapsed by default so the
 * tour leans on the always-visible accordion buttons, badges, and
 * action rows for stable anchoring.
 *
 * Color code in the section badges that the tour decodes:
 *   .t-badge--forest = total = 100%   (configured correctly)
 *   .t-badge--gold   = total < 100%   (missing weight)
 *   .t-badge--rose   = total > 100%   (over-allocated)
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

  add('gradebook', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Gradebook setup',
        text:
          'Two sections stack here. <strong>Termbook</strong> at the ' +
          'top defines the academic terms and how much each one weighs ' +
          'toward the final grade. <strong>Gradebook</strong> below it ' +
          'defines what makes up each term — quizzes, assignments, ' +
          'attendance, etc. Configure each course once per semester.',
        attachTo: { element: '.gb-header', on: 'bottom' },
      },
      {
        id: 'termbook',
        title: 'Termbook — set terms and their weights',
        text:
          'Each subject gets a row per academic term (Prelim, Midterm, ' +
          'Finals, etc.). Each row has a <strong>base grade</strong> and a ' +
          '<strong>percentage</strong>. The percentages across all your ' +
          'terms should sum to <strong>100%</strong>.',
        attachTo: { element: '.gb-section:first-of-type .gb-section-head', on: 'bottom' },
      },
      {
        id: 'termbook-actions',
        title: 'Add or filter termbooks',
        text:
          'Use <strong>Add Termbook</strong> to create a new term row, ' +
          'or type in the <strong>search</strong> field to filter by ' +
          'subject or term name. Click any accordion below to see the ' +
          'rows that already exist.',
        attachTo: { element: '.gb-section:first-of-type .gb-actions', on: 'bottom' },
      },
      {
        id: 'gradebook',
        title: 'Gradebook — what makes up each grade',
        text:
          'The Gradebook section defines the <strong>components</strong> ' +
          'inside each term. A component might be "Quizzes — 30%", ' +
          '"Long Tests — 40%", "Attendance — 10%". The weights here must ' +
          'also add up to 100% per subject.',
        attachTo: { element: '.gb-section:last-of-type .gb-section-head', on: 'bottom' },
      },
      {
        id: 'total-badge',
        title: 'Decoding the total badge',
        text:
          'The badge on each subject accordion shows the math at a glance: ' +
          '<strong>forest green = 100%</strong> (configured correctly), ' +
          '<strong>gold = below 100%</strong> (you\'re missing weight), ' +
          '<strong>rose = over 100%</strong> (over-allocated). Aim for ' +
          'green on every subject.',
        attachTo: { element: '.gb-section:last-of-type .t-badge', on: 'bottom' },
      },
      {
        id: 'gradebook-actions',
        title: 'Add, copy, or configure attendance points',
        text:
          '<strong>Add Gradebook</strong> creates a fresh component row. ' +
          '<strong>Copy Gradebook</strong> duplicates an existing setup ' +
          'to a new term — useful when terms share the same structure. ' +
          '<strong>Attendance Status Points</strong> defines what each ' +
          'status (Present / Late / Absent) is worth.',
        attachTo: { element: '.gb-section:last-of-type .gb-actions', on: 'bottom' },
      },
      {
        id: 'subcategories',
        title: 'Sub-category chips',
        text:
          'When you expand a Gradebook row, each component can have ' +
          '<strong>sub-categories</strong> (chips like "Quiz · 40%", ' +
          '"Recitation · 20%") that further split the component\'s ' +
          'weight. The chips sum to 100% within each component.',
        attachTo: { element: '.gb-accordion', on: 'top' },
      },
    ],
  });
})();
