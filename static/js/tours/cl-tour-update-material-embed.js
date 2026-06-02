/* cl-tour-update-material-embed.js — single-page walkthrough for the
 * Update Material (Embed) form.
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

  add('update-material-embed', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Update this embedded material',
        text:
          'All settings fit on one page. Walk through the fields, then ' +
          'click <strong>Save changes</strong> at the bottom.',
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
        text: 'Move to a different grading period.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'iframe',
        title: 'Iframe code',
        text:
          'Replace the embed if the original source updated — paste the ' +
          'new <code>&lt;iframe&gt;</code> code. The platform validates it ' +
          'before saving.',
        attachTo: { element: '#id_iframe_code', on: 'bottom' },
      },
      {
        id: 'description',
        title: 'Description',
        text: 'Update the description to reflect any changes in scope.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'start-date',
        title: 'Start date',
        text:
          'When students see this embed. Push it earlier or later to ' +
          'change visibility timing.',
        attachTo: { element: '#id_start_date', on: 'bottom' },
      },
      {
        id: 'end-date',
        title: 'End date',
        text:
          'Deadline for visibility. Clear it to keep the embed visible ' +
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
          'Click <strong>Save changes</strong>. Students see the new ' +
          'settings on their next page load.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
