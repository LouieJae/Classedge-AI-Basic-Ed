/* [Classedge LMS] Reusable multi-step form engine — cl-stepper
 * ----------------------------------------------------------------------
 * Attach to any <form data-cl-stepper> that has children of the form:
 *
 *   <section class="cl-step" data-step="basics" data-step-title="Basics">…</section>
 *   <section class="cl-step" data-step="schedule" data-step-title="Schedule">…</section>
 *   <section class="cl-step" data-step="behavior" data-step-title="Behavior">…</section>
 *   <section class="cl-step" data-step="review" data-step-title="Review">…</section>
 *
 * The engine handles:
 *   • Show/hide active step
 *   • Step indicator (progress dots + connector line)
 *   • Per-step Bootstrap validation before "Next"
 *   • Optional review-step auto-population from form values
 *   • Prev/Next/Submit footer wiring
 *   • Conditional fields inside steps stay unchanged — they continue to
 *     show/hide based on their own checkbox listeners (out of scope here)
 *
 * Hooks:
 *   window.ClStepper.bind(formEl)
 *   formEl.addEventListener('cl-stepper:change',   (e) => …)  // e.detail = { from, to, total }
 *   formEl.addEventListener('cl-stepper:reachreview', (e) => …) // fires when user lands on a [data-step-review] step
 *
 * Why no backend changes: every step's <input> stays in the DOM; only
 * display is toggled. The final POST sends the union of all fields.
 */
