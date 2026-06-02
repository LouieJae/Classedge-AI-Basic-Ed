/* cl-tour-course-list.js — single-page walkthrough for the teacher
 * "My Courses" dashboard (templates/teacher/course-list.html).
 *
 * This is the funnel-top page after teacher login. The tour explains
 * the page chrome (search, course cards, Classroom Mode button per
 * card, the Upcoming sidebar) — teaching the conventions teachers
 * will see again on downstream pages.
 *
 * Stable anchors:
 *   .courses-header       — page title + semester sub
 *   .courses-search       — HTMX live search bar
 *   .course-card          — first course card (skipped if .empty-courses)
 *   .course-classroom-btn — Start Classroom button on a card
 *   .courses-sidebar      — Upcoming items aside
 *
 * If the teacher has no courses (.empty-courses is rendered), the
 * tour gracefully degrades — Shepherd centers steps whose anchor
 * isn't found, so the narration still plays.
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

  add('course-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Welcome — these are your courses',
        text:
          'Every course you teach this semester appears here as a card. ' +
          'The subtitle above shows which semester you\'re currently ' +
          'viewing — admins can switch semesters from the sidebar.',
        attachTo: { element: '.courses-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Search as you type',
        text:
          'Type a <strong>course name, code, or room</strong>. Results ' +
          'filter live as you type — no need to hit Enter. The ' +
          '<strong>Clear</strong> button resets the filter.',
        attachTo: { element: '.courses-search', on: 'bottom' },
      },
      {
        id: 'card',
        title: 'A course card',
        text:
          'Click anywhere on the card to open that course\'s ' +
          '<strong>materials and assessments</strong>. The pill at the ' +
          'top-right of each card shows the course type (lecture, lab, etc.).',
        attachTo: { element: '.course-card', on: 'right' },
      },
      {
        id: 'classroom-btn',
        title: 'Jump into Classroom Mode',
        text:
          'The <strong>Start Classroom</strong> button on a card takes ' +
          'you straight into the live, projector-friendly view for that ' +
          'course — no need to open the course page first.',
        attachTo: { element: '.course-classroom-btn', on: 'left' },
      },
      {
        id: 'meta',
        title: 'Class info at a glance',
        text:
          'Each card shows the enrolled student count, room number, ' +
          'substitute teacher (if assigned), and the meeting schedule. ' +
          'Cards with no schedule yet show "No schedule yet" — set it ' +
          'on the course page.',
        attachTo: { element: '.course-meta', on: 'right' },
      },
      {
        id: 'sidebar',
        title: 'Upcoming items',
        text:
          'The right-hand panel rolls up upcoming lessons and ' +
          'assessments across all your courses — a quick way to see ' +
          'what\'s due this week without clicking into each course.',
        attachTo: { element: '.courses-sidebar', on: 'left' },
      },
    ],
  });
})();
