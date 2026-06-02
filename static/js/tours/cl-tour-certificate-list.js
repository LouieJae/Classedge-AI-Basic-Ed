/* cl-tour-certificate-list.js — walkthrough for the Certificate library
 * (accounts/templates/accounts/certificate/certificate.html).
 *
 * Issue and manage certificates that recognize student achievement. Built
 * on the shared async list-table loaded into #cl-cert-wrapper. This script
 * is only included on the certificate template, so it never registers on
 * the other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   .cl-actions       — New Certificate button (always)
 *   .cl-toolbar       — search + rows-per-page (always)
 *   .cl-table         — the certificates table (always)
 *   .cl-action-btn    — per-row action menu (when rows exist)
 *   .cl-pagination    — page navigation (when more than one page)
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

  add('certificate-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Certificate library',
        text:
          'Issue, organize, and update the <strong>certificates</strong> ' +
          'that recognize student achievement across the school.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Create a certificate',
        text:
          '<strong>New Certificate</strong> opens a builder to design one — ' +
          'name it, set its template, and make it available to award.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions .cl-btn'); },
      },
      {
        id: 'search',
        title: 'Find a certificate',
        text:
          '<strong>Search</strong> and set the <strong>rows per page</strong>. ' +
          'The library filters as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Your certificates',
        text:
          'Each row is a certificate in the library. Fields with a dotted ' +
          'underline are editable inline.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Edit or remove',
        text:
          'The <strong>action menu</strong> edits a certificate or removes ' +
          'it from the library.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through certificates',
        text:
          'When the library grows past one page, step through it here.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
