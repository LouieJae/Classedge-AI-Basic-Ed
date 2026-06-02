/* [Classedge LMS] cl-edit-inline — reusable click-to-edit engine.
 * ----------------------------------------------------------------------
 * Attach to any element with `.cl-edit` to make its text content
 * inline-editable. Clicking the element replaces the text with an
 * <input> that auto-focuses + selects-all; Enter or blur saves via
 * PATCH; Esc cancels.
 *
 * Markup:
 *   <span class="cl-edit"
 *         data-endpoint="/assessment/rename/{{ activity.local_id }}/"
 *         data-field="activity_name"
 *         data-min="2"
 *         data-max="120"
 *         data-label="Activity name">
 *     Quiz 1 — Variables & Loops
 *   </span>
 *
 * Endpoint contract:
 *   PATCH <data-endpoint>
 *   Content-Type: application/json
 *   X-CSRFToken: <csrf>
 *   Body: { "<data-field>": "<new value>" }
 *
 *   Success → 200 { ok: true, value: "<sanitized value>" }
 *   Client error → 400 { ok: false, error: "<human-readable message>" }
 *   Conflict → 409 { ok: false, error: "Updated by ...", value: "<authoritative value>" }
 *
 * Hooks:
 *   element.addEventListener('cl-edit:saved',  (e) => …)  // detail.value
 *   element.addEventListener('cl-edit:error',  (e) => …)  // detail.error
 *
 * Dependencies: window.clToast (templates/includes/_toast.html). If
 * clToast isn't available, the engine logs to console as a fallback.
 */
