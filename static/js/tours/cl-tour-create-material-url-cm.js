/* cl-tour-create-material-url-cm.js — Classroom Mode single-page
 * walkthrough for Create Material (URL variant).
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

  add('create-material-url-cm', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Classroom Mode — add a linked material',
        text:
          'Paste a link to a YouTube video, Google Doc, article, or any ' +
          'web-accessible resource. Single page — walk through and save.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      { id: 'name', title: 'Material name', text: 'A name students will recognize.', attachTo: { element: '#id_file_name', on: 'bottom' } },
      { id: 'term', title: 'Term', text: 'Which grading period this belongs to.', attachTo: { element: '#id_term', on: 'bottom' } },
      {
        id: 'url',
        title: 'URL',
        text: 'Paste a <strong>direct link</strong>. The platform renders a preview card for students.',
        attachTo: { element: '#id_url', on: 'bottom' },
      },
      { id: 'audience', title: 'Audience', text: 'Restrict to specific students or leave empty for everyone. Use Select all / Clear all to bulk-edit.', attachTo: { element: '.cm-field-head', on: 'top' } },
      { id: 'window', title: 'Visibility window', text: 'Start = when students first see it. End = when it disappears.', attachTo: { element: '#id_start_date', on: 'top' } },
      { id: 'description', title: 'Description', text: 'Short paragraph explaining the link\'s purpose.', attachTo: { element: '#id_description', on: 'top' } },
      {
        id: 'submit',
        title: 'Save material',
        text: 'Click <strong>Save material</strong> — it appears on the class material list immediately.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