(function () {
  'use strict';
  if (window.ClStepper && window.ClStepper.__loaded) return;

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function visibleInputsIn(step) {
    return $$('input, select, textarea', step).filter(function (el) {
      if (el.type === 'hidden') return false;
      if (el.disabled) return false;
      // Skip inputs inside conditional sub-panels (e.g. "Remedial
      // students" panel that's display:none until its checkbox is
      // ticked). Walk up to the step boundary; if any ancestor BETWEEN
      // input and step is hidden, skip. We deliberately don't check
      // the step itself — at final-submit validation time the step is
      // display:none but its inputs are still real and must be checked.
      var node = el.parentNode;
      while (node && node !== step) {
        var cs = window.getComputedStyle(node);
        if (cs.display === 'none' || cs.visibility === 'hidden') return false;
        node = node.parentNode;
      }
      return true;
    });
  }

  // Delegate per-field validation to the global cl-form-validation
  // engine when available so the user sees the same label-prefixed
  // messages everywhere. The fallback path lets this file work even when
  // cl-form-validation.js hasn't loaded yet (e.g. an old base template).
  function setFieldValidity(el, force) {
    if (window.ClFormValidation && window.ClFormValidation.validateField) {
      return window.ClFormValidation.validateField(el, { force: !!force });
    }
    if (!el.checkValidity) return true;
    var valid = el.checkValidity();
    if (!valid) {
      el.classList.add('is-invalid');
    } else if (force || el.classList.contains('is-invalid')) {
      el.classList.remove('is-invalid');
    }
    return valid;
  }

  function isStepValid(step) {
    var inputs = visibleInputsIn(step);
    var firstInvalid = null;
    inputs.forEach(function (el) {
      if (!setFieldValidity(el, true) && !firstInvalid) firstInvalid = el;
    });
    if (firstInvalid) {
      firstInvalid.focus({ preventScroll: false });
      try { firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (_) {}
      return false;
    }
    return true;
  }

  function attach(form) {
    if (!form || form.__clStepperBound) return;
    form.__clStepperBound = true;

    // The global engine (cl-form-validation.js) auto-binds every form on
    // the page, so we no longer need to wire blur/input listeners here.

    var steps = $$('.cl-step', form);
    if (steps.length < 2) return; // nothing to step through

    var nav   = $('[data-cl-stepper-nav]', form);
    var prevBtn = $('[data-cl-stepper-prev]', form);
    var nextBtn = $('[data-cl-stepper-next]', form);
    var submitBtn = $('[data-cl-stepper-submit]', form);
    var stepCounter = $('[data-cl-stepper-counter]', form);

    var current = 0;

    function dispatch(name, detail) {
      try { form.dispatchEvent(new CustomEvent('cl-stepper:' + name, { detail: detail || {}, bubbles: true })); } catch (_) {}
    }

    function render() {
      steps.forEach(function (s, i) {
        s.classList.toggle('is-active', i === current);
        s.setAttribute('aria-hidden', i === current ? 'false' : 'true');
      });
      if (nav) {
        $$('.cl-stepper-dot', nav).forEach(function (dot, i) {
          dot.classList.toggle('is-active', i === current);
          dot.classList.toggle('is-done', i < current);
          dot.setAttribute('aria-current', i === current ? 'step' : 'false');
        });
      }
      if (prevBtn) prevBtn.disabled = (current === 0);
      var isLast = current === steps.length - 1;
      if (nextBtn) nextBtn.style.display = isLast ? 'none' : '';
      if (submitBtn) submitBtn.style.display = isLast ? '' : 'none';
      if (stepCounter) stepCounter.textContent = (current + 1) + ' / ' + steps.length;

      // Auto-populate review step (any element with data-cl-review-for="<input-name>")
      var activeStep = steps[current];
      if (activeStep && activeStep.hasAttribute('data-step-review')) {
        populateReview(activeStep);
        dispatch('reachreview', { stepIndex: current });
      }

      // Scroll the form into view so the user sees the new step header
      try { form.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (_) {}
    }

    function populateReview(reviewStep) {
      $$('[data-cl-review-for]', reviewStep).forEach(function (slot) {
        var fieldName = slot.dataset.clReviewFor;
        var formatter = slot.dataset.clReviewFormat || 'text';
        var value = collectFieldValue(fieldName, formatter);
        slot.textContent = value || '—';
        slot.classList.toggle('is-empty', !value);
      });
    }

    function collectFieldValue(fieldName, formatter) {
      var els = $$('[name="' + fieldName + '"]', form);
      if (!els.length) return '';
      var el = els[0];
      // checkbox
      if (el.type === 'checkbox') {
        return el.checked ? (el.dataset.reviewYes || 'Yes') : (el.dataset.reviewNo || 'No');
      }
      // multi-select
      if (el.tagName === 'SELECT' && el.multiple) {
        return Array.from(el.selectedOptions).map(function (o) { return o.textContent.trim(); }).join(', ');
      }
      // single select
      if (el.tagName === 'SELECT') {
        var opt = el.selectedOptions[0];
        return opt ? opt.textContent.trim() : '';
      }
      // datetime-local — render as readable date+time
      if (el.type === 'datetime-local' && el.value) {
        if (formatter === 'date') {
          try {
            var d = new Date(el.value);
            return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
          } catch (_) { return el.value; }
        }
      }
      // file input
      if (el.type === 'file') {
        return el.files && el.files[0] ? el.files[0].name : '';
      }
      return el.value || '';
    }

    function go(to) {
      if (to < 0 || to >= steps.length) return;
      if (to > current) {
        // Forward navigation: validate every step from current up to one
        // before the target so users can't skip required fields with
        // dot-clicks.
        for (var i = current; i < to; i++) {
          if (!isStepValid(steps[i])) { go(i); return; }
        }
      }
      var from = current;
      current = to;
      render();
      dispatch('change', { from: from, to: to, total: steps.length });
    }

    if (prevBtn) prevBtn.addEventListener('click', function (e) {
      e.preventDefault();
      go(current - 1);
    });
    if (nextBtn) nextBtn.addEventListener('click', function (e) {
      e.preventDefault();
      if (!isStepValid(steps[current])) return;
      go(current + 1);
    });

    // Step-dot clicks (only allow going back, or forward if every prior
    // step is valid — handled inside go())
    if (nav) {
      $$('.cl-stepper-dot', nav).forEach(function (dot, i) {
        dot.addEventListener('click', function (e) {
          e.preventDefault();
          go(i);
        });
      });
    }

    // Enter key on a non-textarea input advances to next step, doesn't
    // submit the form prematurely
    form.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      var t = e.target;
      if (!t || t.tagName === 'TEXTAREA' || t.tagName === 'BUTTON') return;
      if (current < steps.length - 1) {
        e.preventDefault();
        if (isStepValid(steps[current])) go(current + 1);
      }
    });

    // Final submit — re-validate every step in source order so the user
    // can't land on review with a back-history-edited DOM state
    form.addEventListener('submit', function (e) {
      for (var i = 0; i < steps.length; i++) {
        if (steps[i].hasAttribute('data-step-review')) continue;
        if (!isStepValid(steps[i])) {
          e.preventDefault();
          go(i);
          return;
        }
      }
      // Let Bootstrap finish its own `was-validated` pass
      form.classList.add('was-validated');
    });

    render();
  }

  function init() {
    $$('form[data-cl-stepper]').forEach(attach);
  }

  window.ClStepper = {
    __loaded: true,
    bind: attach,
    rebind: function () { init(); }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.addEventListener('cm:navigated', init);
})();
