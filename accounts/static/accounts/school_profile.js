    document.addEventListener('DOMContentLoaded', function () {
      // Reparent modals to <body> so position:fixed anchors to the viewport.
      ['logoModal','logoModalBackdrop','nameModal','nameModalBackdrop'].forEach(id => {
        const el = document.getElementById(id);
        if (el) document.body.appendChild(el);
      });

      function show(id, bd) {
        document.getElementById(id).classList.add('show');
        document.getElementById(bd).classList.add('show');
      }
      function hide(id, bd) {
        document.getElementById(id).classList.remove('show');
        document.getElementById(bd).classList.remove('show');
      }

      document.getElementById('openLogoModal').addEventListener('click', () => show('logoModal', 'logoModalBackdrop'));
      document.getElementById('closeLogoModalBtn').addEventListener('click', () => hide('logoModal', 'logoModalBackdrop'));
      document.getElementById('cancelLogoBtn').addEventListener('click', () => hide('logoModal', 'logoModalBackdrop'));
      document.getElementById('logoModalBackdrop').addEventListener('click', () => hide('logoModal', 'logoModalBackdrop'));

      document.getElementById('openNameModal').addEventListener('click', () => show('nameModal', 'nameModalBackdrop'));
      document.getElementById('closeNameModalBtn').addEventListener('click', () => hide('nameModal', 'nameModalBackdrop'));
      document.getElementById('cancelNameBtn').addEventListener('click', () => hide('nameModal', 'nameModalBackdrop'));
      document.getElementById('nameModalBackdrop').addEventListener('click', () => hide('nameModal', 'nameModalBackdrop'));

      document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        ['logoModal', 'nameModal'].forEach(id => {
          const m = document.getElementById(id);
          if (m && m.classList.contains('show')) hide(id, id + 'Backdrop');
        });
      });
    });
  

/* ═══════════════════════════════════════════════════════════════
   Theme customizer — preset swatches + hex input wired to a live
   --brand-primary preview. Saving persists via POST; cancelling
   resets the input to the server-rendered value.
   ═══════════════════════════════════════════════════════════════ */
(function () {
  var form = document.getElementById('brandColorForm');
  if (!form) return;

  var swatches = form.querySelectorAll('.sp-brand-swatch');
  var picker   = document.getElementById('brand_color_picker');
  var hexInput = document.getElementById('brand_color_hex');
  var resetBtn = document.getElementById('brandResetBtn');

  // Remember the server-rendered value so Reset can return to it.
  var initialHex = (hexInput.value || '#1b4332').toLowerCase();

  function normalize(hex) {
    if (!hex) return '';
    hex = hex.trim();
    if (hex.charAt(0) !== '#') hex = '#' + hex;
    return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(hex) ? hex.toLowerCase() : '';
  }

  function applyPreview(hex) {
    // Inject (or update) a dedicated <style> that beats the tenant
    // <style data-cl-brand-tenant> via later source order. Removed on
    // Reset so the saved value re-asserts.
    var existing = document.querySelector('style[data-cl-brand-preview]');
    if (!hex) {
      if (existing) existing.remove();
      return;
    }
    if (!existing) {
      existing = document.createElement('style');
      existing.setAttribute('data-cl-brand-preview', '');
      document.head.appendChild(existing);
    }
    existing.textContent =
      ':root, body[data-theme="light"], body[data-theme="dark"], body[data-theme] { ' +
      '--brand-primary: ' + hex + '; }';
  }

  function setActiveSwatch(hex) {
    var match = hex ? hex.toLowerCase() : '';
    swatches.forEach(function (sw) {
      var on = (sw.dataset.brandHex || '').toLowerCase() === match;
      sw.classList.toggle('is-active', on);
      sw.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function updateAll(hex, opts) {
    opts = opts || {};
    var norm = normalize(hex);
    if (!norm) return;
    if (!opts.skipPicker) picker.value = norm;
    if (!opts.skipHex)    hexInput.value = norm.toUpperCase();
    applyPreview(norm);
    setActiveSwatch(norm);
  }

  swatches.forEach(function (sw) {
    sw.addEventListener('click', function () {
      updateAll(sw.dataset.brandHex);
    });
  });

  picker.addEventListener('input', function () {
    updateAll(picker.value, { skipPicker: true });
  });

  hexInput.addEventListener('input', function () {
    var norm = normalize(hexInput.value);
    if (norm) updateAll(norm, { skipHex: true });
  });

  resetBtn.addEventListener('click', function () {
    updateAll(initialHex);
    applyPreview(null);  // strip the preview <style> so the saved value wins
  });
})();
