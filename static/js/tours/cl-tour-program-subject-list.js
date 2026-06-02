/* cl-tour-program-subject-list.js — walkthrough for the program subject browser
 * (course/templates/course/program_subject_list.html).
 *
 * A card grid of the subjects in a program (e.g. COIL), filterable by
 * semester. The template is shared (operations + student views) and the
 * copy stays role-neutral.
 *
 * Stable anchors:
 *   .program-header   — program eyebrow + title + term (always)
 *   .program-search   — search box + semester filter (always)
 *   .program-grid     — subject card grid (always)
 *   .program-card     — first subject card (when any subjects)
 *   .program-pager    — page navigation (when more than one page)
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

  add('program-subject-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Program subjects',
        text:
          'Every subject in this program, for the selected term. The ' +
          'eyebrow and title tell you which <strong>program</strong> and ' +
          '<strong>academic year</strong> you\'re viewing.',
        attachTo: { element: '.program-header', on: 'bottom' },
      },
      {
        id: 'search',
        title: 'Search & filter by term',
        text:
          '<strong>Search</strong> by subject name, code, or teacher, and ' +
          'switch <strong>semester</strong> to see a different term\'s ' +
          'offerings.',
        attachTo: { element: '.program-search', on: 'bottom' },
        showOn: function () { return present('.program-search'); },
      },
      {
        id: 'card',
        title: 'A subject at a glance',
        text:
          'Each card shows the subject\'s <strong>name</strong>, ' +
          '<strong>code</strong>, assigned teacher, enrollment count, and ' +
          'room. Click a card to open its materials.',
        attachTo: { element: '.program-card', on: 'top' },
        showOn: function () { return present('.program-card'); },
      },
      {
        id: 'pagination',
        title: 'Browse more subjects',
        text:
          'When a program has more subjects than fit on one page, page ' +
          'through them here.',
        attachTo: { element: '.program-pager', on: 'top' },
        showOn: function () { return present('.program-pager'); },
      },
    ],
  });
})();
