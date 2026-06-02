/* cl-tour-create-assessment.js — per-form-step walkthroughs for the
 * Create-an-Assessment 4-step stepper form.
 *
 * Each form step owns its own walkthrough. The first ("basics") fires
 * on first visit; the rest auto-fire as the user advances the form
 * via the form's own Next button. Every walkthrough ends in a "Done"
 * button — the popover closes and the user fills the fields freely.
 *
 * Family dismissal (X button): if the user X's any walkthrough, all
 * sibling walkthroughs in this family stop auto-firing. The "Show me
 * how" button at the top of the page resets that.
 */
(function () {
  'use strict';

  // Adapter may not be loaded yet (this file lives in {% block content %}
  // which Django emits earlier than the body-end cl-tour.js). Queue
  // registrations if so; the adapter drains the queue on init.
  function add(id, config) {
    if (window.ClTour && typeof window.ClTour.register === 'function') {
      window.ClTour.register(id, config);
    } else {
      (window.__clTourPending = window.__clTourPending || []).push([id, config]);
    }
  }

  var FAMILY = 'create-assessment';

  // ─── Step 1: Basics ─────────────────────────────────────────────────
  add('create-assessment-basics', {
    autoShow: true,
    tourFamily: FAMILY,
    formStepKey: 'basics',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'intro',
        title: 'Welcome — let\'s create your first assessment',
        text:
          'This form is split into <strong>4 steps</strong>. I\'ll walk ' +
          'you through each one as you progress. The dots at the top show ' +
          'where you are — you can click any of them to jump around.',
        attachTo: { element: '.cl-stepper-head', on: 'bottom' },
      },
      {
        id: 'name',
        title: 'Name your assessment',
        text:
          'Pick something students will recognize at a glance — like ' +
          '<em>"Quiz 1 — Variables &amp; Loops"</em>. You can change it ' +
          'later.',
        attachTo: { element: '#activity_name', on: 'bottom' },
      },
      {
        id: 'term-lessons',
        title: 'Term &amp; lessons',
        text:
          '<strong>Term</strong> tells the system which grading period ' +
          'this belongs to. <strong>Lessons</strong> is optional — link ' +
          'this assessment to one or more lessons, or leave it empty for ' +
          'a standalone activity.',
        attachTo: { element: '#term', on: 'bottom' },
      },
      {
        id: 'done-basics',
        title: 'You\'re all set for Step 1',
        text:
          'Fill in the fields above, then click the <strong>Next</strong> ' +
          'button in the form footer. I\'ll meet you on Step 2 — Schedule.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 2: Schedule (per-field) ───────────────────────────────────
  add('create-assessment-schedule', {
    tourFamily: FAMILY,
    formStepKey: 'schedule',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'max-retake',
        title: 'Max attempts',
        text:
          'How many tries each student gets. Set <strong>1</strong> for a ' +
          'strict exam, <strong>2–3</strong> for a quiz, higher for a ' +
          'practice activity.',
        attachTo: { element: '#max_retake', on: 'bottom' },
      },
      {
        id: 'retake-method',
        title: 'Retake method',
        text:
          'When a student has multiple attempts, which one is recorded? ' +
          '<strong>Highest</strong> is most generous; <strong>First</strong> ' +
          'or <strong>Latest</strong> are stricter; <strong>Average</strong> ' +
          'mediates between attempts.',
        attachTo: { element: '#retake_method', on: 'bottom' },
      },
      {
        id: 'time-duration',
        title: 'Time limit',
        text:
          'Per-attempt clock in minutes. Students see this and pace ' +
          'themselves — set it conservatively. Leave high for take-home ' +
          'assessments.',
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
          'Is the passing score a <strong>Percentage</strong> of the total, ' +
          'or a raw <strong>Number</strong> of points? Most teachers use ' +
          'Percentage.',
        attachTo: { element: '#passing_score_type', on: 'bottom' },
      },
      {
        id: 'start-time',
        title: 'Opens at',
        text:
          'When students can begin. Anything before this time is blocked — ' +
          'useful for keeping a quiz hidden until class.',
        attachTo: { element: '#start_time', on: 'top' },
      },
      {
        id: 'end-time',
        title: 'Closes at',
        text:
          'The deadline. Submissions stop here — unless you turn on ' +
          '<strong>Allow late submission</strong> on the next step, which ' +
          'opens a grace window.',
        attachTo: { element: '#end_time', on: 'top' },
      },
      {
        id: 'done-schedule',
        title: 'Step 2 done',
        text:
          'Once these are filled, click <strong>Next</strong> to move to ' +
          'Step 3 — Behavior toggles.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 3: Behavior (per-toggle) ──────────────────────────────────
  add('create-assessment-behavior', {
    tourFamily: FAMILY,
    formStepKey: 'behavior',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'shuffle',
        title: 'Shuffle questions',
        text:
          'Each student sees the questions in a <em>different</em> order. ' +
          'Reduces accidental answer-sharing during in-class assessments.',
        attachTo: { element: '#shuffle_questions', on: 'right' },
      },
      {
        id: 'is-graded',
        title: 'Graded assessment',
        text:
          'Counts toward the gradebook. Uncheck for practice activities ' +
          'that <em>shouldn\'t</em> affect grades — like ungraded warm-ups ' +
          'or self-checks.',
        attachTo: { element: '#is_graded', on: 'right' },
      },
      {
        id: 'remedial',
        title: 'Remedial',
        text:
          'Assigns this assessment to <strong>specific students only</strong> — ' +
          'typically those who need a retry. Toggling this on reveals a ' +
          'student picker further down.',
        attachTo: { element: '#remedial', on: 'right' },
      },
      {
        id: 'allow-late',
        title: 'Allow late submission',
        text:
          'Lets students submit after the deadline within a grace window. ' +
          'Toggling this reveals two more fields below — how many days, ' +
          'and the penalty percentage applied to late submissions.',
        attachTo: { element: '#allow_late_submission', on: 'right' },
      },
      {
        id: 'done-behavior',
        title: 'Step 3 done',
        text:
          'Toggle whichever behaviors you need, then click ' +
          '<strong>Next</strong> for the final review.',
        attachTo: { element: '[data-cl-stepper-next]', on: 'top' },
      },
    ],
  });

  // ─── Step 4: Review &amp; submit ────────────────────────────────────
  add('create-assessment-review', {
    tourFamily: FAMILY,
    formStepKey: 'review',
    form: 'form[data-cl-stepper]',
    steps: [
      {
        id: 'review',
        title: 'Step 4 · Read-through',
        text:
          'This panel auto-summarizes everything you entered. Spot anything ' +
          'wrong? Click any step dot above (or <strong>Back</strong>) to ' +
          'fix it — your data is preserved.',
        attachTo: { element: '[data-step-review]', on: 'top' },
      },
      {
        id: 'submit',
        title: 'Create the assessment',
        text:
          'When the review looks right, click <strong>Create assessment</strong>. ' +
          'You\'ll be taken to the question editor next, where you add the ' +
          'actual questions.',
        attachTo: { element: '[data-cl-stepper-submit]', on: 'top' },
      },
    ],
  });
})();
