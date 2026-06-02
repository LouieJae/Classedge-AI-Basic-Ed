/* cl-tour-subject-roster.js — walkthrough for the per-course student
 * roster (module/templates/module/subject-student-roster.html).
 *
 * Reached from the Materials list page → student count link, or from
 * any "enrolled students" CTA on a course page. Shows every enrolled
 * student as a clickable card that opens their full account profile.
 *
 * Stable anchors:
 *   .topbar                 — page title + enrollment count + back link
 *   .roster-search          — name / email search input
 *   .roster-grid            — card grid container
 *   .roster-card            — first student card (only when students enrolled)
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

  add('subject-roster', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Course roster',
        text:
          'Every student enrolled in <strong>this course</strong>, this ' +
          'semester. The count below the title is your live enrollment ' +
          'total — useful for sanity-checking against an institutional ' +
          'roster.',
        attachTo: { element: '.topbar', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Search the roster',
        text:
          'Type any part of a student\'s <strong>name</strong> or ' +
          '<strong>email</strong> to filter the grid below. Use it when ' +
          'you have 40+ enrolled and you\'re looking for one specific ' +
          'student.',
        attachTo: { element: '.roster-search', on: 'bottom' },
      },
      {
        id: 'grid',
        title: 'Student cards',
        text:
          'Each card shows the student\'s <strong>photo</strong> (or ' +
          'initials if none uploaded), their <strong>full name</strong>, ' +
          'and <strong>email address</strong>. The cards reflow ' +
          'responsively — narrower viewports stack to fewer columns.',
        attachTo: { element: '.roster-grid', on: 'top' },
      },
      {
        id: 'open-profile',
        title: 'Click into a profile',
        text:
          'Tapping any card opens that student\'s <strong>full account ' +
          'profile</strong> — their bio, contact info, and links to ' +
          'enrolled courses. Use this for quick contact lookups or to ' +
          'verify a student you don\'t recognize.',
        attachTo: { element: '.roster-card', on: 'top' },
      },
    ],
  });
})();
