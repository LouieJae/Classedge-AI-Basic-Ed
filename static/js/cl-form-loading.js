/* ─────────────────────────────────────────────────────────────────
   cl-form-loading.js — submit lock + spinner UX.

   Opt-in via <form data-cl-loading>. On submit:
     • Disables every submit button in the form
     • Replaces the clicked submit's contents with a spinner + label
     • Locks the form against double-submit (Enter + click + dbl-tap)

   Optional knobs:
     <form data-cl-loading data-cl-loading-label="Creating…">
     <button data-cl-loading-label="Updating…">

   Restores on `pageshow` so users coming back via browser bfcache
   don't see a permanently disabled form.
   ───────────────────────────────────────────────────────────────── */
(function () {
  'use strict';

  var DEFAULT_LABEL = 'Saving…';
  var SPINNER_HTML =
    '<span class="cl-form-spinner" aria-hidden="true"></span>';

  function getLabel(button, form) {
    return (
      button.getAttribute('data-cl-loading-label') ||
      form.getAttribute('data-cl-loading-label') ||
      DEFAULT_LABEL
    );
  }

  function lockButton(btn, label) {
    if (btn._clLocked) return;
    btn._clLocked = true;
    btn._clOriginalHTML = btn.innerHTML;
    btn._clOriginalDisabled = btn.disabled;
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    btn.classList.add('is-loading');
    btn.innerHTML = SPINNER_HTML + '<span class="cl-form-spinner-label">' + label + '</span>';
  }

  function unlockButton(btn) {
    if (!btn._clLocked) return;
    btn._clLocked = false;
    btn.disabled = btn._clOriginalDisabled || false;
    btn.removeAttribute('aria-busy');
    btn.classList.remove('is-loading');
    if (typeof btn._clOriginalHTML === 'string') {
      btn.innerHTML = btn._clOriginalHTML;
    }
  }

  function lockForm(form, clickedSubmit) {
    if (form._clLocked) return false;
    form._clLocked = true;

    var submits = form.querySelectorAll(
      'button[type="submit"], input[type="submit"]'
    );
    submits.forEach(function (s) {
      // Only the clicked one gets the spinner; the rest just go disabled
      // (e.g. a hidden stepper-submit twin). Label-bearing inputs (no innerHTML)
      // get a value swap.
      if (s === clickedSubmit) {
        var label = getLabel(s, form);
        if (s.tagName === 'INPUT') {
          s._clOriginalValue = s.value;
          s.value = label;
          s.disabled = true;
          s.classList.add('is-loading');
          s.setAttribute('aria-busy', 'true');
          s._clLocked = true;
        } else {
          lockButton(s, label);
        }
      } else {
        s.disabled = true;
      }
    });
    return true;
  }

  function unlockForm(form) {
    if (!form._clLocked) return;
    form._clLocked = false;
    var submits = form.querySelectorAll(
      'button[type="submit"], input[type="submit"]'
    );
    submits.forEach(function (s) {
      if (s.tagName === 'INPUT') {
        if (s._clLocked) {
          s.value = s._clOriginalValue || s.value;
          s.disabled = false;
          s.classList.remove('is-loading');
          s.removeAttribute('aria-busy');
          s._clLocked = false;
        }
      } else {
        unlockButton(s);
      }
      // Re-enable any non-clicked submits that we disabled
      if (!s._clOriginalDisabledTouched) s.disabled = false;
    });
  }

  function findClickedSubmit(form, event) {
    var active = document.activeElement;
    if (
      active &&
      form.contains(active) &&
      (active.tagName === 'BUTTON' || active.tagName === 'INPUT') &&
      (active.type === 'submit')
    ) {
      return active;
    }
    if (event && event.submitter) return event.submitter;
    return (
      form.querySelector('button[type="submit"]:not([disabled])') ||
      form.querySelector('input[type="submit"]:not([disabled])')
    );
  }

  function bind(form) {
    if (form._clLoadingBound) return;
    form._clLoadingBound = true;

    form.addEventListener('submit', function (e) {
      // If another submit handler has already locked us (double-tap),
      // block the dupe synchronously.
      if (form._clLocked) {
        e.preventDefault();
        return;
      }
      var clicked = findClickedSubmit(form, e);
      // Defer locking to a microtask so we observe whether any other
      // submit handler (Bootstrap needs-validation, stepper logic,
      // page-specific JS) called preventDefault. Microtasks run after
      // every synchronous handler in the same dispatch, but before the
      // browser starts navigating — so we still lock in time to update
      // the UI on a real submit, and skip the lock on a cancelled one.
      Promise.resolve().then(function () {
        if (e.defaultPrevented) return;
        if (form.checkValidity && !form.checkValidity()) return;
        lockForm(form, clicked);
      });
    });
  }

  function boot() {
    document.querySelectorAll('form[data-cl-loading]').forEach(bind);
  }

  // bfcache restore — when user navigates back, unlock all forms so
  // they're usable again. Without this, the form returns frozen.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      document.querySelectorAll('form[data-cl-loading]').forEach(unlockForm);
    }
  });

  // Re-scan when HTMX or JS injects new forms.
  if ('MutationObserver' in window) {
    var observer = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var m = muts[i];
        for (var j = 0; j < m.addedNodes.length; j++) {
          var n = m.addedNodes[j];
          if (n.nodeType !== 1) continue;
          if (n.matches && n.matches('form[data-cl-loading]')) bind(n);
          if (n.querySelectorAll) {
            n.querySelectorAll('form[data-cl-loading]').forEach(bind);
          }
        }
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
