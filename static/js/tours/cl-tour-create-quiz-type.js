/* cl-tour-create-quiz-type.js — walkthrough for the bulk question
 * composer (activity/templates/activity/question/create_quiz_type.html).
 *
 * This is where teachers spend the most cumulative time per assessment.
 * The tour explains:
 *   • The question-type picker (auto-graded vs manually-graded)
 *   • The dynamic question-card list that grows as you add
 *   • The Add Question shortcut (and Ctrl+Enter)
 *   • The Progress side panel (running points + question count)
 *   • The Default Points form (set + apply-to-all)
 *   • Bulk-import CSV / Excel
 *   • The Save all questions footer
 *
 * Stable anchors:
 *   .activity-header           — page title + course/assessment sub
 *   .qc-picker-grid            — auto-graded tile group (first .qc-picker-grid)
 *   .qc-picker-grid.is-manual  — manually-graded tile group (Essay/Document)
 *   #question-cards            — dynamic card list container
 *   #add-question-btn          — Add Question button
 *   #points-side-stat          — Points progress card (when show_exact_badge)
 *   .qc-side-stat              — fallback when points stat hidden (first card)
 *   .form-side .form-card:nth-of-type(2)  — Default points form
 *   .form-side .form-card:last-of-type    — Bulk import card
 *   #saveAllQuestionsForm      — sticky footer save button
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

  add('create-quiz-type', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Add test items',
        text:
          'This is where you build the actual <strong>questions</strong> for ' +
          'this assessment. Pick a type, fill in the prompt and answer, add ' +
          'as many as you need, then save them all in one go.',
        attachTo: { element: '.activity-header', on: 'bottom' },
      },
      {
        id: 'picker',
        title: 'Pick a question type',
        text:
          'Click a tile to add a question of that type. The top group is ' +
          '<strong>auto-graded</strong> (Multiple Choice, True/False, Fill ' +
          'in the Blank, Matching, Calculated Numeric) — the system scores ' +
          'these for you.',
        attachTo: { element: '.qc-picker-grid', on: 'bottom' },
      },
      {
        id: 'manual',
        title: 'Manually-graded types',
        text:
          'The second group needs <strong>you to grade</strong> after ' +
          'submissions: <strong>Essay</strong> for written responses and ' +
          '<strong>Document Upload</strong> for file submissions. Both ' +
          'can use a rubric you attach to the assessment.',
        attachTo: { element: '.qc-picker-grid.is-manual', on: 'bottom' },
      },
      {
        id: 'cards',
        title: 'Your test items',
        text:
          'Each question shows up as a <strong>card</strong> here. Reorder, ' +
          'edit, or delete inline. Cards auto-save as you type — no need ' +
          'to hit save between questions.',
        attachTo: { element: '#question-cards', on: 'top' },
      },
      {
        id: 'add-btn',
        title: 'Add another question',
        text:
          'Click <strong>Add question</strong> to insert another of the ' +
          'same type as your last one. The keyboard shortcut ' +
          '<strong>Ctrl + Enter</strong> does the same thing — faster ' +
          'for power users.',
        attachTo: { element: '#add-question-btn', on: 'top' },
      },
      {
        id: 'progress',
        title: 'Progress tracker',
        text:
          'Watch the <strong>total points</strong> and ' +
          '<strong>question count</strong> climb as you add cards. The ' +
          'points line turns <strong>green when it hits the expected ' +
          'total</strong>, gold when under, rose when over.',
        attachTo: { element: '.form-side .form-card:first-of-type', on: 'left' },
      },
      {
        id: 'default-points',
        title: 'Default points',
        text:
          'Set a default <strong>points value</strong> applied to every ' +
          'new question you add from now on. The <strong>Apply to all</strong> ' +
          'button below it back-fills the same value into existing questions ' +
          '— useful for setting "all worth 2 points".',
        attachTo: { element: '.form-side .form-card:nth-of-type(2)', on: 'left' },
      },
      {
        id: 'bulk-import',
        title: 'Bulk import from CSV / Excel',
        text:
          'Already have questions in a spreadsheet? Click here to upload ' +
          'them in one shot. Download the template first so the column ' +
          'headers match — the modal explains the required format.',
        attachTo: { element: '.form-side .form-card:last-of-type', on: 'left' },
      },
      {
        id: 'save',
        title: 'Save all questions',
        text:
          'When all your cards look right, click <strong>Save all questions</strong> ' +
          'to commit them. Saves in one transaction — partial errors are ' +
          'reported per-card so you can fix and retry.',
        attachTo: { element: '#saveAllQuestionsForm', on: 'top' },
      },
    ],
  });
})();
