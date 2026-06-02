/* cl-tour-school-profile.js — walkthrough for the School Profile settings
 * (accounts/templates/school_profile/school_profile.html).
 *
 * The institution's public-facing identity: logo, name, and brand color —
 * which propagate across login pages, certificates, reports, and the app UI.
 *
 * Stable anchors:
 *   .cl-header        — title + description (always)
 *   #openLogoModal    — Replace logo button (always)
 *   #openNameModal    — Edit school name button (always)
 *   .sp-card--brand   — brand color picker card (always)
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

  add('school-profile', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'School profile',
        text:
          'Your institution\'s <strong>public identity</strong>. What you ' +
          'set here shows up across login pages, certificates, reports, and ' +
          'the app itself.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'logo',
        title: 'School logo',
        text:
          '<strong>Replace logo</strong> uploads a new PNG (square ratio, ' +
          'under 2 MB). It updates everywhere the logo appears.',
        attachTo: { element: '#openLogoModal', on: 'top' },
        showOn: function () { return present('#openLogoModal'); },
      },
      {
        id: 'name',
        title: 'School name',
        text:
          '<strong>Edit school name</strong> sets the display name and a ' +
          'short name — the short one is used in compact spots like the ' +
          'sidebar.',
        attachTo: { element: '#openNameModal', on: 'top' },
        showOn: function () { return present('#openNameModal'); },
      },
      {
        id: 'brand',
        title: 'Brand color',
        text:
          'One color drives every brand surface — sidebar accents, icons, ' +
          'primary buttons, and more. Pick a <strong>preset</strong> or a ' +
          '<strong>custom hex</strong>; the preview is live, and ' +
          '<strong>Save</strong> applies it for every user.',
        attachTo: { element: '.sp-card--brand', on: 'top' },
        showOn: function () { return present('.sp-card--brand'); },
      },
    ],
  });
})();
