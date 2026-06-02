/* cl-tour-student-course-list.js — walkthrough for the student's
 * enrolled-courses grid (templates/student/course-list.html).
 *
 * What lives on this page:
 *   - A search field (HTMX live-filters the grid below).
 *   - A self-attendance strip (only when teacher has it on).
 *   - The course card grid — each card opens that course's
 *     material-list page.
 *   - A sidebar of "Due soon / To do / Upcoming" assessment lists.
 *
 * Stable anchors:
 *   .courses-header          — page title + semester sub
 *   .courses-search          — search input + clear button
 *   .self-attend-strip       — self-check-in row (conditional)
 *   .course-grid             — card grid container
 *   .course-card             — first card (only if enrolled)
 *   .courses-side            — sidebar with the three activity panels
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

  add('student-course-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your enrolled courses',
        text:
          'Every course you\'re enrolled in <strong>this semester</strong>. ' +
          'The semester label under the title tells you which term you\'re ' +
          'looking at — if you ever need a past term, your teacher or the ' +
          'registrar can switch it.',
        attachTo: { element: '.courses-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Filter your courses',
        text:
          'Type any part of the <strong>course name</strong>, ' +
          '<strong>code</strong>, or your <strong>teacher\'s name</strong> ' +
          'to filter the grid below. Results update as you type — no ' +
          'need to press Enter.',
        attachTo: { element: '.courses-search', on: 'bottom' },
      },
      {
        id: 'self-attend',
        title: 'Self check-in (when available)',
        text:
          'If your teacher has self-attendance turned on for a course, a ' +
          'button shows up here during scheduled class time. Tap it to ' +
          '<strong>mark yourself present</strong> — you only see this strip ' +
          'when there\'s actually a class to check in to.',
        attachTo: { element: '.self-attend-strip', on: 'bottom' },
        showOn: function () {
          var el = document.querySelector('.self-attend-strip');
          return !!el && !el.hasAttribute('hidden');
        },
      },
      {
        id: 'card',
        title: 'Course cards',
        text:
          'Each card shows the course <strong>name</strong>, your ' +
          '<strong>teacher</strong>, the <strong>room</strong>, and the ' +
          '<strong>class schedule</strong>. The pill on the top-right marks ' +
          'Lecture / Lab; a left badge appears for special programs (COIL, ' +
          'HALI, CTE). Tap a card to open the course and see materials.',
        attachTo: { element: '.course-card', on: 'top' },
      },
      {
        id: 'sidebar',
        title: 'What needs your attention',
        text:
          'The sidebar pulls together every assessment across <strong>all ' +
          'your courses</strong>: <strong>Due Soon</strong> is what\'s ' +
          'closest to its deadline, <strong>To Do</strong> is everything ' +
          'open that you haven\'t finished, and <strong>Upcoming</strong> ' +
          'is what hasn\'t opened yet. Tap any item to jump straight to it.',
        attachTo: { element: '.courses-side', on: 'left' },
      },
    ],
  });
})();
