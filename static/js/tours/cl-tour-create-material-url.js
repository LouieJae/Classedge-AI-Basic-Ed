/* cl-tour-create-material-url.js — per-step walkthrough for the
 * Create Material (URL) variant. Step 2 anchors to #id_url instead
 * of the dropzone.
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

  var FAMILY = 'create-material-url';

  add('create-material-url-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Add a material from a URL',
        text:
          'Four steps: <strong>Basics → Link → Schedule → Review</strong>. ' +
          'Switch to <em>File upload</em> or <em>Embed</em> using the tabs ' +
          'above if a link isn\'t the right fit.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Material name',
        text:
          'A descriptive name students will see on the material list — ' +
          'e.g. <em>"Week 3 — Khan Academy intro to loops"</em>.',
        attachTo: { element: '#id_file_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text:
          'Which grading period this belongs to. The material list is ' +
          'filtered by term so students only see the current period\'s items.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'A short paragraph explaining what\'s at the link and why ' +
          'students should follow it. Shows up next to the link card.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text: 'Click <strong>Next</strong> to paste the link.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('create-material-url-link', {
    tourFamily: FAMILY,
    formStepKey: 'link',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'url',
        title: 'Paste the URL',
        text:
          'Paste a <strong>direct link</strong> — to a YouTube video, a ' +
          'Google Doc, an article, anything web-accessible. The platform ' +
          'extracts the URL and renders a preview card for students.',
        attachTo: { element: '#id_url', on: 'bottom' },
      },
      {
        id: 'done-link',
        title: 'Step 2 done',
        text:
          'Once the link is in, click <strong>Next</strong> to set ' +
          'availability and audience.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('create-material-url-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'start-date',
        title: 'Start date',
        text:
          'When students can first see this link. Useful for releasing ' +
          'reading on a schedule.',
        attachTo: { element: '#id_start_date', on: 'bottom' },
      },
      {
        id: 'end-date',
        title: 'End date',
        text:
          'When the link disappears from students\' view. Leave empty for ' +
          'indefinite visibility.',
        attachTo: { element: '#id_end_date', on: 'bottom' },
      },
      {
        id: 'audience',
        title: 'Audience',
        text:
          'Restrict to <strong>specific students</strong>. ' +
          '<strong>Leave empty</strong> to show to every enrolled student.',
        attachTo: { element: '#id_display_lesson_for_selected_users', on: 'top' },
      },
      {
        id: 'done-schedule',
        title: 'Step 3 done',
        text: 'Click <strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('create-material-url-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'Summary of everything you entered. Click any step dot above ' +
          'to fix something — values are preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Create the material',
        text:
          'Click <strong>Create material</strong>. It appears on the ' +
          'material list immediately, visible to students from the start ' +
          'date.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
