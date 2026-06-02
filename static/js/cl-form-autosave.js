(function () {
  'use strict';
  if (window.ClFormAutosave && window.ClFormAutosave.__loaded) return;

  var TTL_MS = 7 * 24 * 60 * 60 * 1000;
  var SAVE_DEBOUNCE_MS = 600;
  var KEY_PREFIX = 'cl:draft:';

  function userId() {
    var b = document.body;
    return (b && b.dataset && b.dataset.currentUserId) || 'anon';
  }

  function storageKey(formId) {
    return KEY_PREFIX + formId + ':' + userId();
  }

  function isPersistable(el) {
    if (!el || !el.name) return false;
    if (el.disabled) return false;
    var t = (el.type || '').toLowerCase();
    if (t === 'hidden' || t === 'file' || t === 'password') return false;
    if (t === 'submit' || t === 'button' || t === 'reset' || t === 'image') return false;
    if (el.dataset && el.dataset.clNoAutosave === '1') return false;
    return true;
  }

  function serialize(form) {
    var out = {};
    Array.from(form.elements).forEach(function (el) {
      if (!el.name || el.disabled) return;
      var t = (el.type || '').toLowerCase();
      if (t === 'file') {
        if (el.files && el.files[0]) out['file:' + el.name] = el.files[0].name;
        return;
      }
      if (!isPersistable(el)) return;
      if (t === 'checkbox') {
        out['cb:' + el.name + ':' + (el.value || 'on')] = !!el.checked;
      } else if (t === 'radio') {
        if (el.checked) out['r:' + el.name] = el.value;
      } else if (el.tagName === 'SELECT' && el.multiple) {
        out['ms:' + el.name] = Array.from(el.selectedOptions).map(function (o) { return o.value; });
      } else {
        out[el.name] = el.value;
      }
    });
    return out;
  }

  function hasMeaningfulData(fields, form) {
    var changed = false;
    Object.keys(fields).forEach(function (k) {
      if (changed) return;
      if (k.indexOf('file:') === 0) {
        if (fields[k]) changed = true;
      } else if (k.indexOf('cb:') === 0) {
        var p = k.split(':');
        var el = form.querySelector('input[type="checkbox"][name="' + p[1] + '"][value="' + p[2] + '"]')
          || form.querySelector('input[type="checkbox"][name="' + p[1] + '"]');
        if (el && el.defaultChecked !== fields[k]) changed = true;
      } else if (k.indexOf('ms:') === 0) {
        var name = k.slice(3);
        var sel = form.querySelector('select[multiple][name="' + name + '"]');
        if (!sel) return;
        var defaults = Array.from(sel.options).filter(function (o) { return o.defaultSelected; }).map(function (o) { return o.value; }).sort();
        var saved = (fields[k] || []).slice().sort();
        if (saved.length !== defaults.length || saved.some(function (v, i) { return v !== defaults[i]; })) changed = true;
      } else if (k.indexOf('r:') === 0) {
        var rname = k.slice(2);
        var rs = form.querySelectorAll('input[type="radio"][name="' + rname + '"]');
        var defVal = '';
        rs.forEach(function (r) { if (r.defaultChecked) defVal = r.value; });
        if (defVal !== fields[k]) changed = true;
      } else {
        var els = form.querySelectorAll('[name="' + k + '"]');
        if (!els.length) return;
        var first = els[0];
        if (first.tagName === 'SELECT') {
          var defOpt = Array.from(first.options).find(function (o) { return o.defaultSelected; });
          var defV = defOpt ? defOpt.value : (first.options[0] ? first.options[0].value : '');
          if (defV !== fields[k]) changed = true;
        } else if (typeof first.defaultValue === 'string') {
          if (first.defaultValue !== (fields[k] || '')) changed = true;
        } else if (fields[k]) {
          changed = true;
        }
      }
    });
    return changed;
  }

  function syncChoices(selectEl, vals) {
    if (selectEl._clChoices && typeof selectEl._clChoices.setChoiceByValue === 'function') {
      try {
        selectEl._clChoices.removeActiveItems();
        Array.from(selectEl.options).forEach(function (o) { o.selected = vals.indexOf(o.value) !== -1; });
        if (vals.length) selectEl._clChoices.setChoiceByValue(vals);
        return true;
      } catch (_) { return false; }
    }
    return false;
  }

  function showFileHint(fileInput, filename) {
    if (!fileInput || !fileInput.parentElement) return;
    var existing = fileInput.parentElement.querySelector('.cl-autosave-file-hint');
    if (existing) existing.remove();

    var hint = document.createElement('div');
    hint.className = 'cl-autosave-file-hint';
    hint.innerHTML = '<i class="fas fa-paperclip" aria-hidden="true"></i> Your draft had: <strong></strong> — please re-attach this file.';
    hint.querySelector('strong').textContent = filename;
    fileInput.parentElement.appendChild(hint);

    fileInput.addEventListener('change', function () {
      if (fileInput.files && fileInput.files[0] && hint.parentElement) hint.remove();
    }, { once: true });
  }

  function restore(form, fields) {
    var multiSelectRestores = [];
    var singleChoiceRestores = [];
    Object.keys(fields).forEach(function (k) {
      if (k.indexOf('file:') === 0) {
        var fname = k.slice(5);
        var fi = form.querySelector('input[type="file"][name="' + fname + '"]');
        if (fi) showFileHint(fi, fields[k]);
        return;
      }
      if (k.indexOf('cb:') === 0) {
        var p = k.split(':');
        var el = form.querySelector('input[type="checkbox"][name="' + p[1] + '"][value="' + p[2] + '"]')
          || form.querySelector('input[type="checkbox"][name="' + p[1] + '"]');
        if (el) {
          el.checked = !!fields[k];
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
      } else if (k.indexOf('ms:') === 0) {
        var name = k.slice(3);
        var sel = form.querySelector('select[multiple][name="' + name + '"]');
        if (!sel) return;
        var vals = fields[k] || [];
        Array.from(sel.options).forEach(function (o) { o.selected = vals.indexOf(o.value) !== -1; });
        multiSelectRestores.push({ sel: sel, vals: vals });
      } else if (k.indexOf('r:') === 0) {
        var rname = k.slice(2);
        var rs = form.querySelectorAll('input[type="radio"][name="' + rname + '"]');
        rs.forEach(function (r) {
          r.checked = (r.value === fields[k]);
          if (r.checked) r.dispatchEvent(new Event('change', { bubbles: true }));
        });
      } else {
        var els = form.querySelectorAll('[name="' + k + '"]');
        if (!els.length) return;
        var first = els[0];
        first.value = fields[k];
        if (first.tagName === 'SELECT' && !first.multiple) {
          first.dispatchEvent(new Event('change', { bubbles: true }));
          if (first.classList.contains('js-choice')) {
            singleChoiceRestores.push({ sel: first, val: fields[k] });
          }
        } else {
          first.dispatchEvent(new Event('input', { bubbles: true }));
          first.dispatchEvent(new Event('change', { bubbles: true }));
        }
      }
    });
    multiSelectRestores.forEach(function (r) {
      if (!syncChoices(r.sel, r.vals)) {
        r.sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    singleChoiceRestores.forEach(function (r) {
      if (r.sel._clChoices && typeof r.sel._clChoices.setChoiceByValue === 'function') {
        try { r.sel._clChoices.setChoiceByValue(r.val); } catch (_) {}
      }
    });
  }

  function clearDraft(key) {
    try { localStorage.removeItem(key); } catch (_) {}
  }

  function load(key) {
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.savedAt) return null;
      if (Date.now() - data.savedAt > TTL_MS) {
        clearDraft(key);
        return null;
      }
      return data;
    } catch (_) { return null; }
  }

  function save(key, fields, step) {
    try {
      localStorage.setItem(key, JSON.stringify({
        savedAt: Date.now(),
        step: step || 0,
        fields: fields
      }));
    } catch (_) {}
  }

  function relativeTime(savedAt) {
    var diff = Date.now() - savedAt;
    var min = Math.floor(diff / 60000);
    if (min < 1) return 'just now';
    if (min < 60) return min + ' min ago';
    var hr = Math.floor(min / 60);
    if (hr < 24) return hr + ' hour' + (hr > 1 ? 's' : '') + ' ago';
    var day = Math.floor(hr / 24);
    return day + ' day' + (day > 1 ? 's' : '') + ' ago';
  }

  function currentStep(form) {
    var steps = form.querySelectorAll('.cl-step');
    for (var i = 0; i < steps.length; i++) {
      if (steps[i].classList.contains('is-active')) return i;
    }
    return 0;
  }

  function jumpToStep(form, step) {
    if (typeof step !== 'number' || step <= 0) return;
    var dots = form.querySelectorAll('[data-cl-stepper-nav] .cl-stepper-dot');
    if (!dots.length || step >= dots.length) return;
    setTimeout(function () { try { dots[step].click(); } catch (_) {} }, 50);
  }

  function showBanner(form, draft, onRestore, onDiscard) {
    var banner = document.createElement('div');
    banner.className = 'cl-autosave-banner';
    banner.setAttribute('role', 'status');
    banner.innerHTML =
      '<div class="cl-autosave-banner-text">' +
        '<i class="fas fa-clock-rotate-left" aria-hidden="true"></i>' +
        '<span><strong>We saved your progress!</strong> Pick up where you left off?' +
          ' <span class="cl-autosave-banner-time">Last edited ' + relativeTime(draft.savedAt) + '</span></span>' +
      '</div>' +
      '<div class="cl-autosave-banner-actions">' +
        '<button type="button" class="cl-autosave-btn cl-autosave-btn-ghost" data-cl-autosave-discard>Discard</button>' +
        '<button type="button" class="cl-autosave-btn cl-autosave-btn-primary" data-cl-autosave-restore>Restore</button>' +
      '</div>';

    var anchor = form.querySelector('.cl-stepper-head') || form.firstElementChild || form;
    form.insertBefore(banner, anchor);

    function dismiss() {
      banner.classList.add('is-dismissing');
      setTimeout(function () { if (banner.parentElement) banner.parentElement.removeChild(banner); }, 220);
    }

    banner.querySelector('[data-cl-autosave-restore]').addEventListener('click', function () {
      onRestore();
      dismiss();
    });
    banner.querySelector('[data-cl-autosave-discard]').addEventListener('click', function () {
      onDiscard();
      dismiss();
    });
  }

  function deriveFormId(form) {
    if (form.dataset.clAutosave) return form.dataset.clAutosave;
    var action = form.getAttribute('action') || window.location.pathname || 'form';
    try { action = new URL(action, window.location.origin).pathname; } catch (_) {}
    return action.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-+|-+$/g, '') || 'form';
  }

  function attach(form) {
    if (!form || form.__clAutosaveBound) return;
    form.__clAutosaveBound = true;

    if (form.hasAttribute('data-cl-no-autosave')) return;
    var hasExplicit = form.hasAttribute('data-cl-autosave');
    var isStepper = form.hasAttribute('data-cl-stepper');
    if (!hasExplicit && !isStepper) return;

    var formId = deriveFormId(form);
    var key = storageKey(formId);

    var existing = load(key);
    var prompted = false;
    if (existing && existing.fields && hasMeaningfulData(existing.fields, form)) {
      prompted = true;
      showBanner(form, existing,
        function () {
          restore(form, existing.fields);
          jumpToStep(form, existing.step);
        },
        function () { clearDraft(key); }
      );
    }

    var saveTimer = null;
    function flush() {
      clearTimeout(saveTimer);
      saveTimer = null;
      save(key, serialize(form), currentStep(form));
    }
    function scheduleSave() {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(flush, SAVE_DEBOUNCE_MS);
    }

    form.addEventListener('input', scheduleSave);
    form.addEventListener('change', scheduleSave);

    Array.from(form.querySelectorAll('select')).forEach(function (sel) {
      sel.addEventListener('addItem', flush);
      sel.addEventListener('removeItem', flush);
    });

    Array.from(form.querySelectorAll('input[type="file"]')).forEach(function (fi) {
      fi.addEventListener('change', flush);
    });

    form.addEventListener('cl-stepper:change', function (e) {
      clearTimeout(saveTimer);
      var step = (e.detail && typeof e.detail.to === 'number') ? e.detail.to : currentStep(form);
      save(key, serialize(form), step);
    });

    form.addEventListener('submit', function () {
      clearDraft(key);
    });

    function flushOnHide() { if (saveTimer) flush(); }
    window.addEventListener('pagehide', flushOnHide);
    window.addEventListener('beforeunload', flushOnHide);
  }

  function init() {
    Array.from(document.querySelectorAll('form[data-cl-autosave], form[data-cl-stepper]')).forEach(attach);
  }

  window.ClFormAutosave = { __loaded: true, bind: attach, clear: clearDraft };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  window.addEventListener('cm:navigated', init);
})();
