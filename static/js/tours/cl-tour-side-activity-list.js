/* cl-tour-side-activity-list.js — walkthrough for the Play & Learn list
 * (templates/student/gamification/side_activity_list.html).
 *
 * The page is a grid of mini-activity cards for one subject. Each card
 * shows the activity type, title, XP reward, estimated time, an optional
 * "completed" check, and a Play / Play Again button.
 *
 * Stable anchors:
 *   .sa-head          — page header (always)
 *   .sa-card          — first activity card (when any exist)
 *   .sa-completed     — green check on a finished activity (when any)
 *   .sa-play          — Play / Play Again button (when any card exists)
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

  add('side-activity-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Play & Learn',
        text:
          'These are bite-sized <strong>practice activities</strong> for ' +
          'this subject. Each one earns <strong>XP</strong> and helps a ' +
          'specific skill stick. Pick whatever looks fun — there\'s no ' +
          'penalty for replaying.',
        attachTo: { element: '.sa-head', on: 'bottom' },
      },
      {
        id: 'card',
        title: 'Anatomy of an activity',
        text:
          'Each card shows its <strong>type</strong> (flashcards, quiz, ' +
          'typing drill, and more), the <strong>XP reward</strong>, and a ' +
          'rough <strong>time estimate</strong> so you can pick something ' +
          'that fits the minutes you have.',
        attachTo: { element: '.sa-card', on: 'top' },
        showOn: function () { return present('.sa-card'); },
      },
      {
        id: 'completed',
        title: 'Track what you\'ve done',
        text:
          'A green check marks activities you\'ve already completed. XP is ' +
          'only awarded the <strong>first time</strong>, but replaying is ' +
          'great practice — the button reads <strong>Play Again</strong>.',
        attachTo: { element: '.sa-completed', on: 'left' },
        showOn: function () { return present('.sa-completed'); },
      },
      {
        id: 'play',
        title: 'Jump in',
        text:
          'Hit <strong>Play</strong> to start. Some activities are ' +
          'interactive mini-games, others are quick quizzes — either way ' +
          'you\'ll see your score and any XP earned at the end.',
        attachTo: { element: '.sa-play', on: 'top' },
        showOn: function () { return present('.sa-play'); },
      },
    ],
  });
})();
