/* ============================================================================
 * [Classedge LMS] cl-form-guard.js — Smart Form Interceptor.
 *
 * Protects in-flight composition work. If the user has typed into a form but
 * hasn't saved or submitted, any navigation attempt (browser back, tab close,
 * sidebar link click, etc.) is intercepted with a confirmation prompt.
 *
 * Design notes (see audit on 2026-05-21):
 *
 * • Snapshot strategy. On DOMContentLoaded we walk every <form> on the page
 *   and stash the initial value of each input as `el._clInit`. A form is
 *   "dirty" iff at least one of its inputs differs from its snapshot AND the
 *   form has not been submitted. MutationObserver re-snapshots forms inserted
 *   later (htmx swaps, dynamically-added formset rows).
 *
 * • Exemption rules. We DO NOT track:
 *     - <form method="get">  (search/filter forms — submitting is not a save)
 *     - <form data-dirty-exempt> or descendants of [data-dirty-exempt]
 *     - Forms inside .legal-shell (the legal-consent modal that auto-opens
 *       on page load; treating it as dirty would be a confusing UX)
 *     - CSRF, hidden Django formset-management inputs, and submit buttons
 *
 * • Three entry points to navigation:
 *     1. window 'beforeunload' (tab close / external URL / browser back) —
 *        we set returnValue so the browser shows its native prompt. Browsers
 *        ignore custom message text since ~2017 (Chrome 51), so we accept the
 *        generic "Leave site?" wording.
 *     2. document click capture on <a href> — for in-app sidebar/nav links
 *        we preventDefault and show a SweetAlert2 confirm (falls back to
 *        window.confirm if SweetAlert is not loaded for some reason).
 *     3. Bootstrap 'hide.bs.modal' — intercepts X/backdrop/Escape on modals
 *        that contain dirty forms.
 *
 * • AJAX-submit forms. We can't detect "saved" for forms whose submit handler
 *   calls e.preventDefault(); they would stay dirty forever after a save.
 *   Public API: window.ClFormGuard.markClean(form) lets AJAX submitters tell
 *   the guard "this form is saved now". Or add data-dirty-exempt and manage
 *   the prompt yourself.
 *
 * • Fetch-only critical actions (social media inbox sends, question-batch
 *   save, notification mark-all-read). These have no <form>; the guard never
 *   sees them. The opt-in escape hatch is [data-fetch-dirty="true"] on any
 *   element — when present, the guard treats the page as dirty until the
 *   attribute flips back to "false" or is removed.
 * ============================================================================ */
