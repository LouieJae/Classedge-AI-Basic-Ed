/* cl-tour-student-calendar.js — walkthrough for the student-facing
 * month calendar (templates/student/gamification/student_calendar.html).
 *
 * One month at a time, with prev/next/today navigation. Each cell shows
 * the day number and color-coded dots representing items on that day:
 *   - deadline (assessment due)
 *   - holiday
 *   - event
 *   - announcement
 * Hovering or tapping a cell with events opens a popover with a list.
 *
 * Stable anchors:
 *   .sc-header          — page title + month name + nav
 *   .sc-nav             — prev / today / next buttons
 *   .sc-grid            — day grid container
 *   .sc-day.today       — current day cell (only when looking at current month)
 *   .sc-day.has-events  — first cell with events (only when any exist)
 *   .sc-legend          — color legend chips
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

  add('student-calendar', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your month at a glance',
        text:
          'One calendar that pulls together every <strong>deadline</strong>, ' +
          '<strong>holiday</strong>, <strong>event</strong>, and ' +
          '<strong>announcement</strong> for the month. Use it as your ' +
          'planning surface — see what\'s coming, scan for clashes, plan ' +
          'study time around it.',
        attachTo: { element: '.sc-header', on: 'bottom' },
      },
      {
        id: 'nav',
        title: 'Move between months',
        text:
          'Use <strong>&lt;</strong> and <strong>&gt;</strong> to step ' +
          'through months, or tap <strong>Today</strong> to jump straight ' +
          'back to the current month. The URL updates so you can bookmark ' +
          'a specific month if you need to.',
        attachTo: { element: '.sc-nav', on: 'bottom' },
        showOn: function () { return present('.sc-nav'); },
      },
      {
        id: 'today',
        title: 'Today is highlighted',
        text:
          'When you\'re viewing the current month, <strong>today\'s ' +
          'cell</strong> is tinted so it\'s instantly findable. As you ' +
          'navigate to other months this highlight disappears — a clear ' +
          'signal you\'re looking at a different time window.',
        attachTo: { element: '.sc-day.today', on: 'top' },
        showOn: function () { return present('.sc-day.today'); },
      },
      {
        id: 'dots',
        title: 'Color-coded dots',
        text:
          'A day with one or more items shows a <strong>dot per item</strong>, ' +
          'colored by type. <strong>Hover</strong> the cell (or ' +
          '<strong>tap</strong> on touch) to open a popover with the ' +
          'full list — each entry tells you what it is and the type.',
        attachTo: { element: '.sc-day.has-events', on: 'top' },
        showOn: function () { return present('.sc-day.has-events'); },
      },
      {
        id: 'legend',
        title: 'What the colors mean',
        text:
          'The legend at the bottom maps each <strong>dot color</strong> ' +
          'to its meaning so you can scan the grid without opening every ' +
          'cell. Red = deadline, gold = holiday, teal = event, blue = ' +
          'announcement (your school\'s palette may vary slightly).',
        attachTo: { element: '.sc-legend', on: 'top' },
        showOn: function () { return present('.sc-legend'); },
      },
    ],
  });
})();
