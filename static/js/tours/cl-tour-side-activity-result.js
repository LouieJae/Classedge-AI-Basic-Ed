/* cl-tour-side-activity-result.js — walkthrough for the activity result
 * (templates/student/gamification/side_activity_result.html).
 *
 * A short celebration screen: emoji + score percentage, an XP-earned card
 * (only on first completion), and two next-step buttons.
 *
 * Stable anchors:
 *   .sa-result-score    — emoji + percentage (always)
 *   .sa-xp-earned       — "+N XP earned" card (first completion only)
 *   .sa-result-actions  — Play Again / More Activities (always)
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

  add('side-activity-result', {
    autoShow: true,
    steps: [
      {
        id: 'score',
        title: 'How you did',
        text:
          'Your <strong>score</strong> for this run. The emoji reacts to ' +
          'how you scored — but every attempt is good practice, so don\'t ' +
          'sweat a low one.',
        attachTo: { element: '.sa-result-score', on: 'bottom' },
        showOn: function () { return present('.sa-result-score'); },
      },
      {
        id: 'xp',
        title: 'XP earned',
        text:
          'The <strong>first time</strong> you complete an activity you ' +
          'pocket its XP — it counts toward your level and streak. Replays ' +
          'are free practice but won\'t award XP again.',
        attachTo: { element: '.sa-xp-earned', on: 'bottom' },
        showOn: function () { return present('.sa-xp-earned'); },
      },
      {
        id: 'actions',
        title: 'What\'s next',
        text:
          '<strong>Play Again</strong> to sharpen the same skill, or ' +
          '<strong>More Activities</strong> to head back and pick a ' +
          'different one. Keep the streak alive!',
        attachTo: { element: '.sa-result-actions', on: 'top' },
        showOn: function () { return present('.sa-result-actions'); },
      },
    ],
  });
})();
