/* cl-tour-update-material-url-cm.js — Classroom Mode walkthrough
 * for the Update Material (URL) form. Single page.
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

  add('update-material-url-cm', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Update linked material · Classroom Mode',
        text: 'Single page — walk through the fields, then save.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      { id: 'name', title: 'Name', text: 'Rename if needed.', attachTo: { element: '#id_file_name', on: 'bottom' } },
      { id: 'term', title: 'Term', text: 'Move to a different grading period.', attachTo: { element: '#id_term', on: 'bottom' } },
      { id: 'url', title: 'URL', text: 'Replace the link if the resource moved.', attachTo: { element: '#id_url', on: 'bottom' } },
      { id: 'description', title: 'Description', text: 'Update scope / context.', attachTo: { element: '#id_description', on: 'top' } },
      { id: 'start', title: 'Start date', text: 'When students first see it.', attachTo: { element: '#id_start_date', on: 'top' } },
      { id: 'end', title: 'End date', text: 'When it disappears. Empty = indefinite.', attachTo: { element: '#id_end_date', on: 'top' } },
      { id: 'audience', title: 'Audience', text: 'Restrict to specific students. Empty = everyone. Use Select all / Clear all to bulk-edit.', attachTo: { element: '.cm-field-head', on: 'top' } },
      {
        id: 'submit',
        title: 'Save changes',
        text: 'Click <strong>Save changes</strong>. Students see updates on their next page load.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
