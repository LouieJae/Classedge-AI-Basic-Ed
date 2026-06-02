/* cl-tour-assessment-detail.js — walkthrough for the per-assessment
 * details page (activity/templates/activity/assessments/assessment-detail.html).
 *
 * This page is the funnel parent of the score sheet, question editor,
 * and grading queue. Teachers reach it from the assessment list or
 * from clicking a row in the dashboard's "Needs grading" widget.
 *
 * Teacher anchors (the tour only auto-fires for teacher view via
 * Django gating on is_student_role — the template uses different
 * action buttons for students):
 *   .ad-hero                                   — type-colored banner
 *   .ad-stats                                  — 6 KPI cards
 *   .ad-card                                   — Instructions card (first .ad-card)
 *   .ad-action                                 — action button row
 *   .ad-action-buttons .ad-btn.primary         — "View Details" (question list)
 *   .ad-action-buttons .ad-btn:nth-of-type(2)  — "View Results" (score sheet)
 *   .ad-action-buttons .ad-btn.success         — "Grade Submissions" (when present)
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

  add('assessment-detail', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Assessment details',
        text:
          'Everything about <strong>one assessment</strong> in one place: ' +
          'the schedule, submission stats, instructions students see, and ' +
          'the buttons that take you into the questions, the scores, and ' +
          'the grading queue.',
        attachTo: { element: '.ad-hero', on: 'bottom' },
      },
      {
        id: 'stats',
        title: 'Submission stats',
        text:
          'Six numbers at a glance: when the assessment <strong>opens / ' +
          'closes</strong>, how many students have <strong>submitted</strong> ' +
          'out of the enrolled total, how many haven\'t yet, how many ' +
          'you\'ve <strong>graded</strong>, and the running ' +
          '<strong>average score</strong> for the class.',
        attachTo: { element: '.ad-stats', on: 'bottom' },
      },
      {
        id: 'instructions',
        title: 'Instructions students see',
        text:
          'This is the briefing students read <strong>before they hit ' +
          'Start</strong> — rules, expectations, any attached file. Edit ' +
          'it by opening the assessment\'s update form.',
        attachTo: { element: '.ad-card', on: 'top' },
      },
      {
        id: 'view-details',
        title: 'View Details — the questions',
        text:
          'Opens the <strong>question list</strong>: add, edit, reorder, ' +
          'or delete the actual test items. This is where you spend ' +
          'time when authoring or revising the content.',
        attachTo: { element: '.ad-action-buttons .ad-btn.primary', on: 'top' },
      },
      {
        id: 'view-results',
        title: 'View Results — the score sheet',
        text:
          'Opens the <strong>score sheet</strong>: every student\'s result, ' +
          'searchable + filterable, with print and CSV export. Use this ' +
          'once submissions are in.',
        attachTo: { element: '.ad-action-buttons .ad-btn:nth-of-type(2)', on: 'top' },
      },
      {
        id: 'grade',
        title: 'Grade Submissions',
        text:
          'Only shown when this assessment has <strong>manually-graded ' +
          'questions</strong> (essay / document upload). Opens the ' +
          'grading queue scoped to this activity — go through submissions ' +
          'one student at a time.',
        attachTo: { element: '.ad-action-buttons .ad-btn.success', on: 'top' },
      },
    ],
  });
})();
