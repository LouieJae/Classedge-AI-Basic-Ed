/* ─────────────────────────────────────────────────────────────
   cl-select2.js — Classedge Select2 engine
   Pairs with /static/css/cl-select2.css.

   What it does:
   1. Exposes `window.clSelect2.init(selector, options)` — a small
      wrapper around jQuery's $().select2() that applies our
      defaults: bootstrap-5 theme, width: 100%, placeholder, and
      allowClear.
   2. Globally rewrites every bootstrap-5 Select2 instance's
      chip-remove (×) and clear-all (×) buttons into our own
      <button class="cl-chip-x"> / <button class="cl-select-clear">
      markup so the design tracks --brand-primary / --rose and
      isn't fighting the theme's btn-close SVG mask.
   3. Watches the document for any new Select2 containers (added
      dynamically by HTMX, modals, etc.) and reapplies the
      rewrite without per-page wiring.

   Pages can either:
     - call `clSelect2.init('#someForm select')` — full convenience
     - call $().select2(...) themselves — the chip/clear rewrite
       still applies globally
     - mark <select data-cl-select2> or <select class="cl-select">
       and the engine auto-initializes it on DOMContentLoaded
   ───────────────────────────────────────────────────────────── */

(function (global) {
  'use strict';

  var DEFAULTS = {
    theme: 'bootstrap-5',
    width: '100%',
    placeholder: 'Select…',
    allowClear: true,
  };

  function jq() { return global.jQuery; }
  function ready() {
    var $ = jq();
    return !!($ && $.fn && $.fn.select2);
  }

  // Walk from any element inside a Select2 container to the native
  // <select> Select2 wraps. The native select is the .select2's
  // previous sibling.
  function selectForButton(container) {
    var s2 = container.closest('.select2-container');
    var native = s2 && s2.previousElementSibling;
    if (native && native.tagName === 'SELECT') return native;
    return null;
  }

  function hideOriginalClear(el) {
    el.setAttribute('hidden', '');
    el.setAttribute('data-cl-hidden', '1');
    el.style.display = 'none';
    el.style.visibility = 'hidden';
  }

  function rewriteChips() {
    if (!ready()) return;
    var $ = jq();

    // Per-chip × button on multi-selects
    document.querySelectorAll('.select2-container--bootstrap-5 .select2-selection__choice').forEach(function (chip) {
      if (chip.dataset.clChipRewritten === '1') return;
      var orig = chip.querySelector('.select2-selection__choice__remove');
      if (!orig) return;

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cl-chip-x';
      btn.setAttribute('aria-label', 'Remove item');
      btn.innerHTML = '<i class="fas fa-xmark" aria-hidden="true"></i>';

      btn.addEventListener('mousedown', function (e) { e.preventDefault(); e.stopPropagation(); });
      btn.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        var native = selectForButton(chip);
        if (!native) return;
        var $sel = $(native);
        var label = (chip.getAttribute('title') || (chip.querySelector('.select2-selection__choice__display') || {}).textContent || '').trim();
        if (!label) return;
        var current = $sel.val() || [];
        if (!Array.isArray(current)) current = [current];
        // Remove the value whose <option> text matches this chip's label.
        var values = current.filter(function (v) {
          var opt = native.querySelector('option[value="' + CSS.escape(v) + '"]');
          return opt && opt.textContent.trim() !== label;
        });
        $sel.val(values).trigger('change');
      });

      orig.setAttribute('hidden', '');
      chip.insertBefore(btn, orig);
      chip.dataset.clChipRewritten = '1';
    });

    // Clear-all (×) button on every selection box
    document.querySelectorAll('.select2-container--bootstrap-5 .select2-selection').forEach(function (sel) {
      var orig = sel.querySelector('.select2-selection__clear');
      var existing = sel.querySelector('.cl-select-clear');
      if (!orig) {
        if (existing) existing.remove();
        return;
      }
      hideOriginalClear(orig);
      if (existing) return;

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cl-select-clear';
      btn.setAttribute('aria-label', 'Clear selection');
      btn.setAttribute('title', 'Clear selection');
      btn.innerHTML = '<i class="fas fa-xmark" aria-hidden="true"></i>';

      btn.addEventListener('mousedown', function (e) { e.preventDefault(); e.stopPropagation(); });
      btn.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        var native = selectForButton(sel);
        if (!native) return;
        var $sel = $(native);
        $sel.val(native.multiple ? [] : null).trigger('change');
      });

      sel.appendChild(btn);
    });
  }

  function init(selector, options) {
    if (!ready()) return jq() ? jq() : null;
    var $ = jq();
    var $els = (typeof selector === 'string' || selector instanceof Element) ? $(selector) : selector;
    var opts = $.extend({}, DEFAULTS, options || {});
    $els.each(function () {
      var $el = $(this);
      if ($el.hasClass('select2-hidden-accessible')) return;
      $el.select2(opts);
      $el.on('select2:select select2:unselect change', function () {
        global.requestAnimationFrame(rewriteChips);
      });
    });
    global.requestAnimationFrame(rewriteChips);
    return $els;
  }

  function bootstrapAuto() {
    if (!ready()) return;
    init('select[data-cl-select2], select.cl-select');
    // First sweep over any selects already inited by page-level code
    rewriteChips();

    // Watch every existing & future bootstrap-5 Select2 container for
    // chip / clear-button DOM changes. New containers may also appear
    // later (HTMX swap, modal opens), so re-scan the document body too.
    var obs = new MutationObserver(function () {
      global.requestAnimationFrame(rewriteChips);
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  global.clSelect2 = {
    init: init,
    refresh: rewriteChips,
    defaults: DEFAULTS,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapAuto);
  } else {
    bootstrapAuto();
  }
})(window);
