/* cl-tour-term-form.js — walkthrough for the create/update Term form
 * (course/templates/course/term/create-term.html + update-term.html).
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

  add('term-form', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Set up a term',
        text:
          'A term is a <strong>grading period inside a semester</strong> ' +
          '(prelim, midterm, finals). It scopes when scores are entered and ' +
          'how they roll up.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'fields',
        title: 'Fill in the details',
        text:
          'Name the term, attach it to its <strong>semester</strong>, and ' +
          'set its <strong>date window</strong>. Fields marked ' +
          '<strong>*</strong> are required.',
        attachTo: { element: '.cl-form-section', on: 'top' },
        showOn: function () { return present('.cl-form-section'); },
      },
      {
        id: 'autosave',
        title: 'Drafts are saved',
        text:
          'Your entries are <strong>auto-saved as a draft</strong> while ' +
          'you work, so an accidental navigation won\'t lose them.',
        attachTo: { element: '[data-cl-autosave]', on: 'top' },
        showOn: function () { return present('[data-cl-autosave]'); },
      },
      {
        id: 'submit',
        title: 'Save or cancel',
        text:
          'Use the <strong>primary button</strong> to save the term, or ' +
          '<strong>Cancel</strong> to go back to the catalog.',
        attachTo: { element: '.cl-form-actions', on: 'top' },
        showOn: function () { return present('.cl-form-actions'); },
      },
    ],
  });
})();
