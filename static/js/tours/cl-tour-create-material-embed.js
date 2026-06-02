/* cl-tour-create-material-embed.js — per-step walkthrough for the
 * Create Material (Embed/iframe) variant. Step 2 anchors to
 * #id_iframe_code.
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

  var FAMILY = 'create-material-embed';

  add('create-material-embed-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Add an embedded material',
        text:
          'Four steps: <strong>Basics → Embed → Schedule → Review</strong>. ' +
          'Use this if you have iframe code from <em>Microsoft Sway</em>, ' +
          '<em>YouTube</em>, <em>Genially</em>, <em>H5P</em>, or similar.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Material name',
        text: 'A name students will recognize on the material list.',
        attachTo: { element: '#id_file_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text: 'Which grading period this belongs to.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'A short paragraph explaining what the embed shows. Students ' +
          'read this before clicking into the interactive content.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text: 'Click <strong>Next</strong> to paste the embed code.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('create-material-embed-embed', {
    tourFamily: FAMILY,
    formStepKey: 'embed',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'iframe',
        title: 'Paste the iframe code',
        text:
          'Paste the <strong>full iframe code</strong> (the ' +
          '<code>&lt;iframe ...&gt;...&lt;/iframe&gt;</code> block) ' +
          'directly into this field. The platform validates it before ' +
          'saving — bad embeds get rejected at submit time.',
        attachTo: { element: '#id_iframe_code', on: 'bottom' },
      },
      {
        id: 'done-embed',
        title: 'Step 2 done',
        text:
          'Once the iframe is pasted, click <strong>Next</strong> for ' +
          'scheduling and audience.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  add('create-material-embed-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'start-date',
        title: 'Start date',
        text:
          'When students can first see this embed. Useful for releasing ' +
          'interactives on a schedule.',
        attachTo: { element: '#id_start_date', on: 'bottom' },
      },
      {
        id: 'end-date',
        title: 'End date',
        text:
          'When the embed disappears from students\' view. Leave empty ' +
          'for indefinite visibility.',
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

  add('create-material-embed-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'Summary of everything you entered. Click any step dot to fix ' +
          'something — values are preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Create the material',
        text:
          'Click <strong>Create material</strong>. The embed becomes ' +
          'visible to students at the start date you set.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
