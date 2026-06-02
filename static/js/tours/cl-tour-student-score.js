/* cl-tour-student-score.js — walkthrough for the student post-submission
 * confirmation page (activity/templates/activity/assessments/
 * assessment-completed.html).
 *
 * This is the page a student lands on right after submitting an
 * assessment. It either shows their score (auto-graded objective tests)
 * or a "pending teacher review" notice (essays, file submissions, etc.).
 *
 * Stable anchors:
 *   .ac-card           — main confirmation card
 *   .ac-progress       — circular score ring (only when show_score)
 *   .ac-stats          — score / max / percentage row (only when show_score)
 *   .ac-pending        — "teacher will review" notice (only when !show_score)
 *   .ac-late-notice    — late penalty banner (conditional)
 *   .ac-actions        — back-to-assessments button
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

  add('student-score', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Submission received',
        text:
          'Your assessment has been <strong>submitted</strong> and ' +
          'recorded. The next sections below tell you what was scored, ' +
          'what\'s still pending, and where to go next.',
        attachTo: { element: '.ac-card', on: 'bottom' },
      },
      {
        id: 'score-ring',
        title: 'Your score at a glance',
        text:
          'This ring shows your <strong>final score</strong> against the ' +
          'maximum possible. The number in the center is the raw score; ' +
          'the percentage underneath tells you how close to full marks ' +
          'you landed.',
        attachTo: { element: '.ac-progress', on: 'bottom' },
        showOn: function () { return present('.ac-progress'); },
      },
      {
        id: 'stats',
        title: 'Score breakdown',
        text:
          '<strong>Score</strong> is the points you earned, ' +
          '<strong>Maximum</strong> is the highest possible, and ' +
          '<strong>Percentage</strong> is your raw score over the max — ' +
          'useful when comparing across assessments worth different totals.',
        attachTo: { element: '.ac-stats', on: 'top' },
        showOn: function () { return present('.ac-stats'); },
      },
      {
        id: 'pending',
        title: 'Waiting on your teacher',
        text:
          'Some assessments (essays, file uploads, written responses) ' +
          'need <strong>human review</strong> before a score is final. ' +
          'Your submission is safe — check back later, or watch your ' +
          'notifications: you\'ll be pinged when it\'s graded.',
        attachTo: { element: '.ac-pending', on: 'bottom' },
        showOn: function () { return present('.ac-pending'); },
      },
      {
        id: 'late',
        title: 'Late penalty applied',
        text:
          'You submitted past the deadline, so the percentage shown here ' +
          'was <strong>deducted</strong> from your raw score. The pre- ' +
          'penalty number is included if your teacher chose to display ' +
          'it, so you can see exactly what was taken.',
        attachTo: { element: '.ac-late-notice', on: 'bottom' },
        showOn: function () { return present('.ac-late-notice'); },
      },
      {
        id: 'back',
        title: 'Where to next',
        text:
          'Tap <strong>Back to assessments</strong> to return to this ' +
          'course\'s assessment list — see what else is open, what\'s ' +
          'due soon, or jump into the next one.',
        attachTo: { element: '.ac-actions', on: 'top' },
      },
    ],
  });
})();
