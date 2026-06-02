/* cl-tour-teacher-dashboard.js — walkthrough for the Faculty Dashboard
 * (templates/teacher/gamification/teacher_dashboard.html).
 *
 * The page is structured as five sections from top to bottom:
 *   .dash-topbar    — greeting + today pill
 *   .today-card     — Today's schedule (per-class status cards)
 *   .quick-stats    — 4 daily-glance numbers
 *   .work-grid      — Needs grading + Closing soon (two columns)
 *   .qa-strip       — Quick action links
 *   .classes        — My Classes carousel (one card per active section)
 *
 * Each step anchors to a stable class. Shepherd falls back to a
 * centered popover for any anchor that's missing (e.g. an empty
 * schedule), so the tour gracefully degrades.
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

  add('teacher-dashboard', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Faculty dashboard',
        text:
          'A bird\'s-eye view of your teaching day. Six sections, top to ' +
          'bottom: today\'s schedule, quick stats, grading queue, ' +
          'closing-soon items, quick actions, and your classes.',
        attachTo: { element: '.dash-topbar', on: 'bottom' },
      },
      {
        id: 'today',
        title: 'Today\'s schedule',
        text:
          'Every class on your schedule for today, with a status pill — ' +
          '<strong>In session</strong>, <strong>Upcoming</strong>, or ' +
          '<strong>Done</strong>. Click any card to jump straight into ' +
          'that class\'s Classroom Mode.',
        attachTo: { element: '.today-card', on: 'bottom' },
      },
      {
        id: 'quick-stats',
        title: 'Quick stats',
        text:
          'Four numbers you\'ll check daily: total students across all ' +
          'your sections, submissions waiting on grading (highlighted ' +
          'if there are any), your overall class average, and at-risk ' +
          'students who need attention.',
        attachTo: { element: '.quick-stats', on: 'bottom' },
      },
      {
        id: 'needs-grading',
        title: 'Needs grading',
        text:
          'A live list of submissions waiting on you. Click any row to ' +
          'open the grading screen for that assessment. The count badge ' +
          'matches the <em>Needs grading</em> tile above.',
        attachTo: { element: '.work-grid .work-card:first-child', on: 'top' },
      },
      {
        id: 'closing-soon',
        title: 'Closing soon',
        text:
          'Assessments with deadlines in the <strong>next 7 days</strong>. ' +
          'Use this to spot quizzes about to expire so you can extend the ' +
          'window or remind students before they miss it.',
        attachTo: { element: '.work-grid .work-card:last-child', on: 'top' },
      },
      {
        id: 'quick-actions',
        title: 'Quick actions',
        text:
          'One-tap shortcuts to <strong>All assessments</strong>, ' +
          '<strong>My courses</strong>, <strong>Attendance</strong>, and ' +
          'the <strong>Gradebook</strong>. Use these when you know exactly ' +
          'where you want to go.',
        attachTo: { element: '.qa-strip', on: 'top' },
      },
      {
        id: 'classes',
        title: 'My classes',
        text:
          'Each card is one of your active sections this semester. The ' +
          'metrics show <strong>class average</strong>, ' +
          '<strong>ungraded count</strong>, and a <strong>material progress</strong> ' +
          'bar. Tap any card to open the class\'s analytics panel.',
        attachTo: { element: '.classes', on: 'top' },
      },
    ],
  });
})();
