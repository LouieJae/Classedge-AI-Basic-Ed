/* cl-tour-badge-collection.js — walkthrough for the achievements grid
 * (templates/student/gamification/badge_collection.html).
 *
 * The page surfaces three things: the unlocked/total/completion stat
 * strip, filter chips for All / Earned / Locked, and the badge grid.
 * Earned badges expose a "Share" link (public shareable token); locked
 * badges with partial progress show a mini bar.
 *
 * Stable anchors:
 *   .bc-header            — page title + back link
 *   .bc-stats             — three-tile stat strip
 *   .bc-filters           — All / Earned / Locked chips
 *   .bc-grid              — badge card grid
 *   .bc-card              — first card (any state)
 *   .bc-card.is-locked    — locked card (only when at least one locked)
 *   .bc-share             — share link (only when an earned badge with a token)
 *   .bc-empty             — empty state
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

  add('badge-collection', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your achievement wall',
        text:
          'Every milestone you can unlock — past, present, and future. ' +
          'Badges are earned through quests, streaks, and specific ' +
          'accomplishments your school has defined. Use this page to see ' +
          'what you\'ve earned and what\'s still ahead.',
        attachTo: { element: '.bc-header', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'At-a-glance totals',
        text:
          '<strong>Unlocked</strong> is what you\'ve already earned, ' +
          '<strong>Total available</strong> is the full set, and ' +
          '<strong>Completion</strong> is your unlocked-out-of-total ' +
          'percentage with a progress bar.',
        attachTo: { element: '.bc-stats', on: 'bottom' },
        showOn: function () { return present('.bc-stats'); },
      },
      {
        id: 'filters',
        title: 'Filter the wall',
        text:
          '<strong>All</strong> shows everything. <strong>Earned</strong> ' +
          'narrows to what you\'ve unlocked — great for screenshotting ' +
          'or just savoring the wins. <strong>Locked</strong> shows what\'s ' +
          'left to chase.',
        attachTo: { element: '.bc-filters', on: 'bottom' },
        showOn: function () { return present('.bc-filters'); },
      },
      {
        id: 'card',
        title: 'A badge up close',
        text:
          'Each card has an <strong>icon</strong>, the badge ' +
          '<strong>name</strong>, a short description of how to earn it, ' +
          'and a <strong>tier</strong> chip (bronze / silver / gold). ' +
          'A check ribbon means earned; a lock ribbon means not yet.',
        attachTo: { element: '.bc-card', on: 'top' },
        showOn: function () { return present('.bc-card'); },
      },
      {
        id: 'locked-progress',
        title: 'Progress toward locked badges',
        text:
          'When you\'re <strong>partway through</strong> earning a badge ' +
          '(e.g. 3 of 5 quests done), the card shows a mini-progress bar ' +
          'with the percentage. The closer to 100%, the closer you are ' +
          'to unlocking it.',
        attachTo: { element: '.bc-card.is-locked', on: 'top' },
        showOn: function () {
          var locked = document.querySelectorAll('.bc-card.is-locked');
          for (var i = 0; i < locked.length; i++) {
            if (locked[i].querySelector('.bc-card-progress')) return true;
          }
          return false;
        },
      },
      {
        id: 'share',
        title: 'Brag a little',
        text:
          'Earned a badge you\'re proud of? Tap <strong>Share</strong> on ' +
          'the card to open a <strong>public link</strong> — send it to ' +
          'a friend, post it, save it to your portfolio. Only your ' +
          'earned badges have this link.',
        attachTo: { element: '.bc-share', on: 'top' },
        showOn: function () { return present('.bc-share'); },
      },
      {
        id: 'empty',
        title: 'No badges defined yet',
        text:
          'If this wall is empty, your school hasn\'t set up the badge ' +
          'catalog yet. They\'ll appear here as soon as definitions are ' +
          'published.',
        attachTo: { element: '.bc-empty', on: 'top' },
        showOn: function () { return present('.bc-empty'); },
      },
    ],
  });
})();
