/* cl-tour-subject-analytics.js — walkthrough for the Subject Analytics
 * Panel (templates/teacher/gamification/subject_analytics_panel.html),
 * opened from the teacher dashboard's "My Classes" cards.
 *
 * Page structure:
 *   .cl-header     — title + enrolled-count meta
 *   .sa-tiles      — 3 KPI tiles (class avg, at-risk, completion)
 *   #saScoreDist   — score distribution histogram (Chart.js)
 *   #saRiskDonut   — risk-level donut
 *   #saByType      — avg by activity type horizontal bar
 *   .sa-table      — per-student table sorted by risk
 *
 * Tour decodes the at-risk math (score < 65, weighted by attendance +
 * completion) and the color coding teachers see in the bars/badges.
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

  add('subject-analytics', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Subject analytics',
        text:
          'How the <strong>whole class</strong> is doing in this course. ' +
          'Three KPI tiles at the top, then three charts, then the ' +
          'per-student table — each layer drills deeper.',
        attachTo: { element: '.cl-header', on: 'bottom' },
      },
      {
        id: 'tiles',
        title: 'KPIs at a glance',
        text:
          '<strong>Class average</strong> across all graded work, ' +
          '<strong>at-risk count</strong> (score &lt; 65, weighted by ' +
          'attendance + submission completion), and ' +
          '<strong>completion</strong> — the percentage of expected ' +
          'submissions that have been turned in.',
        attachTo: { element: '.sa-tiles', on: 'bottom' },
      },
      {
        id: 'distribution',
        title: 'Score distribution',
        text:
          'How many students fall into each score band. Bars are ' +
          'color-coded: <strong>rose</strong> for failing bands (0–60), ' +
          '<strong>gold</strong> for borderline (61–70), <strong>brand-' +
          'colored</strong> for passing — gives you the shape of the ' +
          'class\'s performance at a glance.',
        attachTo: { element: '#saScoreDist', on: 'top' },
      },
      {
        id: 'risk',
        title: 'Risk breakdown',
        text:
          'Donut chart splits the class into <strong>Low</strong>, ' +
          '<strong>Medium</strong>, and <strong>High</strong> risk groups. ' +
          'Hover any slice for the exact count and percentage. The high-' +
          'risk slice tells you how many students need immediate attention.',
        attachTo: { element: '#saRiskDonut', on: 'top' },
      },
      {
        id: 'by-type',
        title: 'Average by activity type',
        text:
          'Horizontal bars show the class average for each activity type ' +
          '(quiz, assignment, exam, etc.). Spot weak spots — if essays ' +
          'are at 50% but quizzes are at 85%, you know where to invest ' +
          'review time.',
        attachTo: { element: '#saByType', on: 'top' },
      },
      {
        id: 'student-table',
        title: 'Per-student detail',
        text:
          'The table is <strong>sorted by risk level</strong> (high → low) ' +
          'so the students who need help float to the top. The score bar ' +
          'fills proportionally and turns rose / gold for low / borderline ' +
          'scores.',
        attachTo: { element: '.sa-table', on: 'top' },
      },
      {
        id: 'student-link',
        title: 'Drill into one student',
        text:
          'Click any student name to open their <strong>individual ' +
          'detail page</strong> — assessment-by-assessment scores, ' +
          'attendance record, and submission history.',
        attachTo: { element: '.sa-student-link', on: 'right' },
      },
    ],
  });
})();
