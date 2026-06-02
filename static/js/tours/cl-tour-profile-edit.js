/* cl-tour-profile-edit.js — walkthrough for the admin/registrar profile editor
 * (accounts/templates/accounts/admin_update/_profile_page.html — the shared
 * partial behind all student / teacher / staff / program-head edit pages, in
 * both the admin_update and registrar_update wrappers).
 *
 * One tour serves all eight pages because they share this partial.
 *
 * Stable anchors:
 *   .cl-header        — page title + description (always)
 *   .pp-identity      — whose profile is being edited (always)
 *   #profileForm      — the editable fields (always)
 *   .pf-btn-primary   — Save changes button (always)
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

  add('profile-edit', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Edit a profile',
        text:
          'Update someone\'s <strong>personal, contact, and academic</strong> ' +
          'details from here. Use <strong>Back</strong> at the top to return ' +
          'to the list without saving.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'identity',
        title: 'Who you\'re editing',
        text:
          'This banner confirms the <strong>person</strong>, their ' +
          '<strong>role</strong>, ID, and email — a quick check that you\'re ' +
          'on the right account before making changes.',
        attachTo: { element: '.pp-identity', on: 'bottom' },
        showOn: function () { return present('.pp-identity'); },
      },
      {
        id: 'fields',
        title: 'The editable fields',
        text:
          'Adjust name, contact info, and academic details. Some fields may ' +
          'be <strong>locked</strong> when they\'re managed elsewhere — those ' +
          'appear read-only.',
        attachTo: { element: '#profileForm', on: 'top' },
        showOn: function () { return present('#profileForm'); },
      },
      {
        id: 'save',
        title: 'Save your changes',
        text:
          '<strong>Save changes</strong> writes the update and returns you to ' +
          'the list. Nothing is changed until you save.',
        attachTo: { element: '.pf-btn-primary', on: 'top' },
        showOn: function () { return present('.pf-btn-primary'); },
      },
    ],
  });
})();
