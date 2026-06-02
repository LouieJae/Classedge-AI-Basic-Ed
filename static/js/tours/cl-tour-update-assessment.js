/* cl-tour-update-assessment.js — per-form-step walkthroughs for the
 * Update Assessment form. Mirrors cl-tour-create-assessment.js since
 * the form fields share IDs (#activity_name, #term, #max_retake, …)
 * and the same 4-step stepper structure.
 *
 * Differences from the create flow:
 *   • Intro copy mentions the orange "submissions exist" lock banner
 *     so editors aren't surprised when most fields are disabled.
 *   • Step 4 anchors to the same submit button; copy says "Update".
 *   • Family id is distinct ("update-assessment") so dismissal state
 *     on the create page doesn't suppress this one and vice versa.
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

  var FAMILY = 'update-assessment';

  // ─── Step 1: Basics ─────────────────────────────────────────────────
  add('update-assessment-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Update an existing assessment',
        text:
          'Same 4-step layout as creation. <strong>If students have ' +
          'already submitted</strong>, you\'ll see an orange banner above — ' +
          'and most fields will be locked. Only the <em>Schedule</em> and ' +
          '<em>late-submission</em> settings remain editable so existing ' +
          'grades stay protected.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Assessment name',
        text:
          'Rename the assessment if needed — students see the new name on ' +
          'their next page load.',
        attachTo: { element: '#activity_name', on: 'bottom' },
      },
      {
        id: 'term-lessons',
        title: 'Term &amp; lessons',
        text:
          'Move the assessment to a different term or re-link it to a ' +
          'different set of lessons. Leave Lessons empty to detach the ' +
          'assessment from any lesson.',
        attachTo: { element: '#term', on: 'bottom' },
      },
      {
        id: 'done-basics',
        title: 'Step 1 done',
        text:
          'Save your changes by progressing through the steps. Click ' +
          '<strong>Next</strong> below to move to Schedule.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 2: Schedule (per-field) ───────────────────────────────────
  add('update-assessment-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'max-retake',
        title: 'Max attempts',
        text:
          'How many tries each student gets. <strong>Reducing this number ' +
          'after submissions exist</strong> may invalidate some students\' ' +
          'attempts — increase, don\'t decrease.',
        attachTo: { element: '#max_retake', on: 'bottom' },
      },
      {
        id: 'retake-method',
        title: 'Retake method',
        text:
          'When a student has multiple attempts, which one is recorded? ' +
          'Changing this here re-applies to existing submissions on the ' +
          'next gradebook refresh.',
        attachTo: { element: '#retake_method', on: 'bottom' },
      },
      {
        id: 'time-duration',
        title: 'Time limit',
        text:
          'Per-attempt clock in minutes. Updating this only affects ' +
          '<em>new</em> attempts — students already mid-attempt keep their ' +
          'original timer.',
        attachTo: { element: '#time_duration', on: 'bottom' },
      },
      {
        id: 'passing-score',
        title: 'Passing score',
        text:
          'Minimum score considered passing. Used by the gradebook and ' +
          'class analytics to flag at-risk students.',
        attachTo: { element: '#passing_score', on: 'bottom' },
      },
      {
        id: 'passing-score-type',
        title: 'Score type',
        text:
          'Is the passing score a <strong>Percentage</strong> or a raw ' +
          '<strong>Number</strong> of points? Most teachers use Percentage.',
        attachTo: { element: '#passing_score_type', on: 'bottom' },
      },
      {
        id: 'start-time',
        title: 'Opens at',
        text:
          'When students can begin. Pushing this earlier opens the ' +
          'assessment to students sooner — useful if you announced a date ' +
          'and forgot to update the form.',
        attachTo: { element: '#start_time', on: 'top' },
      },
      {
        id: 'end-time',
        title: 'Closes at',
        text:
          'The deadline. <strong>Extending it</strong> is the most common ' +
          'reason teachers come back to this form — to give students who ' +
          'missed the deadline a second chance.',
        attachTo: { element: '#end_time', on: 'top' },
      },
      {
        id: 'done-schedule',
        title: 'Step 2 done',
        text:
          'Click <strong>Next</strong> below for Behavior toggles.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 3: Behavior (per-toggle) ──────────────────────────────────
  add('update-assessment-behavior', {
    tourFamily: FAMILY,
    formStepKey: 'behavior',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'shuffle',
        title: 'Shuffle questions',
        text:
          'Each student sees the questions in a <em>different</em> order. ' +
          'Changing this after submissions exist only affects future ' +
          'attempts.',
        attachTo: { element: '#shuffle_questions', on: 'right' },
      },
      {
        id: 'is-graded',
        title: 'Graded assessment',
        text:
          'Counts toward the gradebook. Unchecking after grades are out ' +
          'will <strong>remove</strong> this assessment from gradebook ' +
          'calculations — do this carefully.',
        attachTo: { element: '#is_graded', on: 'right' },
      },
      {
        id: 'remedial',
        title: 'Remedial',
        text:
          'Restricts this assessment to a specific group of students — ' +
          'typically those who need a retry. Toggling on reveals a student ' +
          'picker further down.',
        attachTo: { element: '#remedial', on: 'right' },
      },
      {
        id: 'allow-late',
        title: 'Allow late submission',
        text:
          'Lets students submit after the deadline within a grace window. ' +
          'This is the most common toggle teachers flip when updating an ' +
          'assessment for stragglers.',
        attachTo: { element: '#allow_late_submission', on: 'right' },
      },
      {
        id: 'done-behavior',
        title: 'Step 3 done',
        text:
          'Click <strong>Next</strong> to review and save.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 4: Review &amp; submit ────────────────────────────────────
  add('update-assessment-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Read-through',
        text:
          'This panel summarizes everything as it stands now. Spot ' +
          'anything wrong? Click any step dot above (or <strong>Back</strong>) ' +
          'to fix it — your edits are preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Save changes',
        text:
          'When the review looks right, click <strong>Update assessment</strong>. ' +
          'Students will see the new settings on their next page load — no ' +
          'need to re-publish.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
