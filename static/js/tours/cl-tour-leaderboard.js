/* cl-tour-leaderboard.js — walkthrough for the semester XP leaderboard
 * (templates/student/gamification/leaderboard.html).
 *
 * The page presents two visual tiers:
 *   - A three-up podium for the top three (gold/silver/bronze).
 *   - A list panel for ranks 4+.
 * The current viewer's row is highlighted via .is-you so they can spot
 * themselves at a glance.
 *
 * Stable anchors:
 *   .lb-header          — page title
 *   .lb-podium          — top-3 podium row
 *   .lb-podium-card.gold-rank — first-place card (always when any rows)
 *   .lb-list-panel      — list panel for 4th onward (or the empty state)
 *   .lb-row.is-you      — your own row (only when you exist in the list)
 *   .lb-empty           — empty state
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

  add('leaderboard', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'How you stack up',
        text:
          'Rankings are by <strong>total XP this semester</strong> — XP ' +
          'comes from completing tasks, submitting assessments, and ' +
          'consistency rewards. The numbers reset each term, so a clean ' +
          'slate every semester.',
        attachTo: { element: '.lb-header', on: 'bottom' },
      },
      {
        id: 'podium',
        title: 'The top three',
        text:
          'Gold, silver, and bronze get a <strong>podium spotlight</strong>. ' +
          'Each card shows the rank, name, XP total, level, and badge ' +
          'count. If you make the top three, your card pulses to make it ' +
          'easy to find.',
        attachTo: { element: '.lb-podium', on: 'bottom' },
        showOn: function () { return present('.lb-podium'); },
      },
      {
        id: 'list',
        title: 'Everyone else',
        text:
          'Ranks <strong>4 and below</strong> live in this panel — same ' +
          'data, compact layout. Your row is highlighted so you can spot ' +
          'yourself without scrolling.',
        attachTo: { element: '.lb-list-panel', on: 'top' },
        showOn: function () { return present('.lb-list-panel') && !present('.lb-empty'); },
      },
      {
        id: 'you',
        title: 'Spot yourself',
        text:
          'Your row is <strong>tinted</strong> so it stands out. The XP ' +
          'gap between you and the rank above is your <strong>next ' +
          'climb</strong> — focus on quick wins (daily quests, badge ' +
          'milestones) to close it.',
        attachTo: { element: '.lb-row.is-you, .lb-podium-card.is-you', on: 'top' },
        showOn: function () { return present('.lb-row.is-you') || present('.lb-podium-card.is-you'); },
      },
      {
        id: 'empty',
        title: 'No rankings yet',
        text:
          'The board lights up as soon as <strong>activity gets ' +
          'logged</strong> this semester — finish a quest, submit an ' +
          'assessment, or earn a badge, and the leaderboard populates.',
        attachTo: { element: '.lb-empty', on: 'top' },
        showOn: function () { return present('.lb-empty'); },
      },
    ],
  });
})();
