/* cl-tour-update-material-url.js — single-page walkthrough for the
 * Update Material (URL) form. No stepper — all fields are on one page,
 * so this is one sequential tour rather than four per-step tours.
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

  add('update-material-url', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Update this linked material',
        text:
          'All settings fit on one page. Walk through the fields below, ' +
          'then click <strong>Save changes</strong> at the bottom.',
        attachTo: { element: '.lesson-header', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Material name',
        text:
          'Rename if needed — students see the new name on their next ' +
          'page load.',
        attachTo: { element: '#id_file_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text:
          'Move to a different grading period. Useful if you pulled a ' +
          'resource from a previous semester and want it under the ' +
          'current term.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'url',
        title: 'URL',
        text:
          'Replace the link if the resource moved, or paste a new URL to ' +
          'redirect students elsewhere.',
        attachTo: { element: '#id_url', on: 'bottom' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'Update the description to reflect any changes in scope or ' +
          'context.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'start-date',
        title: 'Start date',
        text:
          'When students see this link. Push it earlier to open access ' +
          'now; later to hide until that date.',
        attachTo: { element: '#id_start_date', on: 'bottom' },
      },
      {
        id: 'end-date',
        title: 'End date',
        text:
          'Deadline for visibility. Clear it to keep the link visible ' +
          'indefinitely.',
        attachTo: { element: '#id_end_date', on: 'bottom' },
      },
      {
        id: 'audience',
        title: 'Audience',
        text:
          'Restrict to specific students. <strong>Leave empty</strong> ' +
          'to show to every enrolled student.',
        attachTo: { element: '#id_display_lesson_for_selected_users', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Save changes',
        text:
          'Click <strong>Save changes</strong> when ready. Students see ' +
          'the new settings on their next page load.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
