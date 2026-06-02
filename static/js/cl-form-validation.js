/* [Classedge LMS] Global inline form validation
 * ----------------------------------------------------------------------
 * Drop-in inline validation for every <form> on the page. Auto-binds on
 * DOMContentLoaded and also watches the DOM for forms inserted later
 * (modals, htmx swaps, etc.).
 *
 * Per-field behaviour:
 *   • On blur — validate; show message if invalid.
 *   • On input/change — re-validate ONLY if the field is already flagged
 *     invalid (clears the message as the user fixes it; never yells while
 *     they're still typing their first character).
 *   • On submit — validate every field; prevent submit + focus the first
 *     invalid one.
 *
 * Messages embed the field's visible label so users see "Course name is
 * required." instead of the generic browser default. Labels are sourced
 * from <label for="id">, ancestor <label>, aria-label, aria-labelledby,
 * placeholder, or a humanised version of the `name` attribute.
 *
 * Inline feedback is rendered into a `<div class="cl-field-feedback">`
 * appended to the field's wrapper (.field / .form-group / .cl-field) so
 * the `.is-invalid ~ .cl-field-feedback` reveal rule fires even when
 * Select2/bootstrap-select wedge a chip between the input and the slot.
 *
 * Opt-out: add `data-cl-no-validate` to a <form>, or `formnovalidate` to
 * a submit button, or `data-cl-skip-validation` to a single field.
 *
 * Public API:
 *   window.ClFormValidation.bindForm(form)
 *   window.ClFormValidation.bindAll()
 *   window.ClFormValidation.validateField(input, { force })
 *   window.ClFormValidation.validateForm(form)  // returns true/false
 */
