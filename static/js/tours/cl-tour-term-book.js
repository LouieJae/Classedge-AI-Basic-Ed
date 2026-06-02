/* cl-tour-term-book.js — walkthrough for the Termbook list
 * (gradebookcomponent/templates/termbook/term_book.html).
 *
 * Termbooks define how much a term weighs toward a subject's grade, plus
 * the base grade. Custom .gb-* table (not the shared list-table).
 *
 * Stable anchors:
 *   .gb-actions          — Add Termbook button + search (always)
 *   .gb-btn--primary     — Add Termbook button (always)
 *   .gb-search           — filter input (always)
 *   .gb-table            — the termbook table (always)
 *   .gb-action-cell      — per-row edit/delete (when rows exist)
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

  add('term-book', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Termbooks',
        text:
          'A termbook sets how much a <strong>term weighs</strong> toward a ' +
          'subject\'s final grade, along with its base grade — the backbone ' +
          'of how term scores roll up.',
        attachTo: { element: '.gb-actions', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Add a termbook',
        text:
          '<strong>Add Termbook</strong> opens a form to pick the ' +
          'subject(s), term, percentage weight, and base grade.',
        attachTo: { element: '.gb-btn--primary', on: 'bottom' },
        showOn: function () { return present('.gb-btn--primary'); },
      },
      {
        id: 'search',
        title: 'Filter termbooks',
        text:
          'Type to <strong>filter</strong> by subject or term — the table ' +
          'narrows instantly.',
        attachTo: { element: '.gb-search', on: 'bottom' },
        showOn: function () { return present('.gb-search'); },
      },
      {
        id: 'table',
        title: 'Your termbooks',
        text:
          'Each row shows the <strong>subject(s)</strong>, the term\'s ' +
          '<strong>percentage weight</strong>, the term, and the base ' +
          'grade. The footer totals how many you have.',
        attachTo: { element: '.gb-table', on: 'top' },
        showOn: function () { return present('.gb-table'); },
      },
      {
        id: 'actions',
        title: 'Edit or delete',
        text:
          'Use the row\'s <strong>edit</strong> and <strong>delete</strong> ' +
          'buttons to adjust a termbook\'s weighting or remove it.',
        attachTo: { element: '.gb-action-cell', on: 'left' },
        showOn: function () { return present('td.gb-action-cell'); },
      },
    ],
  });
})();
