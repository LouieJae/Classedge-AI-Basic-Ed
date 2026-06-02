/* ─────────────────────────────────────────────────────────────────
   cl-table-mobile.js — Intentional Column Dropping engine.

   Activates on any <table data-cl-mobile-collapse> at viewports
   ≤ 640px. Hides every column except those marked
   `data-cl-mobile-keep` on the matching <th>, and rebuilds the
   hidden cells as an expandable accordion drawer below each row.

   Defaults to keeping the first 2 columns if no header opts in.

   Re-applies automatically when:
     • the viewport crosses the breakpoint (resize)
     • the table's tbody contents change (HTMX refresh, JS row inject)
   ───────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var BREAKPOINT_QUERY = '(max-width: 640px)';
  var KEEP_DEFAULT = 2;
  // Selectors for interactive descendants that should NOT trigger the
  // row's expand/collapse toggle. Keeps existing in-row controls
  // (action dropdowns, inline-edit fields, links) working untouched.
  var INTERACTIVE_SELECTOR =
    'a, button, input, select, textarea, label, [contenteditable], ' +
    '[role="button"], .dropdown-toggle, .dropdown-menu, .dropdown-item, ' +
    '.cl-action-btn, .cl-edit';

  function mql() { return window.matchMedia(BREAKPOINT_QUERY); }

  var INLINE_ACTION_LIMIT = 2;

  function flattenActionMenu(val) {
    var menu = val.querySelector(
      '.dropdown-menu, [role="menu"], .rb-actions-menu, .cm-row-actions-menu, .ll-add-menu'
    );
    if (!menu) return;
    var rawChildren = Array.prototype.slice.call(menu.children);
    var actionNodes = rawChildren.filter(function (n) {
      if (!n.classList) return false;
      if (n.classList.contains('dropdown-divider')) return false;
      if (n.tagName === 'HR') return false;
      if (n.classList.contains('dropdown-item')) return true;
      if (n.getAttribute && n.getAttribute('role') === 'menuitem') return true;
      if (n.tagName === 'A' || n.tagName === 'BUTTON') return true;
      if (n.tagName === 'FORM') return !!n.querySelector('a, button, [role="menuitem"], .dropdown-item');
      if (n.querySelector && n.querySelector('.dropdown-item, [role="menuitem"]')) return true;
      return false;
    });
    if (!actionNodes.length) return;

    var toggleSelector =
      '.dropdown-toggle, .rb-actions-btn, .cm-row-actions-btn, .ll-add-trigger, [aria-haspopup="menu"], [aria-haspopup="true"]';
    var toggle = val.querySelector(toggleSelector);
    if (toggle) toggle.style.display = 'none';
    menu.style.display = 'none';

    var inline = actionNodes.slice(0, INLINE_ACTION_LIMIT);
    var overflow = actionNodes.slice(INLINE_ACTION_LIMIT);

    var row = document.createElement('div');
    row.className = 'cl-action-row';

    function findActionItem(clone) {
      if (clone.classList && clone.classList.contains('dropdown-item')) return clone;
      if (clone.getAttribute && clone.getAttribute('role') === 'menuitem') return clone;
      if (clone.tagName === 'A' || clone.tagName === 'BUTTON') return clone;
      return clone.querySelector('.dropdown-item, [role="menuitem"], a, button');
    }

    function unwrap(clone, item) {
      if (!clone || !item) return item || clone;
      if (clone === item) return clone;
      if (clone.tagName === 'FORM') return clone;
      if (clone.querySelector && clone.querySelector('form')) return clone;
      return item;
    }

    inline.forEach(function (node) {
      var clone = node.cloneNode(true);
      var item = findActionItem(clone);
      if (!item) return;
      var icon = item.querySelector('i, [class*="fa-"]');
      var label = (item.textContent || '').trim() || item.getAttribute('aria-label') || '';
      item.innerHTML = '';
      if (icon) {
        var iconClone = icon.cloneNode(true);
        iconClone.className = iconClone.className.replace(/\bme-\d+\b/g, '').trim();
        item.appendChild(iconClone);
      } else if (label) {
        var initial = document.createElement('span');
        initial.textContent = label.charAt(0).toUpperCase();
        item.appendChild(initial);
      }
      item.classList.remove('dropdown-item');
      item.classList.add('cl-action-pill');
      var isDanger = item.classList.contains('danger') ||
                     item.classList.contains('text-danger') ||
                     /danger/.test(item.className);
      if (isDanger) {
        item.classList.add('is-danger');
      }
      if (label) {
        item.setAttribute('aria-label', label);
        item.setAttribute('title', label);
      }
      row.appendChild(unwrap(clone, item));
    });

    if (overflow.length > 0) {
      var moreWrap = document.createElement('div');
      moreWrap.className = 'cl-action-more';
      var moreBtn = document.createElement('button');
      moreBtn.type = 'button';
      moreBtn.className = 'cl-action-pill cl-action-pill-more';
      moreBtn.setAttribute('aria-label', 'More actions');
      moreBtn.setAttribute('aria-haspopup', 'true');
      moreBtn.setAttribute('aria-expanded', 'false');
      moreBtn.innerHTML = '<i class="fas fa-ellipsis"></i>';
      var moreMenu = document.createElement('div');
      moreMenu.className = 'cl-action-more-menu';
      overflow.forEach(function (node) {
        var oClone = node.cloneNode(true);
        var oItem = findActionItem(oClone);
        moreMenu.appendChild(unwrap(oClone, oItem));
      });
      moreBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        var willOpen = !moreMenu.classList.contains('is-open');
        document.querySelectorAll('.cl-action-more-menu.is-open').forEach(function (m) {
          m.classList.remove('is-open');
        });
        if (willOpen) {
          moreMenu.classList.add('is-open');
          moreBtn.setAttribute('aria-expanded', 'true');
        } else {
          moreBtn.setAttribute('aria-expanded', 'false');
        }
      });
      moreWrap.appendChild(moreBtn);
      moreWrap.appendChild(moreMenu);
      row.appendChild(moreWrap);
    }

    val.appendChild(row);
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('.cl-action-more')) return;
    document.querySelectorAll('.cl-action-more-menu.is-open').forEach(function (m) {
      m.classList.remove('is-open');
      var btn = m.parentElement && m.parentElement.querySelector('.cl-action-pill-more');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  });

  // ── One-time setup per table: stamp keep classes on the header,
  //    capture header labels for use as drawer keys.
  function setupTable(table) {
    if (table._clMobileWired) return;
    table._clMobileWired = true;

    var thead = table.tHead;
    if (!thead || !thead.rows[0]) return;
    var headerRow = thead.rows[0];
    var headers = Array.prototype.slice.call(headerRow.cells);
    if (!headers.length) return;

    var keep = [];
    headers.forEach(function (th, i) {
      if (th.hasAttribute('data-cl-mobile-keep')) keep.push(i);
    });
    if (!keep.length) {
      for (var k = 0; k < Math.min(KEEP_DEFAULT, headers.length); k++) keep.push(k);
    }
    headers.forEach(function (th, i) {
      if (keep.indexOf(i) !== -1) th.classList.add('cl-mobile-keep');
    });

    table._clMobileKeep = keep;
    table._clMobileLabels = headers.map(function (th) {
      return (th.textContent || '').trim();
    });
  }

  // ── Build (or rebuild) the drawer rows for the current tbody. Safe
  //    to call repeatedly — strips existing drawer rows first so HTMX
  //    refreshes don't double up.
  function rebuildDrawers(table) {
    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return;
    var keep = table._clMobileKeep || [];
    var labels = table._clMobileLabels || [];

    // Drop stale drawer rows.
    Array.prototype.slice.call(tbody.rows).forEach(function (r) {
      if (r.classList.contains('cl-table-drawer')) r.parentNode.removeChild(r);
    });

    Array.prototype.slice.call(tbody.rows).forEach(function (row) {
      if (row.classList.contains('cl-table-drawer')) return;
      var cells = Array.prototype.slice.call(row.cells);
      if (!cells.length) return;

      // Empty-state placeholder (single cell with colspan) — skip drawer.
      if (cells.length === 1 && cells[0].hasAttribute('colspan')) {
        row.classList.add('cl-empty-row');
        return;
      }
      row.classList.remove('cl-empty-row');

      // Tag keep/drop cells.
      cells.forEach(function (td, i) {
        if (keep.indexOf(i) !== -1) td.classList.add('cl-mobile-keep');
        else td.classList.remove('cl-mobile-keep');
      });

      // Compose drawer row.
      var drawer = document.createElement('tr');
      drawer.className = 'cl-table-drawer';
      drawer.setAttribute('aria-hidden', 'true');
      var drawerCell = document.createElement('td');
      drawerCell.setAttribute('colspan', String(cells.length));
      var inner = document.createElement('div');
      inner.className = 'cl-table-drawer-inner';

      cells.forEach(function (td, i) {
        if (keep.indexOf(i) !== -1) return;
        var raw = (td.textContent || '').trim();
        var hasInteractive = td.querySelector(
          'a, button, input, select, textarea, [role="button"], .dropdown, .dropdown-toggle, form'
        );
        var hasMedia = td.querySelector('img, svg, i, .fa, .fas, .far, .fab');
        if (!raw && !hasInteractive && !hasMedia) return;
        if (raw === '—' && !hasInteractive && !hasMedia) return;
        var item = document.createElement('div');
        item.className = 'cl-table-drawer-item';
        var lab = document.createElement('div');
        lab.className = 'cl-table-drawer-label';
        lab.textContent = labels[i] || '';
        var val = document.createElement('div');
        val.className = 'cl-table-drawer-value';
        val.innerHTML = td.innerHTML;
        item.appendChild(lab);
        item.appendChild(val);
        inner.appendChild(item);
      });

      Array.prototype.slice.call(inner.querySelectorAll('.cl-table-drawer-value')).forEach(flattenActionMenu);

      drawerCell.appendChild(inner);
      drawer.appendChild(drawerCell);
      row.parentNode.insertBefore(drawer, row.nextSibling);

      if (!row._clMobileClick) {
        row._clMobileClick = function (e) {
          var t = e.target;
          while (t && t !== row) {
            if (t.matches && t.matches(INTERACTIVE_SELECTOR)) return;
            t = t.parentNode;
          }
          var sel = window.getSelection && window.getSelection();
          if (sel && sel.type === 'Range' && sel.toString().length) return;

          var opening = !row.classList.contains('is-expanded');
          if (opening) {
            Array.prototype.slice.call(tbody.rows).forEach(function (other) {
              if (other === row) return;
              if (other.classList.contains('is-expanded')) {
                other.classList.remove('is-expanded');
                var otherDrawer = other.nextElementSibling;
                if (otherDrawer && otherDrawer.classList.contains('cl-table-drawer')) {
                  otherDrawer.setAttribute('aria-hidden', 'true');
                }
              }
            });
            dismissHint(table);
          }
          row.classList.toggle('is-expanded');
          drawer.setAttribute('aria-hidden', opening ? 'false' : 'true');
        };
        row.addEventListener('click', row._clMobileClick);
      } else {
        drawer.setAttribute('aria-hidden', row.classList.contains('is-expanded') ? 'false' : 'true');
      }
    });
  }

  // ── Tear down: undo every mobile mutation so the desktop layout
  //    is byte-identical to what it was before the engine ran.
  function teardown(table) {
    table.classList.remove('is-mobile-collapse');
    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return;
    Array.prototype.slice.call(tbody.rows).forEach(function (r) {
      if (r.classList.contains('cl-table-drawer')) {
        r.parentNode.removeChild(r);
        return;
      }
      Array.prototype.slice.call(r.cells).forEach(function (c) {
        c.classList.remove('cl-mobile-keep');
      });
      r.classList.remove('is-expanded', 'cl-empty-row');
    });
    if (table.tHead && table.tHead.rows[0]) {
      Array.prototype.slice.call(table.tHead.rows[0].cells).forEach(function (c) {
        c.classList.remove('cl-mobile-keep');
      });
    }
  }

  var MIN_COLS_FOR_COLLAPSE = 3;

  function eligible(table) {
    if (!table || table.nodeName !== 'TABLE') return false;
    if (table.classList.contains('cl-no-mobile-collapse')) return false;
    if (table.hasAttribute('data-cl-no-collapse')) return false;
    var th = table.tHead;
    if (!th || !th.rows[0]) return false;
    if (th.rows[0].cells.length < MIN_COLS_FOR_COLLAPSE) return false;
    var ancestor = table.parentElement;
    while (ancestor) {
      if (ancestor.classList && ancestor.classList.contains('cl-no-mobile-collapse')) return false;
      ancestor = ancestor.parentElement;
    }
    return true;
  }

  function lockAncestorOverflow(table) {
    var ancestor = table.parentElement;
    var depth = 0;
    while (ancestor && ancestor !== document.body && depth < 12) {
      if (!ancestor.dataset.clScrollLocked) {
        var cs = getComputedStyle(ancestor);
        if (cs.overflowX === 'auto' || cs.overflowX === 'scroll') {
          ancestor.dataset.clScrollLocked = cs.overflowX;
          ancestor.style.overflowX = 'hidden';
        }
      }
      ancestor = ancestor.parentElement;
      depth++;
    }
  }
  function restoreAncestorOverflow(table) {
    var ancestor = table.parentElement;
    var depth = 0;
    while (ancestor && ancestor !== document.body && depth < 12) {
      if (ancestor.dataset.clScrollLocked) {
        ancestor.style.overflowX = ancestor.dataset.clScrollLocked;
        delete ancestor.dataset.clScrollLocked;
      }
      ancestor = ancestor.parentElement;
      depth++;
    }
  }

  function hintAnchor(table) {
    var wrap = table.closest ? table.closest('.table-responsive') : null;
    return wrap || table;
  }
  function ensureHint(table) {
    if (table._clHintDismissed) return;
    if (table._clHintEl && table._clHintEl.isConnected) return;
    var anchor = hintAnchor(table);
    var host = anchor.parentNode;
    if (!host) return;
    var wrap = document.createElement('div');
    wrap.className = 'cl-table-hint-wrap';
    var hint = document.createElement('div');
    hint.className = 'cl-table-hint';
    hint.setAttribute('role', 'note');
    hint.innerHTML =
      '<i class="fas fa-chevron-down cl-table-hint-glyph" aria-hidden="true"></i>' +
      '<span><strong>Tap any row</strong> to expand</span>';
    wrap.appendChild(hint);
    host.insertBefore(wrap, anchor);
    table._clHintEl = wrap;
  }
  function removeHint(table) {
    var wrap = table._clHintEl;
    if (!wrap) return;
    if (wrap.parentNode) wrap.parentNode.removeChild(wrap);
    table._clHintEl = null;
  }
  function dismissHint(table) {
    table._clHintDismissed = true;
    var wrap = table._clHintEl;
    if (!wrap) return;
    var hint = wrap.firstElementChild;
    if (hint) hint.classList.add('is-dismissed');
    wrap.classList.add('is-dismissed');
    table._clHintEl = null;
    setTimeout(function () {
      if (wrap && wrap.parentNode) wrap.parentNode.removeChild(wrap);
    }, 400);
  }

  function applyAll() {
    var on = mql().matches;
    document.querySelectorAll('table').forEach(function (table) {
      if (!eligible(table)) return;
      setupTable(table);
      if (on) {
        table.classList.add('is-mobile-collapse');
        rebuildDrawers(table);
        lockAncestorOverflow(table);
        ensureHint(table);
      } else {
        restoreAncestorOverflow(table);
        teardown(table);
        removeHint(table);
      }
    });
  }

  // ── DOM observer: HTMX swaps a tbody, async-table replaces rows,
  //    JS injects new content — re-apply the engine whenever the
  //    contents of a collapsible table change.
  function observe() {
    if (!('MutationObserver' in window)) return;
    var observer = new MutationObserver(function (mutations) {
      var dirty = false;
      for (var i = 0; i < mutations.length && !dirty; i++) {
        var m = mutations[i];
        if (m.target.closest && m.target.closest('table')) {
          var changedRealRow = false;
          for (var a = 0; a < m.addedNodes.length; a++) {
            var n = m.addedNodes[a];
            if (n.classList && !n.classList.contains('cl-table-drawer')) {
              changedRealRow = true; break;
            }
          }
          for (var r = 0; r < m.removedNodes.length && !changedRealRow; r++) {
            var rn = m.removedNodes[r];
            if (rn.classList && !rn.classList.contains('cl-table-drawer')) {
              changedRealRow = true; break;
            }
          }
          if (changedRealRow || (m.addedNodes.length === 0 && m.removedNodes.length === 0)) {
            dirty = true;
          }
        }
        for (var b = 0; b < m.addedNodes.length && !dirty; b++) {
          var nn = m.addedNodes[b];
          if (nn.querySelector && nn.querySelector('table')) {
            dirty = true;
          }
        }
      }
      if (dirty) Promise.resolve().then(applyAll);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function boot() {
    applyAll();
    var m = mql();
    // matchMedia change covers viewport rotation + resize without
    // having to debounce a scroll-heavy resize listener.
    if (m.addEventListener) m.addEventListener('change', applyAll);
    else if (m.addListener) m.addListener(applyAll);
    observe();
    // Diagnostic — confirms the engine loaded + reports current state.
    // Check the browser console after load: you should see how many
    // collapsible tables were found and whether the mobile breakpoint
    // is active. If "tables found: 0", the page you're on doesn't ship
    // the data-cl-mobile-collapse attribute on its table.
    try {
      var allTables = document.querySelectorAll('table');
      var eligibleCount = 0;
      allTables.forEach(function (t) { if (eligible(t)) eligibleCount++; });
      console.log('[cl-table-mobile] loaded — eligible tables:', eligibleCount, '/ total tables:', allTables.length, '· mobile breakpoint:', m.matches);
    } catch (e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
