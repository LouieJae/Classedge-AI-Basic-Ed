/* cl-tour-student-profile.js — walkthrough for the gamified profile hub
 * (templates/student/student_profile.html).
 *
 * This page is the learner's identity + achievement hub. It also serves
 * teachers (base_operation.html) and renders for both the owner and a
 * viewer looking at someone else's profile. Owner-only controls (Edit,
 * Share, Manage Featured, per-badge Share) are gated with showOn() so
 * the tour gracefully shrinks to whatever the current viewer can see.
 *
 * Stable anchors:
 *   .profile-hero                       — hero card (always)
 *   .profile-photo-wrap                 — avatar + XP ring + level pill (always)
 *   .profile-stats                      — Total XP / Level / Badges / Streak (always)
 *   [data-bs-target="#editProfileModal"]— Edit Profile button (own only)
 *   #public-link-btn                    — Share Profile button (own only)
 *   .badges-grid                        — featured / earned badge grid
 *   #manageFeaturedBtn                  — Manage Featured (own, needs 7 earned)
 *   .badge-share-btn                    — per-badge share (own, badge has token)
 *   #toggleMoreBadges                   — Show more badges (own + has extras)
 *   .upcoming-list                      — locked "Up next" badges
 *   .info-list                          — personal info rows (always)
 *   .rec-profile-grid                   — teacher recognitions (when any)
 *   .cert-grid                          — certificates (when any)
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

  add('student-profile', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your profile hub',
        text:
          'This is your <strong>identity page</strong> — everything you\'ve ' +
          'earned in one place. Level, XP, badges, recognitions, and ' +
          'certificates all live here. Let\'s take a quick spin.',
        attachTo: { element: '.profile-hero', on: 'bottom' },
      },
      {
        id: 'avatar',
        title: 'Level & XP ring',
        text:
          'The ring around your photo fills as you earn XP toward your ' +
          'next level, and the <strong>Lv</strong> pill shows where you ' +
          'are now. The colored glow reflects your <strong>tier</strong> — ' +
          'bronze, silver, gold, platinum, or diamond.',
        attachTo: { element: '.profile-photo-wrap', on: 'right' },
        showOn: function () { return present('.profile-photo-wrap'); },
      },
      {
        id: 'stats',
        title: 'Your headline numbers',
        text:
          '<strong>Total XP</strong>, current <strong>Level</strong>, ' +
          '<strong>Badges earned</strong>, and your <strong>login ' +
          'streak</strong> — a quick pulse on your progress at a glance.',
        attachTo: { element: '.profile-stats', on: 'bottom' },
        showOn: function () { return present('.profile-stats'); },
      },
      {
        id: 'edit',
        title: 'Keep your details current',
        text:
          'Tap <strong>Edit Profile</strong> to update your photo, phone, ' +
          'and personal details. Registrar-managed fields (ID, program, ' +
          'year level) stay locked — those are set by your school.',
        attachTo: { element: '[data-bs-target="#editProfileModal"]', on: 'bottom' },
        showOn: function () { return present('[data-bs-target="#editProfileModal"]'); },
      },
      {
        id: 'share-profile',
        title: 'Share a public page',
        text:
          '<strong>Share Profile</strong> creates a read-only public link ' +
          'showing your name, level, and featured badges — no personal ' +
          'info exposed. Toggle it on, copy the link, or rotate it to ' +
          'invalidate the old one.',
        attachTo: { element: '#public-link-btn', on: 'bottom' },
        showOn: function () { return present('#public-link-btn'); },
      },
      {
        id: 'badges',
        title: 'Your badge showcase',
        text:
          'Each badge shows its <strong>icon</strong>, <strong>name</strong>, ' +
          'and a <strong>tier</strong> chip. Hover a badge to reveal its ' +
          'share button, and read how it was earned in the tooltip.',
        attachTo: { element: '.badges-grid', on: 'top' },
        showOn: function () { return present('.badges-grid'); },
      },
      {
        id: 'manage-featured',
        title: 'Curate your top 7',
        text:
          'Once you\'ve earned <strong>7 badges</strong>, <strong>Manage ' +
          'Featured</strong> lets you pick exactly which seven headline ' +
          'your profile and public page. Until then it stays locked.',
        attachTo: { element: '#manageFeaturedBtn', on: 'bottom' },
        showOn: function () { return present('#manageFeaturedBtn'); },
      },
      {
        id: 'badge-share',
        title: 'Brag a little',
        text:
          'Proud of a badge? Hit its <strong>share</strong> icon to open a ' +
          'public link with a preview card — send it to a friend, post it, ' +
          'or save it to your portfolio.',
        attachTo: { element: '.badge-share-btn', on: 'left' },
        showOn: function () { return present('.badge-share-btn'); },
      },
      {
        id: 'more-badges',
        title: 'See the full collection',
        text:
          'Featuring only seven? <strong>Show more badges</strong> expands ' +
          'the rest of what you\'ve earned without leaving the page.',
        attachTo: { element: '#toggleMoreBadges', on: 'top' },
        showOn: function () { return present('#toggleMoreBadges'); },
      },
      {
        id: 'upcoming',
        title: 'What\'s next to chase',
        text:
          'The <strong>Up next</strong> list previews locked badges you\'re ' +
          'closest to unlocking — handy targets for your next quest or ' +
          'streak.',
        attachTo: { element: '.upcoming-list', on: 'top' },
        showOn: function () { return present('.upcoming-list'); },
      },
      {
        id: 'info',
        title: 'Personal info',
        text:
          'Your contact and school details live here. Anything marked ' +
          '<em>Not set</em> can be filled in from <strong>Edit ' +
          'Profile</strong> above.',
        attachTo: { element: '.info-list', on: 'top' },
        showOn: function () { return present('.info-list'); },
      },
      {
        id: 'recognition',
        title: 'Teacher recognition',
        text:
          'When a teacher gives you a shout-out, it shows up here with ' +
          'their message and the XP it awarded — proof your effort got ' +
          'noticed.',
        attachTo: { element: '.rec-profile-grid', on: 'top' },
        showOn: function () { return present('.rec-profile-grid'); },
      },
      {
        id: 'certificates',
        title: 'Accolades & certificates',
        text:
          'Earned certificates land here. <strong>Click any card</strong> ' +
          'to open a full-size preview you can show off or screenshot.',
        attachTo: { element: '.cert-grid', on: 'top' },
        showOn: function () { return present('.cert-grid'); },
      },
    ],
  });
})();
