/* cl-tour-grade-submission.js — walkthrough for the per-submission
 * grading workspace (gradebookcomponent/templates/gradebookcomponent/
 * grade_submission.html).
 *
 * The page splits into two columns: student's answers on the left,
 * grading form on the right. The tour decodes the lesser-known
 * affordances: live percentage feedback while you type a score, the
 * quick-score 0/Half/Full buttons, the feedback snippet chips, and
 * the Save & Next keyboard shortcut that lets teachers blast through
 * a queue without touching the mouse.
 *
 * Stable anchors:
 *   .gs-header                       — title + student name
 *   .gs-meta                         — 5 context-strip cards
 *   .gs-panel--answer                — left panel (student answers)
 *   .gs-q                            — first question/answer block
 *   #gs-score                        — score input
 *   .gs-quick                        — quick-score buttons row
 *   #gs-feedback                     — feedback textarea
 *   .gs-feedback-chips               — snippet chips
 *   .gs-btn-row                      — Save + Save & Next buttons
 *   .gs-shortcuts                    — keyboard-shortcut hint
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

  add('grade-submission', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Grade a submission',
        text:
          'Two-column workspace: <strong>student\'s answers on the left</strong>, ' +
          '<strong>your grading form on the right</strong>. Score, leave ' +
          'feedback, save — or save and jump straight to the next one.',
        attachTo: { element: '.gs-header', on: 'bottom' },
      },
      {
        id: 'meta',
        title: 'Submission context',
        text:
          'Quick context for the work you\'re about to grade: ' +
          '<strong>subject</strong>, <strong>activity type</strong>, ' +
          '<strong>when</strong> it was submitted, which ' +
          '<strong>attempt</strong> this is (if retakes are allowed), ' +
          'and the maximum score available.',
        attachTo: { element: '.gs-meta', on: 'bottom' },
      },
      {
        id: 'answers',
        title: 'Student\'s answers',
        text:
          'Each question shows up as a block with the prompt and the ' +
          'student\'s response. <strong>Image attachments</strong> ' +
          'render inline; other file types appear as a clickable ' +
          'paperclip — open in a new tab to review.',
        attachTo: { element: '.gs-panel--answer', on: 'right' },
      },
      {
        id: 'score',
        title: 'Score — with live percentage',
        text:
          'Type a number out of the max. The little percentage to the ' +
          'right of the label <strong>updates live</strong> as you type ' +
          'and turns green when the score is passing or rose when failing — ' +
          'so you don\'t have to do the math.',
        attachTo: { element: '#gs-score', on: 'left' },
      },
      {
        id: 'quick-score',
        title: 'Quick-score buttons',
        text:
          'Skip the keypad when the answer is clearly all-or-nothing. ' +
          '<strong>0</strong> = none, <strong>Half</strong> = half credit, ' +
          '<strong>Full</strong> = max score. Each button shows the ' +
          'numeric value below the label so you know what it\'ll set.',
        attachTo: { element: '.gs-quick', on: 'left' },
      },
      {
        id: 'feedback',
        title: 'Feedback &amp; snippets',
        text:
          'Leave a comment for the student — it appears in their results ' +
          'view. The <strong>snippet chips</strong> below insert canned ' +
          'phrases ("Great work", "Review rubric", "Needs evidence") at ' +
          'your cursor so you can blast through routine feedback fast.',
        attachTo: { element: '#gs-feedback', on: 'left' },
      },
      {
        id: 'save',
        title: 'Save — or Save &amp; Next',
        text:
          '<strong>Save</strong> records this score and stays on the ' +
          'page. <strong>Save &amp; Next</strong> (when more work waits) ' +
          'records and jumps straight to the next ungraded submission — ' +
          'use it to plow through the queue without breaking flow.',
        attachTo: { element: '.gs-btn-row', on: 'top' },
      },
      {
        id: 'shortcuts',
        title: 'Keyboard shortcuts',
        text:
          'No need to reach for the mouse: <strong>Ctrl + Enter</strong> ' +
          'saves the current submission, and <strong>Ctrl + Shift + Enter</strong> ' +
          'saves and advances to the next one. Power-users grade entire ' +
          'queues this way.',
        attachTo: { element: '.gs-shortcuts', on: 'top' },
      },
    ],
  });
})();
