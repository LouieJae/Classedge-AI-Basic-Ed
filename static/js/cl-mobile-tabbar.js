(function () {
  'use strict';

  // Only activate on touch-leaning viewports. The CSS hides the bar
  // above 768px regardless, but we also skip the JS work there.
  function isMobileViewport() {
    return window.matchMedia('(max-width: 768px)').matches;
  }

  // ── 1. Auto-hide on scroll down, re-show on scroll up.
  //    Threshold of 200px prevents flicker on small scroll jitters.
  //    The bar always shows when scroll is near the top.
  function wireScrollHide(bar) {
    var lastY = window.scrollY;
    var hidden = false;
    var THRESHOLD = 200;
    var TICK_MIN = 8; // ignore sub-8px moves to dampen noise

    function onScroll() {
      var y = window.scrollY;
      var dy = y - lastY;

      if (Math.abs(dy) < TICK_MIN) return;

      // Always show near the top of the page
      if (y < THRESHOLD) {
        if (hidden) { bar.classList.remove('is-hidden'); hidden = false; }
        lastY = y;
        return;
      }

      if (dy > 0 && !hidden) {
        // scrolling DOWN — hide
        bar.classList.add('is-hidden');
        hidden = true;
      } else if (dy < 0 && hidden) {
        // scrolling UP — show
        bar.classList.remove('is-hidden');
        hidden = false;
      }
      lastY = y;
    }

    var rafQueued = false;
    window.addEventListener('scroll', function () {
      if (rafQueued) return;
      rafQueued = true;
      window.requestAnimationFrame(function () {
        rafQueued = false;
        onScroll();
      });
    }, { passive: true });
  }

  // ── 2. Action-sheet open/close (FAB + More).
  //    Both sheets share a single backdrop. Close on backdrop click,
  //    swipe-down on the handle, or Escape.
  var sheetRegistry = {};
  function wireSheet(triggerSelector, sheetName) {
    var triggers = triggerSelector
      ? document.querySelectorAll('[' + triggerSelector + ']')
      : [];
    var sheet = document.querySelector('[data-cl-tabbar-sheet="' + sheetName + '"]');
    var backdrop = document.querySelector('[data-cl-tabbar-sheet-backdrop]');
    if (!sheet || !backdrop) return;

    function open() {
      sheet.removeAttribute('hidden');
      backdrop.removeAttribute('hidden');
      // Force a paint then add visible class so the transition fires
      requestAnimationFrame(function () {
        sheet.classList.add('is-open');
        backdrop.classList.add('is-open');
      });
      triggers.forEach(function (t) { t.setAttribute('aria-expanded', 'true'); });
      document.body.classList.add('cl-tabbar-sheet-open');
    }
    function close() {
      sheet.classList.remove('is-open');
      backdrop.classList.remove('is-open');
      triggers.forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
      document.body.classList.remove('cl-tabbar-sheet-open');
      // Wait for the slide-out transition to finish before hiding
      setTimeout(function () {
        if (!sheet.classList.contains('is-open')) {
          sheet.setAttribute('hidden', '');
        }
        if (!document.querySelector('.cl-tabbar-sheet.is-open')) {
          backdrop.setAttribute('hidden', '');
        }
      }, 220);
    }

    triggers.forEach(function (t) { t.addEventListener('click', open); });
    backdrop.addEventListener('click', close);
    sheet.querySelectorAll('[data-cl-tabbar-sheet-close]').forEach(function (el) {
      el.addEventListener('click', close);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sheet.classList.contains('is-open')) close();
    });

    sheetRegistry[sheetName] = { open: open, close: close, sheet: sheet };

    // Swipe-down-to-close on the sheet handle
    var handle = sheet.querySelector('.cl-tabbar-sheet-handle');
    if (handle) {
      var startY = null;
      handle.addEventListener('touchstart', function (e) {
        startY = e.touches[0].clientY;
      }, { passive: true });
      handle.addEventListener('touchmove', function (e) {
        if (startY === null) return;
        var dy = e.touches[0].clientY - startY;
        if (dy > 40) { close(); startY = null; }
      }, { passive: true });
      handle.addEventListener('touchend', function () { startY = null; });
    }
  }

  // ── 3. Body padding so the last bit of page content isn't covered.
  //    Applied as a class so CSS owns the value (varies with safe-area-inset).
  function addBodyPadding() {
    document.body.classList.add('has-cl-tabbar');
  }

  // ── Boot
  function boot() {
    var bar = document.querySelector('[data-cl-tabbar]');
    if (!bar) return;

    if (isMobileViewport()) {
      addBodyPadding();
      wireScrollHide(bar);
    }

    // Sheets work on all viewports (so the More menu would work on
    // tablets too if the bar is ever shown wider). Cheap to wire.
    wireSheet('data-cl-tabbar-fab', 'fab');
    wireSheet('data-cl-tabbar-more', 'more');
    wireSheet(null, 'picker-material');
    wireSheet(null, 'picker-assessment');

    document.addEventListener('click', function (e) {
      var btn = e.target.closest && e.target.closest('[data-cl-pick]');
      if (!btn) return;
      var name = btn.getAttribute('data-cl-pick');
      if (!name) return;
      var pickerKey = 'picker-' + name;
      var fab = sheetRegistry.fab;
      var picker = sheetRegistry[pickerKey];
      if (!picker) return;
      e.preventDefault();
      if (fab) fab.close();
      setTimeout(function () { picker.open(); }, 240);
    });

    // Re-evaluate body padding if the viewport flips between desktop/mobile
    window.addEventListener('resize', function () {
      if (isMobileViewport()) {
        document.body.classList.add('has-cl-tabbar');
      } else {
        document.body.classList.remove('has-cl-tabbar');
        bar.classList.remove('is-hidden');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
