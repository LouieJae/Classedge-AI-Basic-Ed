/* cl-tour-student-dashboard.js — walkthrough for the gamified student
 * landing page (templates/student/gamification/student_dashboard.html).
 *
 * The dashboard surfaces four things in roughly priority order:
 *   1. Hero — greeting, daily-task progress copy, login streak.
 *   2. Level / XP bar — gamified progress toward the next level.
 *   3. Today's schedule — the only "act on this now" widget.
 *   4. Quick stats / Today's tasks / Upcoming / Quick links / Badges.
 *
 * Stable anchors:
 *   .sd-hero           — greeting + streak + XP block
 *   .sd-level-pill     — current level chip (anchor for XP step)
 *   .sd-today          — today's schedule strip
 *   .sd-stats          — quick-stat row
 *   .sd-work-grid      — today's tasks + upcoming
 *   .sd-qa-strip       — quick-link tiles
 *   .sd-bottom         — badges + recognition
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

  add('student-dashboard', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Welcome to your dashboard',
        text:
          'This is your <strong>home base</strong> every time you sign in. ' +
          'It pulls together what\'s due, what\'s next, and how you\'re ' +
          'progressing — so you can decide what to work on without ' +
          'hunting through menus.',
        attachTo: { element: '.sd-hero', on: 'bottom' },
      },
      {
        id: 'streak-xp',
        title: 'Level + XP',
        text:
          'Your <strong>level</strong> climbs as you earn XP from completing ' +
          'tasks, submitting assessments, and showing up consistently. The ' +
          'bar beside it shows how close you are to your <strong>next ' +
          'level</strong>.',
        attachTo: { element: '.sd-level-row', on: 'bottom' },
      },
      {
        id: 'today',
        title: "Today's classes",
        text:
          'Every class on your <strong>schedule today</strong>, ordered by ' +
          'time. The chip on each tile tells you if a class is ' +
          '<strong>In session</strong>, <strong>Upcoming</strong>, or ' +
          '<strong>Done</strong>. Tap a tile to jump into that course.',
        attachTo: { element: '.sd-today', on: 'top' },
      },
      {
        id: 'stats',
        title: 'At-a-glance numbers',
        text:
          'Three counts you\'ll check most: <strong>today\'s task ' +
          'progress</strong>, <strong>assessments due this week</strong>, ' +
          'and <strong>badges earned</strong> out of total available. The ' +
          'cards tint amber when something needs attention.',
        attachTo: { element: '.sd-stats', on: 'top' },
      },
      {
        id: 'work',
        title: "Today's tasks & what's coming",
        text:
          'On the left, the <strong>tasks for today</strong> — tap one to ' +
          'jump straight to it and earn the listed XP. On the right, the ' +
          '<strong>next five</strong> assessments and events on your ' +
          'calendar so nothing sneaks up on you.',
        attachTo: { element: '.sd-work-grid', on: 'top' },
      },
      {
        id: 'quick-links',
        title: 'Quick shortcuts',
        text:
          'Jump straight to <strong>My courses</strong>, ' +
          '<strong>My grades</strong>, the <strong>calendar</strong>, or ' +
          'the <strong>quest map</strong>. These are the four destinations ' +
          'you\'ll hit most often.',
        attachTo: { element: '.sd-qa-strip', on: 'top' },
      },
      {
        id: 'recognition',
        title: 'Badges & recognition',
        text:
          '<strong>Recent badges</strong> shows the latest milestones ' +
          'you\'ve unlocked. <strong>Recognition</strong> on the right ' +
          'collects shout-outs your teachers have sent you — XP awards ' +
          'and personal notes both land here.',
        attachTo: { element: '.sd-bottom', on: 'top' },
      },
    ],
  });
})();
