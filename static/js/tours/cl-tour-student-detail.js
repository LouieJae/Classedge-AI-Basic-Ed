/* cl-tour-student-detail.js — walkthrough for the per-student
 * detail page (templates/teacher/gamification/student_detail.html),
 * reached from subject-analytics by clicking a student name.
 *
 * Page structure:
 *   .sd-hero                              — avatar + name + risk pill + Recognize
 *   .sd-tiles                             — 4 KPI tiles (avg / XP / streak / risk)
 *   .sd-main .sd-card:first-child         — Activity score history table
 *   .sd-main .sd-card:nth-of-type(2)      — Module progress list
 *   .sd-main .sd-card:nth-of-type(3)      — Recognition history
 *   .sd-side .sd-card:first-child         — Risk breakdown (3 metrics)
 *   .sd-side .sd-card:nth-of-type(2)      — XP & streaks grid
 *   .sd-side .sd-card:last-child          — Badges earned
 *   .sd-btn.primary                       — Recognize button (opens modal)
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

  add('student-detail', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Student deep-dive',
        text:
          'Everything about <strong>one student in one course</strong>. ' +
          'Use this when you\'re following up on an at-risk student, ' +
          'preparing for a conference, or just deciding who to ' +
          'recognize for great work.',
        attachTo: { element: '.sd-hero', on: 'bottom' },
      },
      {
        id: 'tiles',
        title: 'Four numbers that matter',
        text:
          '<strong>Average score</strong> across this course, ' +
          '<strong>Total XP</strong> earned through activities, ' +
          '<strong>Login streak</strong> (consecutive days), and the ' +
          'overall <strong>risk level</strong> — color-tinted to ' +
          'highlight urgency.',
        attachTo: { element: '.sd-tiles', on: 'bottom' },
      },
      {
        id: 'activity-history',
        title: 'Activity score history',
        text:
          'Every assessment with the student\'s raw score, percentage ' +
          '(color-coded green/gold/rose at 75 / 50 thresholds), and ' +
          'whether they submitted <strong>on time</strong> or ' +
          '<strong>late</strong>. Pending submissions are tagged so you ' +
          'know what\'s still waiting.',
        attachTo: { element: '.sd-main .sd-card:first-child', on: 'top' },
      },
      {
        id: 'module-progress',
        title: 'Module progress',
        text:
          'How much of each lesson this student has worked through. ' +
          'Bars are color-coded: <strong>green = completed</strong>, ' +
          '<strong>gold = in progress</strong>, neutral = not started. ' +
          'Use this to spot students stuck on a specific lesson.',
        attachTo: { element: '.sd-main .sd-card:nth-of-type(2)', on: 'top' },
      },
      {
        id: 'risk-breakdown',
        title: 'Risk breakdown',
        text:
          'The risk level is computed from three weighted metrics: ' +
          '<strong>Grade score</strong> (average across activities), ' +
          '<strong>Completion</strong> (submitted vs assigned), and ' +
          '<strong>Attendance</strong>. Bars show each component — find ' +
          'the weakest one to know what to address first.',
        attachTo: { element: '.sd-side .sd-card:first-child', on: 'left' },
      },
      {
        id: 'xp-streaks',
        title: 'XP &amp; streaks',
        text:
          'Engagement signals: total XP, current level, login / ' +
          'submission / accuracy streaks, last-active date. Useful for ' +
          'spotting drop-off before grades start slipping.',
        attachTo: { element: '.sd-side .sd-card:nth-of-type(2)', on: 'left' },
      },
      {
        id: 'recognize',
        title: 'Recognize their work',
        text:
          'Click <strong>Recognize</strong> to send a custom note + an ' +
          'XP bonus. Useful both for top performers (positive ' +
          'reinforcement) and at-risk students (encouragement when they ' +
          'turn things around). The recognition history below the table ' +
          'shows everything you\'ve sent.',
        attachTo: { element: '.sd-btn.primary', on: 'left' },
      },
    ],
  });
})();
