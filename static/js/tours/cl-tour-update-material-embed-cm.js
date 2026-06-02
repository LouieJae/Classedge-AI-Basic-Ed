/* cl-tour-update-material-embed-cm.js — Classroom Mode walkthrough
 * for the Update Material (Embed) form. Single page.
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

  add('update-material-embed-cm', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Update embedded material · Classroom Mode',
        text: 'Single page — walk through and save.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      { id: 'name', title: 'Name', text: 'Rename if needed.', attachTo: { element: '#id_file_name', on: 'bottom' } },
      { id: 'term', title: 'Term', text: 'Move to a different grading period.', attachTo: { element: '#id_term', on: 'bottom' } },
      {
        id: 'iframe',
        title: 'Embed code',
        text: 'Replace the embed if the source updated. Paste the full <code>&lt;iframe&gt;</code> tag.',
        attachTo: { element: '#id_iframe_code', on: 'bottom' },
      },
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
