/* cl-tour-quest-map-picker.js — walkthrough for the gamified entry page
 * where students choose which course's quest map to enter
 * (templates/student/gamification/quest_map_picker.html).
 *
 * Each enrolled subject is a quest line; each module is a stop on the
 * path. The picker shows per-subject progress and a roll-up overall bar.
 *
 * Stable anchors:
 *   .qp-head              — page title + back-to-dashboard
 *   .qp-banner            — intro banner + 3 stat tiles
 *   .qp-overall           — overall module progress bar
 *   .qp-grid              — subject card grid
 *   .qp-card              — first card (any state)
 *   .qp-card.done         — a mastered subject card (only when exists)
 *   .qp-empty             — no-subjects state
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

  add('quest-map-picker', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Pick a quest line',
        text:
          'Each subject you\'re enrolled in is its own <strong>quest ' +
          'line</strong>. The lessons in that course are stops along the ' +
          'path — finish them in order to unlock the next, claim XP, and ' +
          'earn badges as you go.',
        attachTo: { element: '.qp-head', on: 'bottom' },
      },
      {
        id: 'banner',
        title: 'Your overall picture',
        text:
          '<strong>Subjects</strong> is how many quest lines you have. ' +
          '<strong>Done</strong> is the total modules finished across all ' +
          'of them. <strong>Mastered</strong> counts the subjects where ' +
          'every quest is complete — a green-flag tally of subjects you\'ve ' +
          'fully cleared.',
        attachTo: { element: '.qp-banner', on: 'bottom' },
        showOn: function () { return present('.qp-banner'); },
      },
      {
        id: 'overall',
        title: 'Overall progress',
        text:
          'The combined progress across every quest line — useful for a ' +
          '<strong>single percentage</strong> of "how far through the ' +
          'semester I am". Each subject contributes proportionally.',
        attachTo: { element: '.qp-overall', on: 'bottom' },
        showOn: function () { return present('.qp-overall'); },
      },
      {
        id: 'card',
        title: 'Subject cards',
        text:
          'Each card shows the subject <strong>name</strong>, a status ' +
          'badge (<em>New</em> / <em>In Progress</em> / <em>Mastered</em>), ' +
          'and a progress bar with quest count. The CTA line tells you ' +
          'exactly how many quests remain. Tap to enter that subject\'s ' +
          'quest map.',
        attachTo: { element: '.qp-card', on: 'top' },
        showOn: function () { return present('.qp-card'); },
      },
      {
        id: 'mastered',
        title: 'Mastered subjects',
        text:
          'Cards turn gold when you\'ve cleared <strong>every quest</strong> ' +
          'in a subject. You can still revisit a mastered map to review ' +
          'completed modules — the path stays open, the trophy stays earned.',
        attachTo: { element: '.qp-card.done', on: 'top' },
        showOn: function () { return present('.qp-card.done'); },
      },
      {
        id: 'empty',
        title: 'No subjects yet',
        text:
          'Quest maps appear here once you\'re <strong>enrolled in a ' +
          'class</strong> and the teacher has set up lessons. If this ' +
          'is empty mid-semester, check with your teacher or the ' +
          'registrar.',
        attachTo: { element: '.qp-empty', on: 'top' },
        showOn: function () { return present('.qp-empty'); },
      },
    ],
  });
})();
