/* cl-tour-schedule-list.js — walkthrough for Schedule Management
 * (subject/templates/schedule/schedule_list.html).
 *
 * Class meeting times by subject, day, and room — registrars and admins
 * add, edit, and remove meeting blocks here.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-actions       — New Schedule button (when permitted)
 *   .cl-toolbar       — search + rows-per-page (always)
 *   .cl-table         — the schedule table (always)
 *   .cl-action-btn    — per-row action menu (when rows + permission)
 *   .pagination       — page navigation (when more than one page)
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

  add('schedule-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Schedule management',
        text:
          'Every class meeting time — <strong>by subject, day, and ' +
          'room</strong>. This is the master list of when and where ' +
          'classes meet.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'new',
        title: 'Add a meeting block',
        text:
          '<strong>New Schedule</strong> creates a meeting block — pick the ' +
          'subject, set the time and days, and assign a room and teacher.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions .cl-btn'); },
      },
      {
        id: 'search',
        title: 'Find a schedule',
        text:
          '<strong>Search</strong> by subject, teacher, room, or type, and ' +
          'set how many <strong>rows per page</strong> to show.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'The meeting blocks',
        text:
          'Each row is one meeting block — <strong>subject</strong>, ' +
          '<strong>time</strong>, <strong>days</strong>, type, room, and ' +
          'the assigned teacher.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Edit or remove',
        text:
          'The <strong>action menu</strong> on each row lets you edit a ' +
          'meeting block or delete it (with a confirmation, since it can\'t ' +
          'be undone).',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through schedules',
        text:
          'When there are more meeting blocks than fit on a page, step ' +
          'through them here.',
        attachTo: { element: '.pagination', on: 'top' },
        showOn: function () { return present('.pagination'); },
      },
    ],
  });
})();
