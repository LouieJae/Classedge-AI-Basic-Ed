/* cl-tour-create-material-cm.js — Classroom Mode single-page
 * walkthrough for Create Material (file upload variant).
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

  add('create-material-cm', {
    autoShow: true,
    steps: [
      {
        id: 'intro',
        title: 'Classroom Mode — add a material',
        text:
          'Streamlined for live class use. All fields fit on one screen — ' +
          'walk through them, then click <strong>Save material</strong>.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Material name',
        text: 'A descriptive name students see on their material list.',
        attachTo: { element: '#id_file_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text: 'Which grading period this belongs to.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'dropzone',
        title: 'Upload file',
        text:
          'Drag a file into this box or click to browse. ' +
          '<strong>PDF, images, video, PowerPoint, Word, Excel</strong>. ' +
          'Max <strong>30 MB</strong>.',
        attachTo: { element: '#dropzone', on: 'bottom' },
      },
      {
        id: 'audience',
        title: 'Audience',
        text:
          'Restrict to specific students, or <strong>leave empty</strong> ' +
          'to show to everyone enrolled. Use the <em>Select all</em> / ' +
          '<em>Clear all</em> buttons to bulk-edit.',
        attachTo: { element: '.cm-field-head', on: 'top' },
      },
      {
        id: 'window',
        title: 'Visibility window',
        text:
          '<strong>Start date</strong> is when students first see it. ' +
          '<strong>End date</strong> hides it — leave empty for indefinite.',
        attachTo: { element: '#id_start_date', on: 'top' },
      },
      {
        id: 'description',
        title: 'Description',
        text: 'Short paragraph explaining what students should learn from this.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Save material',
        text:
          'Click <strong>Save material</strong> — it appears on the class ' +
          'material list immediately, visible from the start date.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
      },
    ],
  });
})();
