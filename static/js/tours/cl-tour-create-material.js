/* cl-tour-create-material.js — per-form-step walkthroughs for the
 * Create Material form (file upload variant). Three other variants
 * (URL, Embed) get their own configs since each has a different Step 2.
 *
 * Form structure:
 *   Step 1 (basics)   — file_name, term, description
 *   Step 2 (content)  — dropzone file picker
 *   Step 3 (schedule) — start/end dates, audience picker, allow_download
 *   Step 4 (review)   — auto-summary panel + Create button
 *
 * Anchor selectors use Django's auto-generated IDs (id_<field>) because
 * the template renders fields via {{ form.field }}.
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

  var FAMILY = 'create-material';

  // ─── Step 1: Basics ─────────────────────────────────────────────────
  add('create-material-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Welcome — let\'s add a new material',
        text:
          'This form has <strong>4 steps</strong>: Basics, Content, ' +
          'Schedule, Review. You can switch between <em>File upload</em>, ' +
          '<em>URL</em>, and <em>Embed</em> using the tabs just below the ' +
          'header — pick whichever fits the resource you\'re sharing.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'tabs',
        title: 'Material type',
        text:
          'Right now you\'re on <strong>File upload</strong>. Use ' +
          '<strong>URL</strong> for a link to an external site or video, ' +
          'and <strong>Embed</strong> if you have HTML iframe code (e.g. ' +
          'from Genially or H5P).',
        attachTo: { element: '.lesson-type-tabs', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Material name',
        text:
          'Give it a name students will recognize on the material list — ' +
          'e.g. <em>"Week 3 — Loops Practice"</em>.',
        attachTo: { element: '#id_file_name', on: 'bottom' },
      },
      {
        id: 'term',
        title: 'Term',
        text:
          'Pick the term this material belongs to. The system filters the ' +
          'material list by term, so students only see content for the ' +
          'current grading period.',
        attachTo: { element: '#id_term', on: 'bottom' },
      },
      {
        id: 'description',
        title: 'Description',
        text:
          'A short paragraph explaining <em>what the material is</em> and ' +
          '<em>why students should read it</em>. This shows up next to ' +
          'the preview so it helps students decide what to open first.',
        attachTo: { element: '#id_description', on: 'top' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text:
          'Fill these in, then click <strong>Next</strong> to upload your file.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 2: Content (file upload) ──────────────────────────────────
  add('create-material-content', {
    tourFamily: FAMILY,
    formStepKey: 'content',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'dropzone',
        title: 'Upload your file',
        text:
          'Drag a file into the dashed box, or click anywhere inside to ' +
          'browse. Supported: <strong>PDF, images, video, PowerPoint, ' +
          'Word, Excel</strong>. Max size <strong>30 MB</strong>.',
        attachTo: { element: '#dropzone', on: 'bottom' },
      },
      {
        id: 'preview',
        title: 'Preview the file',
        text:
          'Once a file is picked, you\'ll see its name and size here. ' +
          'You can swap it by dropping a new file or clicking again.',
        attachTo: { element: '#filePreview', on: 'bottom' },
      },
      {
        id: 'done-content',
        title: 'Step 2 done',
        text:
          'After your file is attached, click <strong>Next</strong> to set ' +
          'when it\'s available and who can see it.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 3: Schedule &amp; audience ────────────────────────────────
  add('create-material-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'start-date',
        title: 'Start date',
        text:
          'When students can first see this material. Useful for releasing ' +
          'content on a schedule — e.g. unlocking next week\'s reading on ' +
          'Monday morning.',
        attachTo: { element: '#id_start_date', on: 'bottom' },
      },
      {
        id: 'end-date',
        title: 'End date',
        text:
          'When the material disappears from students\' view. Leave it ' +
          'empty to keep the material visible indefinitely.',
        attachTo: { element: '#id_end_date', on: 'bottom' },
      },
      {
        id: 'audience',
        title: 'Audience',
        text:
          'Restrict this material to <strong>specific students</strong>. ' +
          'Use the <em>Select all</em> button to start with everyone, then ' +
          'remove students. <strong>Leave empty</strong> to show it to ' +
          'every enrolled student.',
        attachTo: { element: '#id_display_lesson_for_selected_users', on: 'top' },
      },
      {
        id: 'allow-download',
        title: 'Allow downloads',
        text:
          'When on, students can download the file. When off, they can ' +
          'only view it in-browser — useful for protecting copyrighted ' +
          'material or keeping students engaged in the platform.',
        attachTo: { element: '#id_allow_download', on: 'right' },
      },
      {
        id: 'done-schedule',
        title: 'Step 3 done',
        text:
          'Click <strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 4: Review &amp; submit ────────────────────────────────────
  add('create-material-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'This panel summarizes everything you entered. Spot anything ' +
          'wrong? Click any step dot above (or <strong>Back</strong>) to ' +
          'fix it — your file and field values are preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Create the material',
        text:
          'When the review looks right, click <strong>Create material</strong>. ' +
          'It\'ll appear on the material list immediately, and become ' +
          'visible to students at the start date you set.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