(function () {
  'use strict';
  if (window.ClEditInline && window.ClEditInline.__loaded) return;

  function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function getCsrf() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  function toast(msg, type) {
    if (typeof window.clToast === 'function') {
      window.clToast(msg, type || 'success');
    } else {
      console.info('[cl-edit-inline]', type || 'info', msg);
    }
  }

  function attach(el) {
    if (!el || el.__clEditBound) return;
    el.__clEditBound = true;

    // Always render as a button-ish affordance so keyboard users can
    // tab to the element and press Enter to start editing.
    el.setAttribute('role', el.getAttribute('role') || 'button');
    el.setAttribute('tabindex', el.getAttribute('tabindex') || '0');
    el.setAttribute(
      'title',
      el.getAttribute('title') ||
        'Click to edit ' + (el.dataset.label || el.dataset.field || 'this field')
    );

    // Capture-phase listener so we run BEFORE any wrapping card / <a>
     // / <button> bubble-phase handler — and crucially before the
     // browser follows a parent <a href="...">. Without this, clicking
     // the .cl-edit inside a card-link element navigates the page
     // before our input can take focus.
    el.addEventListener('click', function (e) {
      // While editing, ANY click inside the .cl-edit (including the
      // input child where the user positions their cursor) must both
      // stopPropagation AND preventDefault — otherwise the click
      // event's default action on the wrapping <a href=""> ancestor
      // fires (navigation). Cursor positioning inside the <input>
      // is handled by mousedown, so blocking click's default here
      // is safe.
      if (el.classList.contains('is-editing')) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      // Only intercept when the click is on the .cl-edit text itself,
      // not on nested children.
      if (e.target !== el) return;
      e.preventDefault();
      e.stopPropagation();
      startEdit(el);
    }, true);
    // Mousedown gets stopPropagation only (no preventDefault) so the
    // input still receives focus + cursor placement natively. Some
    // card components navigate on mousedown for snappier feel — this
    // blocks that path too.
    el.addEventListener('mousedown', function (e) {
      if (el.classList.contains('is-editing')) {
        e.stopPropagation();
        return;
      }
      if (e.target !== el) return;
      e.stopPropagation();
    }, true);
    // dblclick (selecting a word) and auxclick (middle-click) also
    // emit default actions that anchor ancestors can swallow. Block
    // them while editing.
    el.addEventListener('dblclick', function (e) {
      if (el.classList.contains('is-editing')) {
        e.stopPropagation();
      }
    }, true);
    el.addEventListener('auxclick', function (e) {
      if (el.classList.contains('is-editing')) {
        e.preventDefault();
        e.stopPropagation();
      }
    }, true);
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        if (e.target !== el) return;
        e.preventDefault();
        e.stopPropagation();
        startEdit(el);
      }
    });
  }

  function startEdit(el) {
    if (el.classList.contains('is-editing')) return;

    var original = el.textContent.trim();
    var minLen = parseInt(el.dataset.min || '1', 10);
    var maxLen = parseInt(el.dataset.max || '255', 10);

    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'cl-edit-input';
    input.value = original;
    input.setAttribute('aria-label', el.dataset.label || el.dataset.field || 'Edit value');
    input.minLength = minLen;
    input.maxLength = maxLen;

    // Stash the original on the input so commit/cancel can restore it.
    input.dataset.original = original;

    el.classList.add('is-editing');
    el.textContent = '';
    el.appendChild(input);
    input.focus();
    input.select();

    var committed = false;

    function cancel() {
      if (committed) return;
      committed = true;
      revert(el, original);
    }

    function commit() {
      if (committed) return;
      committed = true;
      var next = input.value.trim();
      if (next === original) {
        revert(el, original);
        return;
      }
      if (next.length < minLen) {
        toast('Value must be at least ' + minLen + ' character' + (minLen > 1 ? 's' : ''), 'danger');
        revert(el, original);
        return;
      }
      if (next.length > maxLen) {
        toast('Value can be at most ' + maxLen + ' characters', 'danger');
        revert(el, original);
        return;
      }
      save(el, next, original);
    }

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        commit();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        cancel();
      }
    });
    // blur saves (matches Linear/Notion behavior). Wrapped in
    // setTimeout so an Enter keydown's blur fires after `committed`
    // is set by the keydown handler.
    input.addEventListener('blur', function () {
      setTimeout(commit, 0);
    });
  }

  function revert(el, value) {
    el.classList.remove('is-editing', 'is-saving');
    el.textContent = value;
  }

  function save(el, value, original) {
    var endpoint = el.dataset.endpoint;
    var field = el.dataset.field;
    if (!endpoint || !field) {
      console.error('[cl-edit-inline] missing data-endpoint or data-field on', el);
      revert(el, original);
      return;
    }

    el.classList.add('is-saving');
    // Keep the input visible during the request so the user can see
    // their pending value; we re-attach the text node only after the
    // server responds.
    var input = el.querySelector('.cl-edit-input');
    if (input) input.disabled = true;

    var payload = {};
    payload[field] = value;

    fetch(endpoint, {
      method: 'PATCH',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(payload)
    })
      .then(function (res) {
        return res
          .json()
          .catch(function () { return { ok: res.ok, error: 'Unexpected server response' }; })
          .then(function (body) { return { status: res.status, body: body }; });
      })
      .then(function (r) {
        if (r.status >= 200 && r.status < 300) {
          var finalValue = (r.body && r.body.value) || value;
          revert(el, finalValue);
          toast(
            (el.dataset.label || 'Value') + ' saved',
            'success'
          );
          try {
            el.dispatchEvent(new CustomEvent('cl-edit:saved', {
              detail: { value: finalValue, field: field }
            }));
          } catch (_) {}
        } else if (r.status === 409 && r.body && r.body.value) {
          // Concurrency: someone else edited this. Revert to the
          // server's authoritative value and tell the user.
          revert(el, r.body.value);
          toast(
            r.body.error || 'Updated by another user — your change was discarded.',
            'warning'
          );
          try {
            el.dispatchEvent(new CustomEvent('cl-edit:error', {
              detail: { status: 409, error: r.body.error }
            }));
          } catch (_) {}
        } else {
          revert(el, original);
          var msg = (r.body && r.body.error) ||
            'Could not save ' + (el.dataset.label || field).toLowerCase() + '.';
          toast(msg, 'danger');
          try {
            el.dispatchEvent(new CustomEvent('cl-edit:error', {
              detail: { status: r.status, error: msg }
            }));
          } catch (_) {}
        }
      })
      .catch(function (err) {
        revert(el, original);
        toast('Network error — please try again.', 'danger');
        console.error('[cl-edit-inline] save failed:', err);
      });
  }

  function init() {
    $$('.cl-edit').forEach(attach);

    // Auto-bind future .cl-edit elements added via HTMX, DataTables,
    // or any JS-rendered list.
    if (window.MutationObserver) {
      try {
        new MutationObserver(function (records) {
          records.forEach(function (rec) {
            rec.addedNodes && rec.addedNodes.forEach(function (n) {
              if (n.nodeType !== 1) return;
              if (n.matches && n.matches('.cl-edit')) attach(n);
              if (n.querySelectorAll) n.querySelectorAll('.cl-edit').forEach(attach);
            });
          });
        }).observe(document.body, { childList: true, subtree: true });
      } catch (_) {}
    }
  }

  window.ClEditInline = {
    __loaded: true,
    bind: attach,
    rebind: function () { init(); }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
