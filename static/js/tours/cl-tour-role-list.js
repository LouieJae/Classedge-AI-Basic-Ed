/* cl-tour-role-list.js — walkthrough for the Roles & Permissions manager
 * (roles/templates/role/role_list.html).
 *
 * Define roles and control what each can access. The table is an async
 * component (data-cl-async-table) loaded into #cl-role-wrapper.
 *
 * Stable anchors:
 *   .cl-header          — title + description (always)
 *   .cl-actions         — Add Role / Import / Export buttons (always)
 *   #cl-role-wrapper    — the roles table (always present)
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

  add('role-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Roles & permissions',
        text:
          'This is where you <strong>define roles</strong> and control what ' +
          'each one can access across the system. Every account is assigned ' +
          'a role, and the role decides what they see.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'actions',
        title: 'Add & move roles in bulk',
        text:
          '<strong>Add Role</strong> opens a builder to name a role and tick ' +
          'its permissions. <strong>Import</strong> / <strong>Export</strong> ' +
          'move role definitions in and out via CSV — handy for setting up a ' +
          'new school or backing up your config.',
        attachTo: { element: '.cl-actions', on: 'bottom' },
        showOn: function () { return present('.cl-actions'); },
      },
      {
        id: 'table',
        title: 'Your roles',
        text:
          'Each row is a role. From here you can <strong>view</strong> its ' +
          'permissions, <strong>edit</strong> what it can access, or remove ' +
          'it. Use the table\'s search and sort to find a role fast.',
        attachTo: { element: '#cl-role-wrapper', on: 'top' },
        showOn: function () { return present('#cl-role-wrapper'); },
      },
    ],
  });
})();
