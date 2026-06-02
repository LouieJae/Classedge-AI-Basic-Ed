/* cl-tour-create-material-embed-cm.js — Classroom Mode single-page
 * walkthrough for Create Material (Embed variant).
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

  add('create-material-embed-cm', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Classroom Mode — add an embedded material',
        text:
          'Paste iframe code from Microsoft Sway, YouTube, Genially, H5P, ' +
          'or similar. Single page — walk through and save.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      { id: 'name', title: 'Material name', text: 'A name students will recognize.', attachTo: { element: '#id_file_name', on: 'bottom' } },
      { id: 'term', title: 'Term', text: 'Which grading period this belongs to.', attachTo: { element: '#id_term', on: 'bottom' } },
      {
        id: 'iframe',
        title: 'Embed code',
        text: 'Paste the <strong>full</strong> <code>&lt;iframe&gt;</code> tag. The platform validates it before saving.',
        attachTo: { element: '#id_iframe_code', on: 'bottom' },
      },
      { id: 'audience', title: 'Audience', text: 'Restrict to specific students or leave empty for everyone. Use Select all / Clear all to bulk-edit.', attachTo: { element: '.cm-field-head', on: 'top' } },
      { id: 'window', title: 'Visibility window', text: 'Start = when students first see it. End = when it disappears.', attachTo: { element: '#id_start_date', on: 'top' } },
      { id: 'description', title: 'Description', text: 'Short paragraph explaining what the embed shows.', attachTo: { element: '#id_description', on: 'top' } },
      {
        id: 'submit',
        title: 'Save material',
        text: 'Click <strong>Save material</strong>. The embed becomes visible to students at the start date.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
