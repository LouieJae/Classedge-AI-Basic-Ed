/* cl-media-skeleton.js — global media-embed skeleton engine.
 *
 * Auto-binds to any element with [data-skeleton] (typically a media
 * shell wrapping an <iframe>, <video>, or <img>). Adds .is-loaded when
 * the embed's first paint fires, .is-slow after a configurable wait,
 * and force-hides after a hard timeout so a dead embed never traps a
 * forever-shimmer.
 *
 * Attributes the engine reads from the shell:
 *   data-skeleton        "doc" | "video" — present-only; the value is
 *                        a hint for CSS, the engine itself doesn't
 *                        care which flavor it is.
 *   data-settle-delay    ms to wait AFTER load before fading the
 *                        skeleton (Office viewer / OneDrive PPT need
 *                        this — they fire `load` before painting).
 *   data-slow-at         ms after which .is-slow is added so CSS can
 *                        swap the status copy. Default 8000.
 *   data-timeout         ms after which the skeleton hard-hides even
 *                        if no load fired. Default 35000.
 *
 * For shells that contain a render target the engine can't observe
 * (e.g. a <canvas> driven by pdf.js), the engine exposes a callback
 * on the shell node — the page can call it when ready:
 *
 *   shell._clMarkLoaded()   call when your render code has painted.
 *   shell._cmMarkLoaded()   back-compat alias for older pages.
 *
 * Re-runs on `cm:navigated` (SPA swap) and via MutationObserver, so
 * any shell injected later is picked up automatically. Safe to load
 * once globally — does nothing on pages without [data-skeleton].
 */
(function () {
  'use strict';

  if (window.ClMediaSkeleton && window.ClMediaSkeleton.__loaded) return;

  var DEFAULT_SLOW_AT = 8000;
  var DEFAULT_TIMEOUT = 35000;
  var BOUND_FLAG      = '__clMediaSkeletonBound';

  function bindShell(shell) {
    if (shell[BOUND_FLAG]) return;
    shell[BOUND_FLAG] = true;

    var settleDelay = parseInt(shell.dataset.settleDelay || '0', 10) || 0;
    var slowAt      = parseInt(shell.dataset.slowAt  || '', 10) || DEFAULT_SLOW_AT;
    var timeoutMs   = parseInt(shell.dataset.timeout || '', 10) || DEFAULT_TIMEOUT;

    var done = false;
    var slowTimer = null;
    var hardTimer = null;

    function markLoaded() {
      if (done) return;
      done = true;
      shell.classList.add('is-loaded');
      if (slowTimer) clearTimeout(slowTimer);
      if (hardTimer) clearTimeout(hardTimer);
    }

    function onLoad() {
      if (settleDelay > 0) setTimeout(markLoaded, settleDelay);
      else markLoaded();
    }

    // First non-skeleton iframe/video/img inside the shell. Walking
    // descendants (not just direct children) lets pages keep their
    // existing layout wrappers without rewriting.
    var target = null;
    var candidates = shell.querySelectorAll('iframe, video, img');
    for (var i = 0; i < candidates.length; i++) {
      var c = candidates[i];
      // Skip nodes that sit inside a skeleton overlay.
      if (c.closest('[class*="skeleton"]')) continue;
      target = c;
      break;
    }

    if (target) {
      var tag = target.tagName;
      if (tag === 'IFRAME') {
        target.addEventListener('load', onLoad, { once: true });
      } else if (tag === 'VIDEO') {
        target.addEventListener('loadeddata', onLoad, { once: true });
        target.addEventListener('error', markLoaded, { once: true });
      } else if (tag === 'IMG') {
        if (target.complete && target.naturalWidth > 0) {
          markLoaded();
        } else {
          target.addEventListener('load', onLoad, { once: true });
          target.addEventListener('error', markLoaded, { once: true });
        }
      }
    }
    // No observable target (e.g. a pdf.js <canvas>): the page calls
    // markLoaded itself when render finishes.

    shell._clMarkLoaded = markLoaded;
    shell._cmMarkLoaded = markLoaded; // legacy alias

    slowTimer = setTimeout(function () {
      if (!done) shell.classList.add('is-slow');
    }, slowAt);
    hardTimer = setTimeout(markLoaded, timeoutMs);
  }

  function scan(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var shells = scope.querySelectorAll('[data-skeleton]');
    for (var i = 0; i < shells.length; i++) bindShell(shells[i]);
  }

  function init() {
    scan(document);

    if (!document.body) return;
    var mo = new MutationObserver(function (mutations) {
      for (var m = 0; m < mutations.length; m++) {
        var added = mutations[m].addedNodes;
        for (var n = 0; n < added.length; n++) {
          var node = added[n];
          if (node.nodeType !== 1) continue;
          if (node.matches && node.matches('[data-skeleton]')) bindShell(node);
          if (node.querySelectorAll) scan(node);
        }
      }
    });
    mo.observe(document.body, { childList: true, subtree: true });

    document.addEventListener('cm:navigated', function () { scan(document); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  window.ClMediaSkeleton = {
    __loaded: true,
    scan: scan,
    bind: bindShell,
  };
})();
