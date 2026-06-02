/* [Classedge LMS] window.ClBrand — chart-vendor bridge for our
 * --brand-primary CSS variable.
 *
 * The CSS cascade already handles theming for native elements (active
 * nav, primary buttons, em accents). But Chart.js and ECharts don't
 * read CSS variables — they take color strings at init time. This
 * module is the bridge: it resolves --brand-primary at the right
 * moments, pairs it with the LOCKED system neutrals (gold, rose,
 * forest-2, ink-dim, ink-muted — never tenant-overridable), and
 * re-pushes the palette into registered chart instances whenever
 * the theme toggles or a brand override is injected.
 *
 * Public API:
 *   ClBrand.read(token, fallback?)   -> string   read any CSS custom prop
 *   ClBrand.primary()                -> string   resolved --brand-primary
 *   ClBrand.primarySoft()            -> string   resolved --brand-primary-soft
 *   ClBrand.palette()                -> string[] [brand, gold, rose, forest-2, ink-dim, ink-muted]
 *   ClBrand.register(chart, applyFn)            register a chart instance for auto-refresh
 *   ClBrand.refresh()                           manually re-push palette to every registered chart
 *
 * Registration contract:
 *   The caller supplies an `applyFn(palette)` closure that knows how
 *   to project the palette onto its specific chart (which data series
 *   gets which color, etc.). We deliberately don't bake assumptions
 *   about chart shape into this module — each chart's registration
 *   site is the single place that decides how brand color flows into
 *   its dataset configuration.
 *
 * Example:
 *   var chart = new Chart(el, opts);
 *   ClBrand.register(chart, function (palette) {
 *     chart.data.datasets[0].backgroundColor = palette[0];
 *     chart.update();
 *   });
 */
(function () {
  'use strict';
  if (window.ClBrand) return;

  // Each entry: { instance: <opaque>, apply: function(palette) }
  var registered = [];

  function read(token, fallback) {
    try {
      var v = getComputedStyle(document.documentElement)
        .getPropertyValue(token)
        .trim();
      return v || (fallback || '');
    } catch (e) {
      return fallback || '';
    }
  }

  function primary()     { return read('--brand-primary', '#1b4332'); }
  function primarySoft() { return read('--brand-primary-soft', 'rgba(27,67,50,0.18)'); }

  // Palette pairs the tenant-overridable brand color with our LOCKED
  // system neutrals. Order is tuned for chart series so the brand
  // always leads, then the locked accents fill out the remaining slots.
  // The locked colors never move per tenant — categorical readability
  // is preserved across brand swaps.
  function palette() {
    return [
      primary(),                          // 0: brand-driven (tenant-overridable)
      read('--gold',      '#b7925a'),     // 1: locked system accent
      read('--rose',      '#c08479'),     // 2: locked secondary
      read('--forest-2',  '#2d5a47'),     // 3: locked deep variant
      read('--ink-dim',   '#6c7080'),     // 4: locked neutral
      read('--ink-muted', '#a0a4b8'),     // 5: locked deep neutral
    ];
  }

  function register(instance, applyFn) {
    if (!instance || typeof applyFn !== 'function') return null;
    var entry = { instance: instance, apply: applyFn };
    registered.push(entry);
    return entry;
  }

  function refresh() {
    var p = palette();
    for (var i = 0; i < registered.length; i++) {
      try {
        registered[i].apply(p);
      } catch (err) {
        // A single chart's failure shouldn't break the rest.
        console.warn('[ClBrand] refresh failed for one chart:', err);
      }
    }
  }

  function init() {
    if (!window.MutationObserver) return;

    // Theme swap — light/dark toggle changes the resolved value of
    // --forest (and therefore --brand-primary, which aliases it),
    // so we need to re-push the palette.
    try {
      new MutationObserver(refresh).observe(document.body, {
        attributes: true,
        attributeFilter: ['data-theme'],
      });
    } catch (_) {}

    // Brand override appearing at runtime. The dev shim already runs
    // synchronously in <head> before this script, so initial state is
    // correct without help — this observer only catches LATER changes
    // (e.g. a tenant-aware SPA injecting a new <style> after route
    // change, or the dev shim being re-run via a future toggle).
    try {
      new MutationObserver(function (records) {
        for (var i = 0; i < records.length; i++) {
          var r = records[i];
          for (var j = 0; j < r.addedNodes.length; j++) {
            var n = r.addedNodes[j];
            if (n.nodeType !== 1) continue;
            if (n.matches && (
              n.matches('style[data-cl-brand-dev]') ||
              n.matches('style[data-cl-brand]')
            )) {
              refresh();
              return;
            }
          }
        }
      }).observe(document.head, { childList: true });
    } catch (_) {}
  }

  window.ClBrand = {
    read:        read,
    primary:     primary,
    primarySoft: primarySoft,
    palette:     palette,
    register:    register,
    refresh:     refresh,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