(function () {
  'use strict';

  // --- State ---------------------------------------------------------------
  const TRACKED = new WeakSet();          // forms we've snapshotted
  const SUBMITTED = new WeakSet();        // forms that submitted naturally this turn
  let bypassOnce = false;                 // suppress beforeunload after user OK'd a SweetAlert "Leave"
  const PROMPT_TEXT = 'You have unsaved changes. If you leave now, your work will be lost.';

  // --- Exemption -----------------------------------------------------------
  function isExempt(form) {
    if (!form || form.tagName !== 'FORM') return true;
    const method = (form.getAttribute('method') || 'get').toLowerCase();
    if (method !== 'post') return true;
    if (form.hasAttribute('data-dirty-exempt')) return true;
    if (form.closest('[data-dirty-exempt]')) return true;
    if (form.closest('.legal-shell, .legal-modal, [data-legal-modal]')) return true;
    return false;
  }

  function isTrackableInput(el) {
    if (!el || !el.name) return false;
    if (el.disabled) return false;
    const t = (el.type || el.tagName).toLowerCase();
    if (t === 'submit' || t === 'button' || t === 'reset' || t === 'image') return false;
    // Skip Django's CSRF token + formset-management fields — they're stable.
    if (el.name === 'csrfmiddlewaretoken') return false;
    if (el.name && el.name.startsWith('__prefix__')) return false;
    return true;
  }

  // --- Snapshot / dirty detection ------------------------------------------
  function readValue(el) {
    const t = (el.type || el.tagName).toLowerCase();
    if (t === 'checkbox' || t === 'radio') return el.checked ? '1' : '0';
    if (t === 'file') return el.files && el.files.length ? '__file:' + el.files.length : '';
    if (t === 'select-multiple' || (el.tagName === 'SELECT' && el.multiple)) {
      return Array.from(el.selectedOptions).map(o => o.value).join('|');
    }
    return el.value == null ? '' : String(el.value);
  }

  function snapshotForm(form) {
    if (isExempt(form) || TRACKED.has(form)) return;
    Array.from(form.elements || []).forEach((el) => {
      if (!isTrackableInput(el)) return;
      el._clInit = readValue(el);
    });
    TRACKED.add(form);
  }

  function isFormDirty(form) {
    if (isExempt(form)) return false;
    if (SUBMITTED.has(form)) return false;
    if (!TRACKED.has(form)) return false;
    return Array.from(form.elements || []).some((el) => {
      if (!isTrackableInput(el)) return false;
      if (typeof el._clInit === 'undefined') return false;
      return readValue(el) !== el._clInit;
    });
  }

  function pageIsDirty() {
    const forms = document.querySelectorAll('form');
    for (let i = 0; i < forms.length; i++) {
      if (isFormDirty(forms[i])) return true;
    }
    // Fetch-only critical actions can flag dirty without a <form>.
    if (document.querySelector('[data-fetch-dirty="true"]')) return true;
    return false;
  }

  // --- beforeunload (tab close, external nav, address-bar URL change) -----
  // Browsers since 2017 ignore the returned string and show their own generic
  // prompt — we cannot intercept these with SweetAlert2 because the page is
  // about to die. We still set returnValue + return the string so SOME
  // confirmation appears (better the native prompt than silent data loss).
  // The browser BACK button is handled separately below via the History API,
  // which DOES let us show our own modal.
  window.addEventListener('beforeunload', function (e) {
    if (bypassOnce) { bypassOnce = false; return; }
    if (!pageIsDirty()) return;
    e.preventDefault();
    e.returnValue = PROMPT_TEXT;
    return PROMPT_TEXT;
  });

  // --- Back-button guard (History API) ------------------------------------
  // `beforeunload` is the wrong tool for the back button — the browser
  // hijacks the message and shows its generic dialog. Instead we push a
  // sentinel state onto history as soon as the page becomes dirty; clicking
  // back then pops the sentinel and fires `popstate` on the SAME page,
  // giving us a chance to intercept and show SweetAlert2.
  //
  // Flow:
  //   load                  → history: […, prev, page]
  //   user types            → push sentinel → […, prev, page, GUARD]
  //   user clicks back      → browser pops GUARD → popstate fires at `page`
  //                           we re-push GUARD (URL unchanged) + show modal
  //   user picks "Leave"    → bypass next beforeunload, history.go(-2)
  //                           → navigates back to `prev` (same target the
  //                           original back press wanted)
  //   user picks "Stay"     → URL is back at GUARD, nothing else changes
  let guardPushed = false;
  const GUARD_MARKER = '__clFormGuard';

  function armBackGuard() {
    if (guardPushed) return;
    try {
      history.pushState({ [GUARD_MARKER]: true }, '', window.location.href);
      guardPushed = true;
    } catch (_) { /* pushState can throw on file:// or sandboxed contexts */ }
  }

  // First user input (keystroke, checkbox toggle, select change) on any form
  // arms the back guard. Cheaper than polling pageIsDirty on a timer; we
  // accept a false-positive guard push if the user just clicks-then-undoes
  // (the popstate handler still does the real dirty check before prompting).
  document.addEventListener('input', armBackGuard, true);
  document.addEventListener('change', armBackGuard, true);

  window.addEventListener('popstate', function (e) {
    if (!guardPushed) return;          // we never armed → not our event
    if (bypassOnce) {                  // user already confirmed "Leave"
      // history.go(-2) below will fire one extra popstate as it traverses
      // the same-document GUARD → page hop; consume it and let the second
      // hop (page → prev, different document) proceed to beforeunload.
      return;
    }

    if (!pageIsDirty()) {
      // Form became clean before user clicked back. Honor their intent —
      // we're already at the `page` entry (one below GUARD), so triggering
      // history.back() once now takes them to `prev`.
      guardPushed = false;
      bypassOnce = true;
      history.back();
      return;
    }

    // Re-push the sentinel so the URL stays put while we ask. Without this
    // the user would see the URL flicker for a moment.
    try { history.pushState({ [GUARD_MARKER]: true }, '', window.location.href); }
    catch (_) {}
    guardPushed = true;

    confirmLeave(function () {
      guardPushed = false;
      bypassOnce = true;
      // From GUARD (top of stack) we need to traverse two entries to land
      // on the original `prev` (GUARD → page → prev). The page → prev hop
      // is a real document navigation, so beforeunload would fire — but
      // bypassOnce above suppresses it.
      history.go(-2);
    });
  });

  // --- Form lifecycle ------------------------------------------------------
  // Mark dirty-tracked forms as submitted when the native submit event fires;
  // this clears dirty so the subsequent POST → redirect doesn't trip the
  // beforeunload prompt. Capture phase so we run before app submit handlers
  // possibly call e.preventDefault().
  document.addEventListener('submit', function (e) {
    const form = e.target;
    if (form && form.tagName === 'FORM') SUBMITTED.add(form);
  }, true);

  // --- In-app link interception --------------------------------------------
  function shouldGuardLink(a) {
    if (!a || !a.href) return false;
    if (a.hasAttribute('data-dirty-exempt')) return false;
    if (a.target && a.target !== '_self') return false;       // _blank etc. don't unload this tab
    if (a.hasAttribute('download')) return false;
    const href = a.getAttribute('href') || '';
    if (!href) return false;
    if (href.startsWith('#')) return false;                     // same-page anchor
    if (href.startsWith('javascript:')) return false;
    if (href.startsWith('mailto:') || href.startsWith('tel:')) return false;
    // Same-document anchor with full path? compare against current location.
    try {
      const url = new URL(a.href, window.location.href);
      const samePath = url.origin === window.location.origin
                    && url.pathname === window.location.pathname
                    && url.search === window.location.search;
      if (samePath && url.hash && url.hash !== window.location.hash) return false;
    } catch (_) { /* malformed href — fall through and guard */ }
    return true;
  }

  function confirmLeave(onLeave, opts) {
    const confirmText = (opts && opts.confirmText) || 'Leave page';
    if (window.Swal && typeof window.Swal.fire === 'function') {
      window.Swal.fire({
        icon: 'warning',
        title: 'Unsaved changes',
        text: PROMPT_TEXT,
        showCancelButton: true,
        confirmButtonText: confirmText,
        cancelButtonText: 'Stay',
        reverseButtons: true,
        focusCancel: true,
        // SweetAlert respects the brand-primary token via inline CSS variable
        // on the OK button; matches the rest of the LMS confirm dialogs.
        confirmButtonColor: getComputedStyle(document.documentElement)
          .getPropertyValue('--brand-primary').trim() || '#1b4332',
      }).then((res) => { if (res && res.isConfirmed) onLeave(); });
    } else {
      if (window.confirm(PROMPT_TEXT)) onLeave();
    }
  }

  document.addEventListener('click', function (e) {
    if (!pageIsDirty()) return;
    // Honor modifier-click / middle-click (those open new tab/window).
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    const a = e.target && e.target.closest && e.target.closest('a[href]');
    if (!a || !shouldGuardLink(a)) return;
    e.preventDefault();
    e.stopPropagation();
    const href = a.href;
    confirmLeave(function () {
      bypassOnce = true;
      window.location.href = href;
    });
  }, true);

  // --- Keyboard reload (F5, Ctrl/Cmd-R, Ctrl/Cmd-Shift-R) -----------------
  // The browser UI reload button is out of reach (it lives in browser chrome
  // and bypasses page-level event listeners — we can only show the generic
  // beforeunload prompt for it). But the *keyboard* reload shortcuts fire
  // a regular keydown that we CAN preventDefault, so we route those through
  // SweetAlert2 just like the back button.
  //
  // What this catches:    F5, Ctrl/Cmd+R, Ctrl/Cmd+Shift+R (hard reload).
  // What this can't catch: browser's UI reload button, address-bar enter on
  //                        the same URL, right-click → Reload menu.
  document.addEventListener('keydown', function (e) {
    const key = e.key;
    const isF5 = key === 'F5';
    const isCmdR = (e.metaKey || e.ctrlKey) && (key === 'r' || key === 'R');
    if (!isF5 && !isCmdR) return;
    if (!pageIsDirty()) return;
    e.preventDefault();
    e.stopPropagation();
    confirmLeave(function () {
      bypassOnce = true;
      window.location.reload();
    }, { confirmText: 'Reload' });
  }, true);

  // --- Bootstrap modal dismissal -------------------------------------------
  // The legal-consent modal is exempt (handled by isExempt). Other modals
  // (Bootstrap dialogs containing dirty forms) get an X/backdrop/Escape guard
  // via the hide.bs.modal event.
  document.addEventListener('hide.bs.modal', function (e) {
    const modal = e.target;
    if (!modal) return;
    if (modal.matches('.legal-shell, .legal-modal, [data-legal-modal]')) return;
    if (modal.hasAttribute('data-dirty-exempt')) return;
    const forms = modal.querySelectorAll('form');
    const dirty = Array.from(forms).some(isFormDirty);
    if (!dirty) return;
    e.preventDefault();
    confirmLeave(function () {
      // User accepted — mark the modal's forms clean so Bootstrap can close.
      Array.from(forms).forEach((f) => SUBMITTED.add(f));
      if (window.bootstrap && window.bootstrap.Modal) {
        const inst = window.bootstrap.Modal.getInstance(modal);
        if (inst) inst.hide();
      }
    });
  });

  // --- Initial snapshot + MutationObserver ---------------------------------
  function snapshotAll(root) {
    const scope = (root && root.querySelectorAll) ? root : document;
    scope.querySelectorAll('form').forEach(snapshotForm);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { snapshotAll(document); });
  } else {
    snapshotAll(document);
  }

  // Snapshot any <form> elements added later (htmx swap-in, JS-injected
  // dialogs, formset row "Add" button). Throttled scan since rapid mutations
  // can fire dozens of records per tick.
  let scanPending = false;
  const observer = new MutationObserver(function () {
    if (scanPending) return;
    scanPending = true;
    requestAnimationFrame(function () {
      scanPending = false;
      snapshotAll(document);
    });
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  // --- Public API ----------------------------------------------------------
  // Use from AJAX-submitting code:
  //   ClFormGuard.markClean(formEl)   — call after save succeeds.
  //   ClFormGuard.markDirty(formEl)   — force-flag a form as dirty.
  //   ClFormGuard.resnapshot(formEl)  — re-baseline after a programmatic value change.
  //   ClFormGuard.suppressNext()      — disable the next beforeunload prompt.
  //   ClFormGuard.isDirty()           — boolean check for callers.
  window.ClFormGuard = {
    markClean: function (form) {
      if (!form) return;
      SUBMITTED.add(form);
      Array.from(form.elements || []).forEach((el) => {
        if (isTrackableInput(el)) el._clInit = readValue(el);
      });
    },
    markDirty: function (form) {
      if (!form) return;
      SUBMITTED.delete(form);
      Array.from(form.elements || []).forEach((el) => {
        if (isTrackableInput(el)) el._clInit = '__forced_dirty__';
      });
    },
    resnapshot: function (form) {
      if (!form) return;
      TRACKED.delete(form);
      SUBMITTED.delete(form);
      snapshotForm(form);
    },
    suppressNext: function () { bypassOnce = true; },
    isDirty: pageIsDirty,
    _isFormDirty: isFormDirty,  // exposed for tests / debug
  };
})();
