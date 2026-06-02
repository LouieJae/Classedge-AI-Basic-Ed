/* cl-tour-student-material-list.js — walkthrough for the student-facing
 * view of a single course's contents (templates/student/material-list.html).
 *
 * This page has two modes selected by the tab strip:
 *   - Lessons view (default): search/sort toolbar + a list of lesson
 *     blocks. Each lesson can have nested activities (assessments).
 *   - Assessments view: status filter chips + the assessment inventory.
 *
 * The tour steps use showOn() to skip the irrelevant view-specific steps
 * so the same tour runs cleanly whether the student lands on Lessons or
 * Assessments first.
 *
 * Stable anchors:
 *   .lessons-header         — course title + instructor chip
 *   .lessons-tabs           — Lessons / Assessments tab strip
 *   .lessons-toolbar        — search + sort (Lessons view only)
 *   .asm-filters            — status chip filters (Assessments view only)
 *   .lesson-block           — first lesson card (Lessons view, when any)
 *   .asm-card               — first assessment card (Assessments view, when any)
 *   .lessons-side           — sidebar (Due / To Do / Upcoming / Progress / etc.)
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

  function isLessonsView() {
    var active = document.querySelector('.lessons-tab.is-active');
    if (!active) return true;
    return !/assessments/i.test(active.getAttribute('href') || '');
  }
  function isAssessmentsView() { return !isLessonsView(); }

  add('student-material-list', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Your course workspace',
        text:
          'Everything for <strong>this course</strong> lives here — ' +
          'lessons your teacher has posted, assessments to complete, and ' +
          'a side panel with what\'s due, your progress, and quick ' +
          'shortcuts. Use the chip on the right to <strong>message your ' +
          'instructor</strong>.',
        attachTo: { element: '.lessons-header', on: 'bottom' },
      },
      {
        id: 'tabs',
        title: 'Lessons vs Assessments',
        text:
          'Switch between <strong>Lessons</strong> (study material, ' +
          'recordings, embedded slides) and <strong>Assessments</strong> ' +
          '(quizzes, exams, assignments). The number beside each tab is ' +
          'the count — handy for sanity-checking what you have left.',
        attachTo: { element: '.lessons-tabs', on: 'bottom' },
      },
      {
        id: 'lessons-toolbar',
        title: 'Search & sort lessons',
        text:
          '<strong>Search</strong> by material name, or pick a ' +
          '<strong>sort order</strong> — by newest, name, or due date. ' +
          'Useful when a course has dozens of lessons across weeks.',
        attachTo: { element: '.lessons-toolbar', on: 'bottom' },
        showOn: function () {
          return isLessonsView() && !!document.querySelector('.lessons-toolbar');
        },
      },
      {
        id: 'lesson-block',
        title: 'Each lesson + its activities',
        text:
          'A lesson card shows its <strong>title</strong>, the term it ' +
          'belongs to, and an "Open" button. If the lesson has linked ' +
          'activities (quiz, exam, assignment), they\'re nested ' +
          'underneath — tap one to jump straight to it. Completed ' +
          'activities are dimmed and struck through.',
        attachTo: { element: '.lesson-block', on: 'top' },
        showOn: function () {
          return isLessonsView() && !!document.querySelector('.lesson-block');
        },
      },
      {
        id: 'asm-filters',
        title: 'Filter assessments by status',
        text:
          'Quick chips for <strong>Due soon</strong>, ' +
          '<strong>Open</strong>, <strong>Upcoming</strong>, ' +
          '<strong>Missed</strong>, and <strong>Submitted</strong>. The ' +
          'number on each chip is the count — tap to filter the list ' +
          'below.',
        attachTo: { element: '.asm-filters', on: 'bottom' },
        showOn: function () {
          return isAssessmentsView() && !!document.querySelector('.asm-filters');
        },
      },
      {
        id: 'asm-card',
        title: 'Assessment cards',
        text:
          'Each card shows the assessment <strong>name</strong>, ' +
          '<strong>type</strong>, <strong>points</strong>, and ' +
          '<strong>due / opens</strong> date. The status pill on the ' +
          'right tells you where you stand. If the score is visible to ' +
          'you, it shows beneath the pill.',
        attachTo: { element: '.asm-card', on: 'top' },
        showOn: function () {
          return isAssessmentsView() && !!document.querySelector('.asm-card');
        },
      },
      {
        id: 'sidebar',
        title: 'Your side panel',
        text:
          'The right side keeps a live read on this course: ' +
          '<strong>Due Soon</strong>, <strong>To Do</strong>, ' +
          '<strong>Upcoming</strong>, your <strong>progress</strong>, ' +
          'your <strong>instructor</strong> card, and quick links to ' +
          '<strong>classmates</strong> and other resources. It stays ' +
          'visible as you scroll on wide screens.',
        attachTo: { element: '.lessons-side', on: 'left' },
      },
    ],
  });
})();
