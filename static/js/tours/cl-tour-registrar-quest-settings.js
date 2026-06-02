/* cl-tour-registrar-quest-settings.js — walkthrough for Quest Authoring Settings
 * (templates/operations/registrar_quest_settings.html).
 *
 * A small settings form: which quest-authoring modes teachers may use, and
 * which AI provider backs the AI-assisted mode.
 *
 * Stable anchors:
 *   .rqs-page                    — page wrapper / heading (always)
 *   .rqs-modes                   — the three mode toggles (always)
 *   select[name="ai_provider"]   — AI provider picker (always)
 *   button[type="submit"]        — Save button (always)
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

  add('registrar-quest-settings', {
    autoShow: true,
    steps: [
      {
        id: 'welcome',
        title: 'Quest authoring settings',
        text:
          'Control which <strong>quest-authoring modes</strong> teachers ' +
          'across the school are allowed to use. Changes here apply to ' +
          'everyone who builds quests.',
        attachTo: { element: '.rqs-page', on: 'bottom' },
      },
      {
        id: 'modes',
        title: 'Allowed authoring modes',
        text:
          'Toggle each mode on or off — <strong>AI-assisted</strong> ' +
          'generation, <strong>manual</strong> entry, and <strong>bulk ' +
          'upload</strong> from CSV/JSON. Disabled modes disappear from the ' +
          'teacher\'s quest builder.',
        attachTo: { element: '.rqs-modes', on: 'bottom' },
        showOn: function () { return present('.rqs-modes'); },
      },
      {
        id: 'provider',
        title: 'AI provider',
        text:
          'When AI-assisted mode is on, this picks which <strong>provider' +
          '</strong> generates the drafts — Anthropic or OpenAI.',
        attachTo: { element: 'select[name="ai_provider"]', on: 'bottom' },
        showOn: function () { return present('select[name="ai_provider"]'); },
      },
      {
        id: 'save',
        title: 'Apply your changes',
        text:
          'Hit <strong>Save</strong> to roll the settings out. The footer ' +
          'records when they were last changed and by whom.',
        attachTo: { element: 'button[type="submit"]', on: 'top' },
        showOn: function () { return present('button[type="submit"]'); },
      },
    ],
  });
})();
