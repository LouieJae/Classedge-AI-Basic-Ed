/* cl-tour-transmutation-form.js — walkthrough for the create/update
 * Transmutation Rule form
 * (gradebookcomponent/templates/transmutation/create-transmutation.html +
 *  update-transmutation.html).
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

  add('transmutation-form', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Add a transmutation rule',
        text:
          'A rule maps a <strong>range of raw scores</strong> to a single ' +
          '<strong>transmuted grade</strong> for a grading table — build a ' +
          'full scale one rule at a time.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'fields',
        title: 'Define the mapping',
        text:
          'Set the <strong>raw range</strong> (lower and upper bounds) and ' +
          'the <strong>transmuted value</strong> it should produce, against ' +
          'its grading table. Fields marked <strong>*</strong> are required.',
        attachTo: { element: '.cl-form-section', on: 'top' },
        showOn: function () { return present('.cl-form-section'); },
      },
      {
        id: 'autosave',
        title: 'Drafts are saved',
        text:
          'Your entries <strong>auto-save as a draft</strong> as you go, so ' +
          'a misclick won\'t cost you the rule you were building.',
        attachTo: { element: '[data-cl-autosave]', on: 'top' },
        showOn: function () { return present('[data-cl-autosave]'); },
      },
      {
        id: 'submit',
        title: 'Save or cancel',
        text:
          'Use the <strong>primary button</strong> to save the rule, or ' +
          '<strong>Cancel</strong> to return to the rules list.',
        attachTo: { element: '.cl-form-actions', on: 'top' },
        showOn: function () { return present('.cl-form-actions'); },
      },
    ],
  });
})();
