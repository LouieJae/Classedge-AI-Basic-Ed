/* cl-tour-semester-form.js — walkthrough for the create/update Semester form
 * (course/templates/course/semester/create-semester.html + update-semester.html).
 *
 * Both pages share the cl-form-card structure, so one tour serves both. The
 * autosave step only appears on the create page (it carries data-cl-autosave).
 *
 * Stable anchors:
 *   .cl-header          — title + description (always)
 *   .cl-form-section    — the field group (always)
 *   [data-cl-autosave]  — the form, only when draft-autosave is on (create)
 *   .cl-form-actions    — submit + cancel buttons (always)
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

  add('semester-form', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Set up a semester',
        text:
          'A semester\'s <strong>start and end dates</strong> anchor every ' +
          'term and enrollment inside it — so getting these right matters ' +
          'for everything downstream.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'fields',
        title: 'Fill in the details',
        text:
          'Give the semester a <strong>name</strong>, its <strong>start ' +
          'and end dates</strong>, and the grading defaults (passing grade ' +
          'and calculation method). Fields marked <strong>*</strong> are ' +
          'required.',
        attachTo: { element: '.cl-form-section', on: 'top' },
        showOn: function () { return present('.cl-form-section'); },
      },
      {
        id: 'autosave',
        title: 'Drafts are saved',
        text:
          'As you type, your entries are <strong>auto-saved as a ' +
          'draft</strong> — if you navigate away by accident, your progress ' +
          'is waiting when you come back.',
        attachTo: { element: '[data-cl-autosave]', on: 'top' },
        showOn: function () { return present('[data-cl-autosave]'); },
      },
      {
        id: 'submit',
        title: 'Save or cancel',
        text:
          'Hit the <strong>primary button</strong> to save the semester, or ' +
          '<strong>Cancel</strong> to return to the catalog without ' +
          'changes.',
        attachTo: { element: '.cl-form-actions', on: 'top' },
        showOn: function () { return present('.cl-form-actions'); },
      },
    ],
  });
})();
