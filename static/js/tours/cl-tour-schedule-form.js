/* cl-tour-schedule-form.js — walkthrough for the create/update Schedule form
 * (subject/templates/schedule/create_schedule.html + update_schedule.html).
 *
 * Both pages share the same .cl-header + #scheduleForm structure, so one
 * tour serves both.
 *
 * Stable anchors:
 *   .cl-header                       — title + back link (always)
 *   #scheduleForm                    — the schedule form (always)
 *   #scheduleForm .cl-btn-primary    — the save button (always)
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

  add('schedule-form', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Add a meeting block',
        text:
          'Define when and where a class meets — a <strong>subject</strong>, ' +
          'a <strong>time window</strong>, the <strong>days</strong>, and the ' +
          'schedule type.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'fields',
        title: 'Fill in the details',
        text:
          'Pick the <strong>subject</strong> first — its room and assigned ' +
          'teacher come from that record. Then set the <strong>start/end ' +
          'time</strong>, <strong>days of the week</strong>, and the ' +
          '<strong>schedule type</strong>.',
        attachTo: { element: '#scheduleForm', on: 'top' },
        showOn: function () { return present('#scheduleForm'); },
      },
      {
        id: 'submit',
        title: 'Save the schedule',
        text:
          'Hit <strong>Save</strong> to add the meeting block — it appears ' +
          'immediately in the schedule list. <strong>Cancel</strong> goes ' +
          'back without changes.',
        attachTo: { element: '#scheduleForm .cl-btn-primary', on: 'top' },
        showOn: function () { return present('#scheduleForm .cl-btn-primary'); },
      },
    ],
  });
})();
