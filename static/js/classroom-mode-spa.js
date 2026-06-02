/* [Classedge LMS] Classroom-Mode SPA navigator.
 *
 * WHY: Browsers exit fullscreen on every full-page navigation, and the
 * fullscreen API requires a user gesture to re-enter — meaning you cannot
 * programmatically restore fullscreen after a normal page load. The only
 * way to keep the projector view fullscreen across "pages" is to never
 * actually navigate. This script intercepts in-CM link clicks, fetches the
 * destination, parses it, and swaps the body content in place. Fullscreen
 * stays because the document never reloads.
 *
 * Recognition: A page opts into this layer by including the meta tag
 *   <meta name="cm-page" content="true">
 * (already present in _cm_head.html and the standalone classroom_mode head).
 *
 * What gets re-run on swap: any <script> in the new body. Scripts in <head>
 * are not touched. Bare global state survives across swaps; init code that
 * lives inside a DOMContentLoaded handler on the destination page will run
 * because we manually dispatch DOMContentLoaded after the swap.
 */
(function () {
  'use strict';

  // Bail if we are not on a CM page (the meta opts in).
  function isCMDocument(doc) {
    var meta = (doc || document).querySelector('meta[name="cm-page"][content="true"]');
    return !!meta;
  }
  if (!isCMDocument(document)) return;

  // Tag every <style> block already in the head so we know they "belong to"
  // the current page. On the next swap we remove these and inject the new
  // page's <style> blocks. Without this, page-specific inline CSS (like the
  // huge style block in classroom_mode.html) stays on the document forever
  // and the next page renders unstyled.
  Array.from(document.head.querySelectorAll('style')).forEach(function (s) {
    if (s.id === 'cmSpaStyle') return; // our own loading-bar style — keep
    s.setAttribute('data-cm-spa-style', '1');
  });

  // Record every external <script src> that has already been loaded by the
  // initial document. On future swaps we skip re-executing these (re-running
  // Bootstrap, jQuery, Select2, etc. re-registers their delegated event
  // handlers and gives us double-fire bugs — e.g. modal backdrop glitches
  // because $(document).on('click.bs.modal.data-api') is bound twice). Also
  // re-running a file that uses top-level `let` throws SyntaxError.
  //
  // We key by getAttribute('src') (the raw attribute string), not script.src
  // (the resolved URL). DOMParser documents have baseURI=about:blank, so
  // relative src= attributes resolve to different strings on parsed docs
  // vs. the live doc — comparing the resolved URLs would miss every
  // {% static %}-rendered path.
  var loadedScriptSrcs = new Set();
  Array.from(document.querySelectorAll('script[src]')).forEach(function (s) {
    var raw = s.getAttribute('src');
    if (raw) loadedScriptSrcs.add(raw);
  });

  // ── Click interception ─────────────────────────────────────────
  // Defer to the browser if any of these conditions are true.
  function shouldDefer(e, link) {
    if (e.defaultPrevented) return true;
    if (e.button !== 0) return true;                       // not left-click
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return true;
    if (link.target && link.target !== '' && link.target !== '_self') return true;
    if (link.hasAttribute('download')) return true;
    if (link.dataset.cmNoSpa === 'true') return true;
    var href = link.getAttribute('href');
    if (!href) return true;
    if (href.startsWith('#')) return true;                  // in-page anchor
    if (href.startsWith('javascript:')) return true;
    if (href.startsWith('mailto:') || href.startsWith('tel:')) return true;
    // External origin → real navigation.
    try {
      var u = new URL(link.href, document.baseURI);
      if (u.origin !== window.location.origin) return true;
    } catch (err) { return true; }
    return false;
  }

  document.addEventListener('click', function (e) {
    var link = e.target.closest && e.target.closest('a[href]');
    if (!link) return;
    if (shouldDefer(e, link)) return;

    e.preventDefault();
    navigateTo(link.href, { push: true });
  }, true);

  // Form submissions: respect data-cm-spa-form="true" on a form to opt in,
  // otherwise the browser handles it (since most forms POST and lead off-CM).
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form || form.dataset.cmSpaForm !== 'true') return;
    if (form.method && form.method.toLowerCase() !== 'get') return;
    e.preventDefault();
    var url = new URL(form.action || window.location.href, document.baseURI);
    var fd = new FormData(form);
    fd.forEach(function (v, k) { url.searchParams.set(k, v); });
    navigateTo(url.toString(), { push: true });
  }, true);

  // ── popstate (back/forward) ────────────────────────────────────
  window.addEventListener('popstate', function () {
    navigateTo(window.location.href, { push: false });
  });

  // ── Navigation ─────────────────────────────────────────────────
  var inFlight = null;

  function showLoadingHint() {
    var b = document.body;
    if (!b) return;
    b.classList.add('cm-spa-loading');
  }
  function hideLoadingHint() {
    document.body && document.body.classList.remove('cm-spa-loading');
  }

  function navigateTo(href, opts) {
    if (inFlight) {
      try { inFlight.abort(); } catch (e) {}
    }
    var ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    inFlight = ctrl;

    showLoadingHint();
    fetch(href, {
      credentials: 'same-origin',
      headers: { 'X-CM-SPA': '1', 'Accept': 'text/html' },
      signal: ctrl ? ctrl.signal : undefined,
    })
      .then(function (res) {
        if (!res.ok) throw new Error('CM-SPA fetch failed: ' + res.status);
        return Promise.all([res.text(), Promise.resolve(res.url)]);
      })
      .then(function (pair) {
        var html = pair[0], finalUrl = pair[1];
        var doc = new DOMParser().parseFromString(html, 'text/html');

        // If the new document isn't a CM page (e.g. the user clicked a link
        // out of CM), do a real navigation so they leave the projector view
        // cleanly — fullscreen will exit, which is what the user wants when
        // leaving CM.
        if (!isCMDocument(doc)) {
          window.location.href = finalUrl || href;
          return;
        }

        swapDocument(doc, finalUrl || href, opts);
      })
      .catch(function (err) {
        if (err && err.name === 'AbortError') return;
        // Soft-fail: hand off to a real navigation rather than swallow.
        console.warn('[CM-SPA] navigation fell back to native nav:', err);
        window.location.href = href;
      })
      .finally(function () {
        if (inFlight === ctrl) inFlight = null;
        hideLoadingHint();
      });
  }

  // ── Swap ───────────────────────────────────────────────────────
  function swapDocument(newDoc, finalUrl, opts) {
    // 1. Title.
    if (newDoc.title) document.title = newDoc.title;

    // 2. <body> attributes (data-theme, classes, etc.) — preserve any
    //    `cm-fullscreen` class the existing body already has so the
    //    projector treatment doesn't flicker off mid-swap.
    var fsClass = document.body.classList.contains('cm-fullscreen');
    var newBody = newDoc.body;
    if (newBody) {
      // Copy attributes from the new body to the live body.
      var liveAttrs = Array.from(document.body.attributes).map(function (a) { return a.name; });
      liveAttrs.forEach(function (n) {
        if (n !== 'class') document.body.removeAttribute(n);
      });
      Array.from(newBody.attributes).forEach(function (a) {
        if (a.name === 'class') return;
        document.body.setAttribute(a.name, a.value);
      });
      // Class: take from new body, then re-apply the fullscreen flag.
      document.body.className = newBody.className || '';
      if (fsClass) document.body.classList.add('cm-fullscreen');

      // 3. Body content.
      document.body.innerHTML = newBody.innerHTML;

      var scriptsDone = reexecuteScripts(document.body);
    }

    syncHeadStyles(newDoc);

    if (opts && opts.push) {
      try { history.pushState({ cmSpa: true }, '', finalUrl); } catch (e) {}
    } else {
      try { history.replaceState({ cmSpa: true }, '', finalUrl); } catch (e) {}
    }

    Promise.resolve(scriptsDone).then(function () {
      document.dispatchEvent(new Event('DOMContentLoaded', { bubbles: false }));
      window.dispatchEvent(new Event('cm:navigated'));
    });

    window.scrollTo({ top: 0, behavior: 'instant' in window ? 'instant' : 'auto' });
  }

  function reexecuteScripts(scope) {
    // Three rules:
    //
    // (1) External scripts we've already loaded once: DROP them. Re-running
    //     jQuery/Bootstrap/Select2 re-registers their delegated handlers and
    //     causes double-fire bugs (e.g. Bootstrap modal backdrop glitches).
    //
    // (2) External scripts that are new this swap: execute in document order
    //     with async=false. The HTML spec defaults dynamically-inserted
    //     scripts to async=true (network-arrival order), which breaks
    //     dependency chains like bootstrap-select needing bootstrap loaded
    //     first.
    //
    // (3) Inline scripts: always re-execute, but chain them behind any
    //     preceding external script so inline init can't fire before its
    //     dependency is on the page.
    var scripts = Array.from(scope.querySelectorAll('script'));
    var chain = Promise.resolve();
    scripts.forEach(function (old) {
      var rawSrc = old.getAttribute('src');
      // Rule 1: already-loaded external script — remove without re-running.
      if (rawSrc && loadedScriptSrcs.has(rawSrc)) {
        old.parentNode.removeChild(old);
        return;
      }
      chain = chain.then(function () {
        return new Promise(function (resolve) {
          var fresh = document.createElement('script');
          Array.from(old.attributes).forEach(function (a) {
            fresh.setAttribute(a.name, a.value);
          });
          if (rawSrc) {
            fresh.async = false;
            fresh.onload = function () {
              loadedScriptSrcs.add(rawSrc);
              resolve();
            };
            fresh.onerror = function () { resolve(); }; // don't deadlock on 404
          } else {
            fresh.text = old.textContent;
          }
          old.parentNode.replaceChild(fresh, old);
          if (!rawSrc) resolve();
        });
      });
    });
    return chain;
  }

  function syncHeadStyles(newDoc) {
    // <style> blocks: page-specific. Remove the previous page's tagged
    // styles, then clone in the new page's. We DON'T touch the SPA's own
    // loading-bar style (id="cmSpaStyle") nor any <style> some other script
    // injected mid-session.
    Array.from(document.head.querySelectorAll('style[data-cm-spa-style]'))
      .forEach(function (s) { s.remove(); });
    Array.from(newDoc.head.querySelectorAll('style')).forEach(function (s) {
      var clone = document.createElement('style');
      Array.from(s.attributes).forEach(function (a) { clone.setAttribute(a.name, a.value); });
      clone.setAttribute('data-cm-spa-style', '1');
      clone.textContent = s.textContent;
      document.head.appendChild(clone);
    });

    // <link rel="stylesheet">: framework CSS. Cumulative + deduped by href so
    // each unique sheet is only loaded once. Re-loading them on every swap
    // would cause a flash of unstyled content while the browser re-fetches.
    var existing = new Set(
      Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
        .map(function (l) { return l.href; })
    );
    Array.from(newDoc.querySelectorAll('link[rel="stylesheet"]'))
      .filter(function (l) { return !existing.has(l.href); })
      .forEach(function (l) {
        var clone = document.createElement('link');
        Array.from(l.attributes).forEach(function (a) { clone.setAttribute(a.name, a.value); });
        document.head.appendChild(clone);
      });
  }

  // ── Style: tiny "loading" hint while we fetch the next page ───
  // Doesn't depend on a CSS file — injects once.
  (function injectLoadingStyle() {
    if (document.getElementById('cmSpaStyle')) return;
    var s = document.createElement('style');
    s.id = 'cmSpaStyle';
    // The loading bar uses var(--brand-primary) directly inside the
    // injected CSS string. CSS variables are resolved at use-time, not
    // at injection-time, so the gradient automatically tracks the
    // tenant brand without us re-injecting on every theme/brand swap.
    // Hex fallback (forest) keeps it visible on hosts without our cascade.
    s.textContent =
      'body.cm-spa-loading { cursor: progress; } ' +
      'body.cm-spa-loading::after { ' +
      '  content: ""; position: fixed; top: 0; left: 0; right: 0; ' +
      '  height: 3px; background: linear-gradient(90deg, transparent, var(--brand-primary, #b7925a), transparent); ' +
      '  background-size: 200% 100%; animation: cmSpaBar 1.1s linear infinite; ' +
      '  z-index: 99999; pointer-events: none; ' +
      '} ' +
      '@keyframes cmSpaBar { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }';
    document.head.appendChild(s);
  })();
})();
