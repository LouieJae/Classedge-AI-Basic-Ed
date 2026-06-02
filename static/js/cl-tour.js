/* cl-tour.js — thin Shepherd.js adapter, per-form-step model.
 *
 * Each tour is scoped to ONE form step (a single .cl-step section in a
 * cl-stepper form). The user reads the tour, clicks "Done", the
 * popover closes, and they fill the fields freely. When they advance
 * the form to the next step, the matching tour for that step
 * auto-launches (if not already dismissed).
 *
 * Tour config shape:
 *   {
 *     id:          'create-assessment-basics',
 *     formStepKey: 'basics',          // auto-fires when the form's
 *                                     // cl-stepper enters this step
 *     tourFamily:  'create-assessment',
 *     autoShow:    true,              // fires on page load (first one only)
 *     form:        'form[data-cl-stepper]',
 *     steps: [
 *       { id, title, text, attachTo: { element, on } } ...
 *     ]
 *   }
 *
 * Buttons are injected by default:
 *   • First step:   [Skip]                       [Next]
 *   • Middle steps: [Back]                       [Next]
 *   • Last step:    [Back]                       [Done]
 * Each tour ends in "Done" (calls tour.complete()) — never with cross-
 * step Next click. The user clicks Done to close the popover so they
 * can fill the form fields. They then click the form's own Next button
 * to advance the stepper; the next tour auto-fires.
 *
 * Family dismissal:
 *   If the user clicks the X (cancel) on any tour in a family, the
 *   family is marked dismissed and sibling tours stop auto-firing.
 *   Clicking "Done" only marks the individual tour seen — siblings
 *   continue to auto-fire.
 *
 * Replay buttons:
 *   <button data-cl-tour="<id>">  starts a specific tour
 *   <button data-cl-tour-family="<family>"> starts the family tour
 *       whose formStepKey matches the form's current step
 */
