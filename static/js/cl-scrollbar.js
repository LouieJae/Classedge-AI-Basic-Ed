/* [Classedge LMS] Custom overlay scrollbar — pixel-identical across
 * Firefox, Chrome, Edge, Safari, Brave. Native scrollbars are hidden by
 * CSS (.cl-scrollbar-host) and we paint our own thumb/track over the
 * scrolling element. All colors and sizes are driven by the design
 * tokens declared in base_operation.html, so light/dark themes are
 * automatic.
 *
 * Targets:
 *   - the document scroller (html / body), always
 *   - .sidebar-scroll
 *   - any element marked [data-cl-scroll]
 *
 * Hooks:
 *   window.ClScrollbar.bind(element)  // attach to a custom element
 *   window.ClScrollbar.refresh()      // re-measure every bar (e.g. after
 *                                     // injecting a tall block via HTMX)
 */
(function () {
  'use strict';
  if (window.ClScrollbar && window.ClScrollbar.__loaded) return;

  var MIN_THUMB = 28;          // smallest thumb height (px)
  var TRACK_INSET = 4;         // breathing room top/bottom of the track
  var EDGE_INSET = 4;          // breathing room from the right edge
  var IDLE_HIDE_MS = 900;      // ms of no-scroll before the bar fades
  var bars = [];               // every overlay we've ever created

  function isVerticalScrollable(el) {
    if (!el) return false;
    return el.scrollHeight > el.clientHeight + 1;
  }

  function makeBar(target) {
    var isDoc = (target === window || target === document || target === document.documentElement || target === document.body);
    var scroller = isDoc ? (document.scrollingElement || document.documentElement) : target;

    var track = document.createElement('div');
    track.className = 'cl-scrollbar' + (isDoc ? ' cl-scrollbar--doc' : '');
    track.setAttribute('aria-hidden', 'true');

    var thumb = document.createElement('div');
    thumb.className = 'cl-scrollbar__thumb';
    track.appendChild(thumb);
    document.body.appendChild(track);

    var dragging = false;
    var dragStartY = 0;
    var dragStartScroll = 0;
    var idleTimer = null;
    var rafToken = null;

    function metrics() {
      if (isDoc) {
        return {
          scrollTop: scroller.scrollTop,
          scrollHeight: scroller.scrollHeight,
          clientHeight: window.innerHeight,
          top: 0,
          right: 0,
          height: window.innerHeight
        };
      }
      var r = target.getBoundingClientRect();
      return {
        scrollTop: target.scrollTop,
        scrollHeight: target.scrollHeight,
        clientHeight: target.clientHeight,
        top: r.top,
        right: Math.max(0, window.innerWidth - r.right),
        height: r.height
      };
    }

    function update() {
      rafToken = null;
      var m = metrics();
      var overflow = m.scrollHeight - m.clientHeight;
      if (overflow <= 1 || m.height <= 0) {
        track.style.display = 'none';
        return;
      }
      track.style.display = '';

      var trackH = Math.max(0, m.height - TRACK_INSET * 2);
      var thumbH = Math.max(MIN_THUMB, trackH * (m.clientHeight / m.scrollHeight));
      var thumbTop = (m.scrollTop / overflow) * (trackH - thumbH);

      track.style.top = (m.top + TRACK_INSET) + 'px';
      track.style.right = (m.right + EDGE_INSET) + 'px';
      track.style.height = trackH + 'px';
      thumb.style.height = thumbH + 'px';
      thumb.style.transform = 'translate3d(0,' + thumbTop + 'px,0)';
    }

    function schedule() {
      if (rafToken !== null) return;
      rafToken = requestAnimationFrame(update);
    }

    function showThenIdle() {
      track.classList.add('is-visible');
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(function () {
        if (!dragging) track.classList.remove('is-visible');
      }, IDLE_HIDE_MS);
    }

    // ── Scroll & resize wiring ───────────────────────────────────────
    if (isDoc) {
      window.addEventListener('scroll', function () { schedule(); showThenIdle(); }, { passive: true });
      window.addEventListener('resize', schedule);
    } else {
      target.addEventListener('scroll', function () { schedule(); showThenIdle(); }, { passive: true });
      window.addEventListener('resize', schedule);
      if (window.ResizeObserver) {
        try { new ResizeObserver(schedule).observe(target); } catch (_) {}
      }
      if (window.MutationObserver) {
        try {
          new MutationObserver(schedule).observe(target, {
            childList: true, subtree: true, characterData: true
          });
        } catch (_) {}
      }
    }

    // ── Hover keeps the bar visible (overlay UX) ─────────────────────
    track.addEventListener('mouseenter', function () {
      track.classList.add('is-hover');
      track.classList.add('is-visible');
      if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    });
    track.addEventListener('mouseleave', function () {
      track.classList.remove('is-hover');
      if (!dragging) showThenIdle();
    });

    // ── Drag the thumb ───────────────────────────────────────────────
    thumb.addEventListener('mousedown', function (e) {
      dragging = true;
      dragStartY = e.clientY;
      dragStartScroll = scroller.scrollTop;
      track.classList.add('is-active', 'is-visible');
      document.body.classList.add('cl-scrollbar-dragging');
      e.preventDefault();
      e.stopPropagation();
    });

    function onMove(e) {
      if (!dragging) return;
      var m = metrics();
      var overflow = m.scrollHeight - m.clientHeight;
      if (overflow <= 0) return;
      var trackH = Math.max(0, m.height - TRACK_INSET * 2);
      var thumbH = Math.max(MIN_THUMB, trackH * (m.clientHeight / m.scrollHeight));
      var maxDrag = trackH - thumbH;
      if (maxDrag <= 0) return;
      var dy = e.clientY - dragStartY;
      var newScroll = dragStartScroll + (dy / maxDrag) * overflow;
      newScroll = Math.max(0, Math.min(overflow, newScroll));
      scroller.scrollTop = newScroll;
    }
    function onUp() {
      if (!dragging) return;
      dragging = false;
      track.classList.remove('is-active');
      document.body.classList.remove('cl-scrollbar-dragging');
      showThenIdle();
    }
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);

    // ── Click on track (outside thumb) jumps the page ────────────────
    track.addEventListener('mousedown', function (e) {
      if (e.target === thumb) return;
      var rect = track.getBoundingClientRect();
      var m = metrics();
      var overflow = m.scrollHeight - m.clientHeight;
      if (overflow <= 0) return;
      var trackH = rect.height;
      var thumbH = Math.max(MIN_THUMB, trackH * (m.clientHeight / m.scrollHeight));
      var localY = e.clientY - rect.top - thumbH / 2;
      var maxDrag = trackH - thumbH;
      var ratio = Math.max(0, Math.min(1, localY / maxDrag));
      scroller.scrollTop = ratio * overflow;
      e.preventDefault();
    });

    requestAnimationFrame(update);

    var api = { update: schedule, target: target, isDoc: isDoc };
    bars.push(api);
    return api;
  }

  function init() {
    document.documentElement.classList.add('cl-scrollbar-host');

    // Document scroller — always bind.
    makeBar(window);

    // Known scroll containers.
    var sidebarScroll = document.querySelector('.sidebar-scroll');
    if (sidebarScroll) makeBar(sidebarScroll);

    document.querySelectorAll('[data-cl-scroll]').forEach(function (el) {
      makeBar(el);
    });

    // Pick up new opt-in scroll containers added after page load (HTMX
    // swaps, modal mounts, dynamically injected panels).
    if (window.MutationObserver) {
      try {
        new MutationObserver(function (records) {
          records.forEach(function (rec) {
            rec.addedNodes && rec.addedNodes.forEach(function (n) {
              if (n.nodeType !== 1) return;
              if (n.matches && n.matches('[data-cl-scroll]')) makeBar(n);
              if (n.querySelectorAll) {
                n.querySelectorAll('[data-cl-scroll]').forEach(function (el) {
                  if (!el.__clScrollBound) {
                    el.__clScrollBound = true;
                    makeBar(el);
                  }
                });
              }
            });
          });
          // Existing bars may need re-measure after DOM churn.
          bars.forEach(function (b) { b.update(); });
        }).observe(document.body, { childList: true, subtree: true });
      } catch (_) {}
    }
  }

  window.ClScrollbar = {
    __loaded: true,
    bind: function (el) {
      if (!el || el.__clScrollBound) return;
      el.__clScrollBound = true;
      return makeBar(el);
    },
    refresh: function () { bars.forEach(function (b) { b.update(); }); }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
