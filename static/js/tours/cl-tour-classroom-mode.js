/* cl-tour-classroom-mode.js — single-page walkthrough for the
 * Classroom Mode landing dashboard (course/templates/course/classroom_mode.html).
 *
 * This is the entry point teachers see when they tap "Classroom Mode"
 * on a course card. The tour introduces the live session controls
 * (class timer, Start/End Class button), the quick-add modal, the
 * navigation rail, and the weekly schedule grid.
 *
 * Stable anchors used:
 *   .cm-hero                       — top banner
 *   #classroomTimerDisplay         — class session timer
 *   #classActionButton             — Start/End Class button (teacher-only)
 *   .cm-quick-add                  — "Add lesson or activity" trigger
 *   .cm-quick-rail                 — quick links row
 *   .cm-week-grid                  — weekly schedule grid
 *   #cmFullscreenBtn               — fullscreen toggle
 *   [data-cm-exit]                 — exit CM button
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

  add('classroom-mode', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Welcome to Classroom Mode',
        text:
          'A live, projector-friendly view of this course. Use it during ' +
          'class to start the session timer, take attendance, and pull up ' +
          'materials or assessments with one click.',
        attachTo: { element: '.cm-hero', on: 'bottom' },
      },
      {
        id: 'timer',
        title: 'Class session timer',
        text:
          'Tracks how long the current class has been running. Starts ' +
          'when you click <strong>Start Class</strong> and stops when you ' +
          'end the session — useful for attendance records and recap notes.',
        attachTo: { element: '#classroomTimerDisplay', on: 'bottom' },
      },
      {
        id: 'start-class',
        title: 'Start / End Class',
        text:
          'Tap to open the session. Attendance records, the timer, and ' +
          'live participation indicators all key off this button. Tap ' +
          'again at the end of class to stop and save the session.',
        attachTo: { element: '#classActionButton', on: 'bottom' },
      },
      {
        id: 'quick-add',
        title: 'Add lesson or activity',
        text:
          'Open a quick-add panel to drop a lesson, assignment, quiz, ' +
          'exam, or special activity directly into this class — no ' +
          'leaving the live view.',
        attachTo: { element: '.cm-quick-add', on: 'bottom' },
      },
      {
        id: 'quick-rail',
        title: 'Quick navigation',
        text:
          'Jump to the full lists for this course: <strong>Materials</strong>, ' +
          '<strong>Assessments</strong>, and the enrolled <strong>Students</strong> ' +
          'roster. Each opens inside Classroom Mode so you don\'t lose ' +
          'your place.',
        attachTo: { element: '.cm-quick-rail', on: 'bottom' },
      },
      {
        id: 'week-grid',
        title: 'This week\'s schedule',
        text:
          'Your day-by-day plan for the current week. Each card shows ' +
          'the lessons or activities scheduled for that day — click into ' +
          'one to open it.',
        attachTo: { element: '.cm-week-grid', on: 'top' },
      },
      {
        id: 'fullscreen',
        title: 'Fullscreen (or press F)',
        text:
          'Hides the browser chrome so the dashboard fills the projector ' +
          'or screen. Press <strong>F</strong> on the keyboard for the ' +
          'same effect, or Esc to exit.',
        attachTo: { element: '#cmFullscreenBtn', on: 'bottom' },
      },
      {
        id: 'exit',
        title: 'Leave Classroom Mode',
        text:
          'Click the <strong>×</strong> button when class is over. ' +
          'You\'ll return to your course list — any in-progress timer ' +
          'and live attendance state are saved automatically.',
        attachTo: { element: '[data-cm-exit]', on: 'bottom' },
      },
    ],
  });
})();