(function () {
  'use strict';
  if (window.ClFormValidation && window.ClFormValidation.__loaded) return;

  var FORM_BOUND = '__clFormValidationBound';

  function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  // ─── Label resolution ──────────────────────────────────────────────
  function humanise(name) {
    if (!name) return '';
    return name.replace(/[_-]+/g, ' ')
               .replace(/\bid\b/i, '')
               .trim()
               .replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  }

  function textOfLabel(labelEl, input) {
    // Pull the label's text content but strip away the input's own value
    // and any trailing colon / asterisk decorations.
    var clone = labelEl.cloneNode(true);
    clone.querySelectorAll('input, select, textarea, .cl-field-feedback, .invalid-feedback').forEach(function (n) { n.remove(); });
    var text = (clone.textContent || '').replace(/\s+/g, ' ').trim();
    text = text.replace(/[:*]+$/g, '').trim();
    return text;
  }

  function resolveLabel(el) {
    var doc = el.ownerDocument || document;
    // 1. <label for="id">
    if (el.id) {
      var byFor = doc.querySelector('label[for="' + (window.CSS && CSS.escape ? CSS.escape(el.id) : el.id) + '"]');
      if (byFor) {
        var t = textOfLabel(byFor, el);
        if (t) return t;
      }
    }
    // 2. Ancestor <label>
    var ancestor = el.closest('label');
    if (ancestor) {
      var t2 = textOfLabel(ancestor, el);
      if (t2) return t2;
    }
    // 3. aria-labelledby
    var labelledby = el.getAttribute('aria-labelledby');
    if (labelledby) {
      var parts = labelledby.split(/\s+/).map(function (id) {
        var n = doc.getElementById(id);
        return n ? (n.textContent || '').trim() : '';
      }).filter(Boolean);
      if (parts.length) return parts.join(' ');
    }
    // 4. aria-label
    var aria = el.getAttribute('aria-label');
    if (aria) return aria.trim();
    // 5. placeholder
    if (el.placeholder) return el.placeholder.trim();
    // 6. humanise the name/id
    return humanise(el.name || el.id || 'This field');
  }

  // ─── Message composition ──────────────────────────────────────────
  function composeMessage(el, label) {
    var v = el.validity;
    if (!v) return el.validationMessage || (label + ' is invalid.');
    if (v.valueMissing) {
      if (el.tagName === 'SELECT') return 'Please select ' + label.toLowerCase() + '.';
      if (el.type === 'checkbox')  return 'Please check ' + label.toLowerCase() + '.';
      return label + ' is required.';
    }
    if (v.typeMismatch) {
      if (el.type === 'email') return 'Enter a valid email address for ' + label + '.';
      if (el.type === 'url')   return 'Enter a valid URL for ' + label + '.';
      return label + ' has the wrong format.';
    }
    if (v.tooShort)  return label + ' must be at least ' + el.minLength + ' characters.';
    if (v.tooLong)   return label + ' must be at most ' + el.maxLength + ' characters.';
    if (v.rangeUnderflow) return label + ' must be ' + el.min + ' or greater.';
    if (v.rangeOverflow)  return label + ' must be ' + el.max + ' or less.';
    if (v.stepMismatch)   return label + ' must match the required step.';
    if (v.patternMismatch) {
      return el.title ? (label + ' — ' + el.title) : (label + ' is invalid.');
    }
    if (v.badInput) return 'Enter a valid value for ' + label + '.';
    return el.validationMessage || (label + ' is invalid.');
  }

  // ─── Feedback slot management ─────────────────────────────────────
  // Resolution order:
  //   1. An existing `.cl-field-feedback` inside the wrapper (our slot).
  //   2. Any element flagged `[data-feedback-for="<name>"]`.
  //   3. An existing Bootstrap `.invalid-feedback` inside the wrapper —
  //      template authors often pre-write a custom message; we reuse it
  //      and treat its initial text as the static fallback rather than
  //      injecting a duplicate.
  //   4. Otherwise, lazily create a `.cl-field-feedback` slot.
  function ensureFeedback(el) {
    if (el.dataset.clSkipValidation === '' || el.dataset.clSkipValidation === 'true') return null;
    var name = el.name || el.id;
    var wrap = el.closest('.field, .form-group, .cl-field') || el.parentNode;
    if (!wrap) return null;
    var slot = wrap.querySelector(':scope > .cl-field-feedback');
    if (!slot && name) {
      var byAttr = (el.form || document).querySelector('[data-feedback-for="' + name + '"]');
      if (byAttr) slot = byAttr;
    }
    if (!slot) {
      slot = wrap.querySelector(':scope > .invalid-feedback');
      if (slot && slot.textContent && !slot.dataset.clDefault) {
        // Remember the template-authored copy so we can restore it when
        // the engine has no better browser-supplied message.
        slot.dataset.clDefault = slot.textContent.trim();
      }
    }
    if (!slot) {
      slot = document.createElement('div');
      slot.className = 'invalid-feedback cl-field-feedback';
      if (name) slot.setAttribute('data-feedback-for', name);
      wrap.appendChild(slot);
    }
    return slot;
  }

  function isCandidate(el) {
    if (!el || !el.tagName) return false;
    var tag = el.tagName;
    if (tag !== 'INPUT' && tag !== 'SELECT' && tag !== 'TEXTAREA') return false;
    if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button' || el.type === 'reset' || el.type === 'image') return false;
    if (el.disabled) return false;
    if (el.dataset && (el.dataset.clSkipValidation === '' || el.dataset.clSkipValidation === 'true')) return false;
    return typeof el.checkValidity === 'function';
  }

  function validateField(el, opts) {
    opts = opts || {};
    if (!isCandidate(el)) return true;
    var valid = el.checkValidity();
    var slot = ensureFeedback(el);
    if (!valid) {
      el.classList.add('is-invalid');
      el.setAttribute('aria-invalid', 'true');
      if (slot) {
        var label = resolveLabel(el);
        // Prefer a template-authored message ("Please select a term.")
        // when present — those are usually tuned to the field's domain
        // and read more naturally than our generic compose. Fall back
        // to the engine-composed message otherwise.
        slot.textContent = slot.dataset.clDefault || composeMessage(el, label);
      }
    } else if (opts.force || el.classList.contains('is-invalid')) {
      el.classList.remove('is-invalid');
      el.removeAttribute('aria-invalid');
      // Leave a template-authored message in place for future invalidity;
      // only clear engine-generated slot content.
      if (slot && !slot.dataset.clDefault) slot.textContent = '';
    }
    return valid;
  }

  function validateForm(form) {
    var fields = $$('input, select, textarea', form).filter(isCandidate);
    var firstInvalid = null;
    fields.forEach(function (el) {
      if (!validateField(el, { force: true }) && !firstInvalid) firstInvalid = el;
    });
    if (firstInvalid) {
      try { firstInvalid.focus({ preventScroll: false }); } catch (_) {}
      try { firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (_) {}
      return false;
    }
    return true;
  }

  function bindForm(form) {
    if (!form || form[FORM_BOUND]) return;
    if (form.hasAttribute('data-cl-no-validate')) return;
    form[FORM_BOUND] = true;

    // Mark fields as "touched" when the user actually types or changes
    // the value. Prefilled fields on an update page stay untouched until
    // the user edits them, so a stray blur (Select2 dropdown open/close,
    // tabbing past a field, etc.) won't paint them red.
    var markTouched = function (ev) {
      var el = ev.target;
      if (!isCandidate(el)) return;
      el.dataset.clTouched = '1';
    };
    form.addEventListener('input', markTouched, true);
    form.addEventListener('change', markTouched, true);

    // Live per-field validation
    var liveHandler = function (ev) {
      var el = ev.target;
      if (!isCandidate(el)) return;
      var alreadyInvalid = el.classList.contains('is-invalid');
      // On input: only re-check if already showing an error (so we clear
      // it as the user types) — never trip a fresh error mid-keystroke.
      if (ev.type === 'input' && !alreadyInvalid) return;
      // On blur: skip fields the user never touched. The submit guard
      // will catch them later if they're still invalid.
      if (ev.type === 'blur' && el.dataset.clTouched !== '1' && !alreadyInvalid) return;
      validateField(el, { force: ev.type === 'blur' });
    };
    form.addEventListener('blur', liveHandler, true);
    form.addEventListener('input', liveHandler, true);
    form.addEventListener('change', liveHandler, true);

    // Submit guard — but only if the form hasn't opted out via novalidate
    // semantics. We respect `formnovalidate` on the submitter so a "Save
    // draft"-style button can bypass full validation when needed.
    // Bubble phase so component-level handlers (e.g. cl-stepper which
    // navigates to the offending step) get to react first.
    form.addEventListener('submit', function (ev) {
      var submitter = ev.submitter || null;
      if (submitter && submitter.hasAttribute('formnovalidate')) return;
      if (form.hasAttribute('data-cl-no-validate')) return;
      if (!validateForm(form)) {
        ev.preventDefault();
        form.classList.add('was-validated');
      }
    });
  }

  function bindAll(root) {
    $$('form', root || document).forEach(bindForm);
  }

  function init() {
    bindAll();
    // Watch for forms added later (modals, htmx, etc.)
    if (window.MutationObserver) {
      var mo = new MutationObserver(function (records) {
        records.forEach(function (r) {
          r.addedNodes && r.addedNodes.forEach(function (n) {
            if (n.nodeType !== 1) return;
            if (n.tagName === 'FORM') bindForm(n);
            else if (n.querySelectorAll) n.querySelectorAll('form').forEach(bindForm);
          });
        });
      });
      mo.observe(document.body, { childList: true, subtree: true });
    }
  }

  window.ClFormValidation = {
    __loaded: true,
    bindForm: bindForm,
    bindAll: bindAll,
    validateField: validateField,
    validateForm: validateForm,
    resolveLabel: resolveLabel,
    composeMessage: composeMessage
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.addEventListener('cm:navigated', init);
})();
