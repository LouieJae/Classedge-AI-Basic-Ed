/* cl-tour-rubric-form.js — walkthrough for the create/update Rubric form
 * (activity/templates/rubrics/_rubric_form.html — the shared partial behind
 * create-rubric.html and update-rubric.html).
 *
 * One tour serves both pages because they share this partial.
 *
 * Stable anchors:
 *   .rb-form-header   — title + description (always)
 *   .rb-form-card     — the rubric form fields (always)
 *   .rb-btn--primary  — the save button (always)
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

  function present(sel) { return !!document.querySelector(sel); }

  add('rubric-form', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Build a rubric',
        text:
          'Define <strong>reusable scoring criteria</strong> for graded ' +
          'essays and document submissions — once saved, a rubric can be ' +
          'attached wherever you grade.',
        attachTo: { element: '.rb-form-header', on: 'bottom' },
      },
      {
        id: 'fields',
        title: 'Name & criteria',
        text:
          'Give the rubric a <strong>name</strong>, link its ' +
          '<strong>course</strong>, and describe the <strong>criteria</strong> ' +
          'and point levels graders will score against.',
        attachTo: { element: '.rb-form-card', on: 'top' },
        showOn: function () { return present('.rb-form-card'); },
      },
      {
        id: 'save',
        title: 'Save the rubric',
        text:
          'Use the <strong>primary button</strong> to save, or ' +
          '<strong>Cancel</strong> to return to the rubric list without ' +
          'changes.',
        attachTo: { element: '.rb-btn--primary', on: 'top' },
        showOn: function () { return present('.rb-btn--primary'); },
      },
    ],
  });
})();