(function () {
  'use strict';
  if (window.ClTour && window.ClTour.__loaded) return;

  var registry = Object.create(null);
  var active = null;          // { id, tour, formEl, handlers }
  var SEEN_PREFIX     = 'cl-tour:seen:';
  var DISMISSED_PREFIX = 'cl-tour:family-dismissed:';

  function hasShepherd() { return typeof window.Shepherd !== 'undefined'; }

  function defaultOptions() {
    return {
      useModalOverlay: true,
      defaultStepOptions: {
        cancelIcon: { enabled: true },
        classes: 'cl-shepherd',
        scrollTo: { behavior: 'smooth', block: 'center' },
        modalOverlayOpeningPadding: 6,
        modalOverlayOpeningRadius: 10,
      },
    };
  }

  function register(id, config) {
    if (!id || !config || !Array.isArray(config.steps)) return;
    registry[id] = config;
  }

  // Drain any pending registrations that ran before this adapter
  // loaded (tour configs live inside {% block content %} which Django
  // emits BEFORE the body-end <script src="cl-tour.js">).
  function drainPending() {
    var q = window.__clTourPending;
    if (!q || !q.length) return;
    for (var i = 0; i < q.length; i++) {
      try { register(q[i][0], q[i][1]); } catch (_) {}
    }
    q.length = 0;
  }

  // Nuke any Shepherd DOM that the lib may have left attached. Modal
  // overlays in particular tend to linger when complete/cancel fires
  // from within a button action handler, leaving the page dimmed.
  function forceCleanupShepherdDom() {
    try {
      var nodes = document.querySelectorAll(
        '.shepherd-modal-overlay-container, .shepherd-element, .shepherd-target-click-disabled'
      );
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n && n.parentNode) n.parentNode.removeChild(n);
      }
      document.body.classList.remove('shepherd-active');
      document.documentElement.classList.remove('shepherd-active');
    } catch (_) {}
  }

  function destroyActive(opts) {
    if (!active) return;
    var teardown = active;
    active = null;  // flip first so re-entry from listeners no-ops
    if (opts && opts.external) {
      try { teardown.tour.cancel(); } catch (_) {}
    }
    if (teardown.handlers) {
      teardown.handlers.forEach(function (h) {
        h.target.removeEventListener(h.event, h.fn, h.opts || false);
      });
    }
    setTimeout(forceCleanupShepherdDom, 0);
  }

  function bindCmTeardown() {
    function onNav() { destroyActive({ external: true }); }
    document.addEventListener('cm:navigated', onNav);
    return [{ target: document, event: 'cm:navigated', fn: onNav }];
  }

  // Server-side seen set, bootstrapped per account into window.__clTourSeen
  // by the base templates. This makes completion durable across browsers,
  // devices, and cleared local storage — localStorage is just a fast/offline
  // fallback for both anonymous users and instant same-session checks.
  function serverSeenList() {
    var s = window.__clTourSeen;
    return (s && typeof s.indexOf === 'function') ? s : null;
  }
  function serverHasSeen(id) {
    var s = serverSeenList();
    return !!(s && s.indexOf(id) !== -1);
  }
  function readCookie(name) {
    var m = document.cookie.match('(?:^|;\\s*)' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : '';
  }
  function postSeen(id) {
    // Persist to the account. Fire-and-forget; localStorage already covers
    // the offline case, so a failed/blocked request never breaks the tour.
    try {
      var csrf = readCookie('csrftoken');
      var fd = new FormData();
      fd.append('tour_id', id);
      fetch('/tour/seen/', {
        method: 'POST',
        body: fd,
        credentials: 'same-origin',
        headers: csrf ? { 'X-CSRFToken': csrf } : {},
      }).catch(function () {});
    } catch (_) {}
  }

  function markSeen(id) {
    try { localStorage.setItem(SEEN_PREFIX + id, '1'); } catch (_) {}
    // Cache into the in-memory server set so an immediate hasSeen() is true,
    // then persist to the account.
    var s = serverSeenList();
    if (s && s.indexOf(id) === -1) s.push(id);
    postSeen(id);
  }
  function hasSeen(id) {
    if (serverHasSeen(id)) return true;
    try { return localStorage.getItem(SEEN_PREFIX + id) === '1'; } catch (_) { return false; }
  }
  function forget(id) {
    try { localStorage.removeItem(SEEN_PREFIX + id); } catch (_) {}
    // Drop it from the in-memory server set so a replay can auto-fire again
    // this session. (The account record is harmless to keep; the replay pill
    // path explicitly starts the tour regardless.)
    var s = serverSeenList();
    if (s) {
      var i = s.indexOf(id);
      if (i !== -1) s.splice(i, 1);
    }
  }
  function markFamilyDismissed(family) {
    try { localStorage.setItem(DISMISSED_PREFIX + family, '1'); } catch (_) {}
  }
  function isFamilyDismissed(family) {
    try { return localStorage.getItem(DISMISSED_PREFIX + family) === '1'; } catch (_) { return false; }
  }
  function forgetFamily(family) {
    try {
      localStorage.removeItem(DISMISSED_PREFIX + family);
      // Also forget each member's "seen" flag so replays start fresh.
      Object.keys(registry).forEach(function (id) {
        if (registry[id].tourFamily === family) forget(id);
      });
    } catch (_) {}
  }

  function start(id, opts) {
    opts = opts || {};
    var config = registry[id];
    if (!config) {
      console.warn('[cl-tour] No tour registered with id:', id);
      return;
    }
    if (!hasShepherd()) {
      if (opts.__retry >= 20) {
        console.warn('[cl-tour] Shepherd.js not loaded; cannot start tour:', id);
        return;
      }
      var nextOpts = Object.assign({}, opts, { __retry: (opts.__retry || 0) + 1 });
      setTimeout(function () { start(id, nextOpts); }, 100);
      return;
    }

    destroyActive({ external: true });

    var tourOpts = Object.assign({}, defaultOptions(), config.tourOptions || {});
    var tour = new window.Shepherd.Tour(tourOpts);

    // Inject default buttons per step position:
    //   first step: Skip + Next  (or Done if only one step)
    //   middle:     Back + Next
    //   last:       Back + Done
    config.steps.forEach(function (s, i) {
      var step = Object.assign({}, s);
      var isFirst = i === 0;
      var isLast  = i === config.steps.length - 1;
      if (!step.buttons) {
        var left = isFirst
          ? { text: 'Skip', classes: 'cl-shepherd-btn ghost', action: function () { tour.cancel(); } }
          : { text: 'Back', classes: 'cl-shepherd-btn ghost', action: function () { tour.back();   } };
        var right = isLast
          ? { text: 'Done', classes: 'cl-shepherd-btn primary', action: function () { tour.complete(); } }
          : { text: 'Next', classes: 'cl-shepherd-btn primary', action: function () { tour.next();     } };
        step.buttons = [left, right];
      }
      tour.addStep(step);
    });

    var handlers = bindCmTeardown();
    var form = config.form ? document.querySelector(config.form) : document.querySelector('form[data-cl-stepper]');

    // Done → mark individual seen only. Sibling tours still auto-fire
    // when the form advances. Cancel (X / Skip) → mark family dismissed
    // so siblings stop auto-firing.
    tour.on('complete', function () {
      markSeen(id);
      destroyActive();
    });
    tour.on('cancel', function () {
      markSeen(id);
      if (config.tourFamily) markFamilyDismissed(config.tourFamily);
      destroyActive();
    });

    active = { id: id, tour: tour, formEl: form, handlers: handlers };
    tour.start();
  }

  function bindReplayButtons() {
    document.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest && e.target.closest('[data-cl-tour], [data-cl-tour-family]');
      if (!btn) return;
      // Specific tour id takes precedence.
      var directId = btn.getAttribute('data-cl-tour');
      if (directId) {
        e.preventDefault();
        // Replaying after dismissal — clear the family flag so the rest
        // of the chain auto-fires again as the form advances.
        var cfg = registry[directId];
        if (cfg && cfg.tourFamily) forgetFamily(cfg.tourFamily);
        start(directId);
        return;
      }
      var family = btn.getAttribute('data-cl-tour-family');
      if (!family) return;
      e.preventDefault();
      forgetFamily(family);
      var form = document.querySelector('form[data-cl-stepper]');
      var key = '';
      if (form) {
        var activeSection = form.querySelector('.cl-step.is-active');
        key = activeSection ? activeSection.getAttribute('data-step') : '';
      }
      var firstId = findFamilyTour(family, key) || findFamilyTour(family, null);
      if (firstId) start(firstId);
    });
  }

  // Find a registered tour that belongs to `family`. If `stepKey` is
  // provided, return the tour matching that form step. Otherwise return
  // the first member of the family in registration order.
  function findFamilyTour(family, stepKey) {
    var ids = Object.keys(registry);
    for (var i = 0; i < ids.length; i++) {
      var cfg = registry[ids[i]];
      if (cfg.tourFamily !== family) continue;
      if (stepKey == null || cfg.formStepKey === stepKey) return ids[i];
    }
    return null;
  }

  // Listen for cl-stepper:change on every form that has a tour. When
  // the user advances to a new form step, look up the registered tour
  // for that step and auto-start (unless the family was dismissed or
  // this specific tour was already seen).
  function bindGlobalStepperListener() {
    document.addEventListener('cl-stepper:change', function (e) {
      var form = e.target;
      if (!form || !form.matches || !form.matches('form[data-cl-stepper]')) return;
      var detail = e.detail || {};
      var toIndex = detail.to;
      if (typeof toIndex !== 'number') return;
      var sections = form.querySelectorAll('.cl-step');
      var section = sections[toIndex];
      if (!section) return;
      var key = section.getAttribute('data-step') || '';
      if (!key) return;

      // Find a registered tour that owns this stepKey.
      var ids = Object.keys(registry);
      for (var i = 0; i < ids.length; i++) {
        var id = ids[i];
        var cfg = registry[id];
        if (cfg.formStepKey !== key) continue;
        if (hasSeen(id)) continue;
        if (cfg.tourFamily && isFamilyDismissed(cfg.tourFamily)) continue;
        // Brief delay so the new .cl-step section's CSS transition
        // settles before Shepherd computes the anchor rect.
        setTimeout(function (tid) { return function () { start(tid); }; }(id), 80);
        return;
      }
    }, false);
  }

  function autoShowOnFirstVisit() {
    // Each registered tour can opt in via { autoShow: true }. Only one
    // auto-show fires on initial page load (the first matching tour);
    // the rest of the family auto-fires via cl-stepper:change.
    var ids = Object.keys(registry);
    for (var i = 0; i < ids.length; i++) {
      var id = ids[i];
      var cfg = registry[id];
      if (!cfg.autoShow) continue;
      if (hasSeen(id)) continue;
      if (cfg.tourFamily && isFamilyDismissed(cfg.tourFamily)) continue;
      start(id);
      return;
    }
  }

  function init() {
    drainPending();
    bindReplayButtons();
    bindGlobalStepperListener();
    setTimeout(function () {
      drainPending();
      autoShowOnFirstVisit();
    }, 0);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  window.ClTour = {
    __loaded: true,
    register: register,
    start: start,
    forget: forget,
    forgetFamily: forgetFamily,
    hasSeen: hasSeen,
  };
})();
