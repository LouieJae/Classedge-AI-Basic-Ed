/* cl-tour-side-activity-play.js — walkthrough for the activity play screen
 * (templates/student/gamification/side_activity_play.html).
 *
 * The screen mounts one of ~15 mini-activity widgets (flashcards, drills,
 * quizzes, etc.) inside a single body container. JS-driven types submit
 * automatically; form-based types (e.g. practice quiz) show a Submit
 * button. The tour stays page-level since each widget's internals differ.
 *
 * Stable anchors:
 *   .sa-play-head  — activity header: type, XP, time (always)
 *   #saPlayBody    — the interactive activity container (always)
 *   .sa-submit     — Submit button (form-based types only)
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

  add('side-activity-play', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Here\'s the deal',
        text:
          'Up top you\'ll see this activity\'s <strong>type</strong>, the ' +
          '<strong>XP</strong> it\'s worth, and a rough <strong>time</strong> ' +
          'estimate. Take your time — accuracy matters more than speed.',
        attachTo: { element: '.sa-play-head', on: 'bottom' },
      },
      {
        id: 'play-area',
        title: 'Your play area',
        text:
          'Everything happens in this panel. Depending on the activity it ' +
          'might be <strong>flashcards to flip</strong>, a ' +
          '<strong>quiz to answer</strong>, a typing or matching drill, and ' +
          'more. Follow the on-screen prompts inside it.',
        attachTo: { element: '#saPlayBody', on: 'top' },
        showOn: function () { return present('#saPlayBody'); },
      },
      {
        id: 'submit',
        title: 'Submit when ready',
        text:
          'For quiz-style activities, answer every question, then press ' +
          '<strong>Submit</strong> to score it. Interactive mini-games ' +
          'finish on their own and take you straight to your results.',
        attachTo: { element: '.sa-submit', on: 'top' },
        showOn: function () { return present('.sa-submit'); },
      },
    ],
  });
})();
