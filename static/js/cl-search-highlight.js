/* ============================================================================
 * [Classedge LMS] cl-search-highlight.js — instant search highlighting.
 *
 * Wraps matching substrings inside a search-filtered list in a soft
 * brand-tinted <mark>, so the user's eye lands on the keyword without
 * scanning the row. Tracks --brand-primary so the tint follows tenant brand.
 *
 * Public API:
 *   ClHighlight.wrap(rootEl, query)   — wrap matches inside rootEl
 *   ClHighlight.clear(rootEl)         — remove all marks from rootEl
 *   ClHighlight.attach(inputEl, targetSelector, opts)
 *                                     — convenience: bind an input to a
 *                                       target so typing auto-highlights;
 *                                       debounced ~80ms.
 *
 * Design notes:
 *  • TreeWalker on SHOW_TEXT — we only touch real text nodes, so HTML
 *    structure (icons, links, images, attributes) is never broken.
 *  • Skip <script>, <style>, <textarea>, <input>, and existing marks via
 *    the acceptNode filter so we don't recursively re-wrap or corrupt
 *    code/form fields.
 *  • Each wrap() call clears prior marks first, then re-walks. Means the
 *    DOM always reflects the CURRENT query and a backspace cleans up.
 *  • Restores adjacent text-node merges via parent.normalize() on clear,
 *    so repeated wrap/clear cycles don't leave a tree fragmented into
 *    dozens of split text nodes.
 *  • Visible-only by design (per the UX decision on 2026-05-21): if a row
 *    matches via a data-* attribute but the substring doesn't appear in
 *    the rendered text, no highlight is drawn — preferred over surfacing
 *    invisible matches.
 * ============================================================================ */
(function () {
  'use strict';

  if (window.ClHighlight) return;

  const STYLE_ID = 'cl-search-highlight-style';
  if (!document.getElementById(STYLE_ID)) {
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent =
      'mark.cl-search-hit {' +
        'background: color-mix(in srgb, var(--brand-primary, #b7925a) 22%, transparent);' +
        'color: inherit;' +
        'padding: 0 1px;' +
        'border-radius: 3px;' +
        'font-weight: inherit;' +
        'box-shadow: 0 0 0 1px color-mix(in srgb, var(--brand-primary, #b7925a) 30%, transparent);' +
      '}';
    (document.head || document.documentElement).appendChild(style);
  }

  function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function clear(rootEl) {
    if (!rootEl || !rootEl.querySelectorAll) return;
    const marks = rootEl.querySelectorAll('mark.cl-search-hit');
    marks.forEach(function (m) {
      const parent = m.parentNode;
      if (!parent) return;
      while (m.firstChild) parent.insertBefore(m.firstChild, m);
      parent.removeChild(m);
      parent.normalize();
    });
  }

  function wrap(rootEl, query) {
    if (!rootEl) return;
    clear(rootEl);
    if (!query) return;
    const q = String(query).trim();
    if (!q) return;

    const rx = new RegExp(escapeRegex(q), 'gi');

    // Collect all text nodes that contain at least one match. Doing this in
    // two passes (collect, then replace) avoids invalidating the walker
    // mid-iteration by mutating the tree we're walking.
    const textNodes = [];
    const walker = document.createTreeWalker(rootEl, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue) return NodeFilter.FILTER_REJECT;
        const parent = node.parentElement;
        if (!parent) return NodeFilter.FILTER_REJECT;
        if (parent.closest('script, style, textarea, input, select, mark.cl-search-hit')) {
          return NodeFilter.FILTER_REJECT;
        }
        rx.lastIndex = 0;
        if (!rx.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });

    let n;
    while ((n = walker.nextNode())) textNodes.push(n);

    textNodes.forEach(function (node) {
      const text = node.nodeValue;
      const frag = document.createDocumentFragment();
      let lastIdx = 0;
      rx.lastIndex = 0;
      let m;
      while ((m = rx.exec(text)) !== null) {
        // Guard against zero-width matches (shouldn't happen with our regex,
        // but cheap insurance against infinite loops).
        if (m.index === rx.lastIndex) { rx.lastIndex++; continue; }
        if (m.index > lastIdx) {
          frag.appendChild(document.createTextNode(text.slice(lastIdx, m.index)));
        }
        const markEl = document.createElement('mark');
        markEl.className = 'cl-search-hit';
        markEl.textContent = m[0];
        frag.appendChild(markEl);
        lastIdx = m.index + m[0].length;
      }
      if (lastIdx < text.length) {
        frag.appendChild(document.createTextNode(text.slice(lastIdx)));
      }
      if (node.parentNode) node.parentNode.replaceChild(frag, node);
    });
  }

  // Convenience wiring. Pages that don't have their own filter loop can use:
  //   ClHighlight.attach(inputEl, '.row-selector');
  // Pages with a custom filter loop should call wrap()/clear() directly
  // inside that loop so highlighting only fires on visible rows.
  function attach(inputEl, targetSelector, opts) {
    if (!inputEl || !targetSelector) return;
    const debounceMs = (opts && opts.debounce) || 80;
    let timer = null;
    function run() {
      const q = (inputEl.value || '').trim();
      document.querySelectorAll(targetSelector).forEach(function (row) {
        if (row.style.display === 'none') {
          clear(row);
          return;
        }
        wrap(row, q);
      });
    }
    inputEl.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(run, debounceMs);
    });
  }

  window.ClHighlight = { wrap: wrap, clear: clear, attach: attach };
})();
