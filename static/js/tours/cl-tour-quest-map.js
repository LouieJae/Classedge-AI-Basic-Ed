/* cl-tour-quest-map.js — walkthrough for a single-subject gamified quest
 * journey (templates/student/gamification/quest_map.html).
 *
 * Each lesson in the subject is a "node" on an SVG path. The student
 * walks the path module by module — done nodes are checked, locked
 * nodes wait until prerequisites clear, the active node is the next
 * stop. There's a roll-up stat row, an overall progress bar, and a
 * "Continue Learning" CTA pointing at the next module.
 *
 * Stable anchors:
 *   .qm-head              — page title + back link
 *   .qm-stats             — stat tiles (total / completed / in-progress / locked)
 *   .qm-progress-bar      — overall subject progress bar
 *   .qm-svg               — SVG journey canvas with all nodes
 *   .qm-cta               — "Next Quest" call-to-action
 *   .qm-empty             — empty state (no modules)
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

  add('quest-map', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your subject quest map',
        text:
          'Every lesson in this course is a <strong>node</strong> on the ' +
          'path below. You move through them in order — finish one to ' +
          'unlock the next. Think of it as a journey through the ' +
          'semester, one stop at a time.',
        attachTo: { element: '.qm-head', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'Where you stand',
        text:
          'Four tallies at a glance: <strong>Total</strong> quests on ' +
          'this path, <strong>Completed</strong>, <strong>In Progress</strong> ' +
          '(the one you\'re actively on), and <strong>Locked</strong> — ' +
          'still waiting on a prerequisite. The mix shifts as you ' +
          'progress through the course.',
        attachTo: { element: '.qm-stats', on: 'bottom' },
        showOn: function () { return present('.qm-stats'); },
      },
      {
        id: 'progress',
        title: 'Subject progress',
        text:
          'A single percentage capturing <strong>how far through the ' +
          'subject</strong> you are. This is also what feeds your overall ' +
          'progress bar on the quest map picker.',
        attachTo: { element: '.qm-progress-bar', on: 'bottom' },
        showOn: function () { return present('.qm-progress-bar'); },
      },
      {
        id: 'map',
        title: 'The path itself',
        text:
          'Each circle is a quest. A <strong>check</strong> means done, ' +
          'a <strong>number</strong> is the order in the journey, and a ' +
          '<strong>lock</strong> means it\'s not unlocked yet. The dashed ' +
          'line traces your route from start to finish.',
        attachTo: { element: '.qm-svg', on: 'top' },
        showOn: function () { return present('.qm-svg'); },
      },
      {
        id: 'cta',
        title: 'Continue where you left off',
        text:
          'The card down here always points to your <strong>next ' +
          'quest</strong>. Tap <em>Continue Learning</em> to jump straight ' +
          'into the next lesson — no scrolling needed. Once every quest ' +
          'is complete, this card flips to a celebration message.',
        attachTo: { element: '.qm-cta', on: 'top' },
        showOn: function () { return present('.qm-cta'); },
      },
      {
        id: 'empty',
        title: 'No quests yet',
        text:
          'The quest map populates once your teacher publishes lessons ' +
          'for this course. If you see this empty state during the term, ' +
          'check with your teacher — they may still be drafting the ' +
          'syllabus.',
        attachTo: { element: '.qm-empty', on: 'top' },
        showOn: function () { return present('.qm-empty'); },
      },
    ],
  });
})();
