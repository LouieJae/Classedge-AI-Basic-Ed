/* cl-tour-department-list.js — walkthrough for the Departments manager
 * (accounts/templates/accounts/departments/department_list.html).
 *
 * Organize the school into departments. Built on the shared async
 * list-table (includes/_list_table.html) loaded into #cl-dept-wrapper.
 * This script is only included on the department template, so it never
 * registers on the other pages that share the list-table partial.
 *
 * Stable anchors:
 *   .cl-header            — title + description (always)
 *   #openAddDepartmentBtn — New Department button (always)
 *   .cl-toolbar           — search box + rows-per-page (always)
 *   .cl-table             — the departments table (always)
 *   .cl-action-btn        — per-row action menu (when rows exist)
 *   .cl-pagination        — page navigation (when more than one page)
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

  add('department-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Departments',
        text:
          'Organize the school into <strong>departments</strong>. Each one ' +
          'owns its semesters, events, and announcements — so this is the ' +
          'top of your organizational structure.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'add',
        title: 'Create a department',
        text:
          '<strong>New Department</strong> opens a quick form to name a ' +
          'department and set it up. It immediately becomes available to ' +
          'attach semesters and people to.',
        attachTo: { element: '#openAddDepartmentBtn', on: 'bottom' },
        showOn: function () { return present('#openAddDepartmentBtn'); },
      },
      {
        id: 'search',
        title: 'Find a department',
        text:
          '<strong>Search</strong> by name and set the <strong>rows per ' +
          'page</strong>. The list filters as you type.',
        attachTo: { element: '.cl-toolbar', on: 'bottom' },
        showOn: function () { return present('.cl-toolbar'); },
      },
      {
        id: 'table',
        title: 'Your departments',
        text:
          'Each row is a department. Fields with a dotted underline are ' +
          '<strong>editable inline</strong> — click to rename or adjust ' +
          'without leaving the page.',
        attachTo: { element: '.cl-table', on: 'top' },
        showOn: function () { return present('.cl-table'); },
      },
      {
        id: 'actions',
        title: 'Manage a department',
        text:
          'The <strong>action menu</strong> opens the department\'s full ' +
          'settings or removes it.',
        attachTo: { element: '.cl-action-btn', on: 'left' },
        showOn: function () { return present('.cl-action-btn'); },
      },
      {
        id: 'pagination',
        title: 'Page through departments',
        text:
          'When there are more departments than fit on one page, step ' +
          'through them here.',
        attachTo: { element: '.cl-pagination', on: 'top' },
        showOn: function () { return present('.cl-pagination'); },
      },
    ],
  });
})();
