/* cl-tour-termbook-form.js — walkthrough for the create/update Termbook form
 * (gradebookcomponent/templates/termbook/create_term_book.html +
 *  update_term_book.html).
 *
 * Both pages share the gbf-form structure, so one tour serves both. The
 * creation-tips step only appears on the create page (it has the guide card).
 *
 * Stable anchors:
 *   .topbar           — page title + description (always)
 *   .gbf-form         — the termbook form (always)
 *   .gbf-guide-card   — creation tips sidebar (create page only)
 *   .gbf-actions      — submit + cancel buttons (always)
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

  add('termbook-form', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Set up a termbook',
        text:
          'A termbook defines how much a <strong>term weighs</strong> toward ' +
          'a course\'s grade, and the base/passing thresholds. Assign one ' +
          'term to one or many courses at once.',
        attachTo: { element: '.topbar', on: 'bottom' },
      },
      {
        id: 'fields',
        title: 'Fill in the weighting',
        text:
          'Pick the <strong>term</strong> and the <strong>courses</strong> ' +
          'it applies to, then set the <strong>base grade</strong>, ' +
          '<strong>passing grade</strong>, and the term\'s <strong>percentage ' +
          'weight</strong>. All term percentages for a course must total 100%.',
        attachTo: { element: '.gbf-form', on: 'top' },
        showOn: function () { return present('.gbf-form'); },
      },
      {
        id: 'tips',
        title: 'Watch the rules',
        text:
          'These <strong>creation tips</strong> flag the common gotchas — ' +
          'percentages can\'t exceed 100% per course, and a course can only ' +
          'appear once per term.',
        attachTo: { element: '.gbf-guide-card', on: 'left' },
        showOn: function () { return present('.gbf-guide-card'); },
      },
      {
        id: 'submit',
        title: 'Save or cancel',
        text:
          'Use the <strong>primary button</strong> to save the termbook, or ' +
          '<strong>Cancel</strong> to return to the gradebook.',
        attachTo: { element: '.gbf-actions', on: 'top' },
        showOn: function () { return present('.gbf-actions'); },
      },
    ],
  });
})();
