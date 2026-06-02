  (function () {
    const nameInput = document.getElementById('id_name');
    const descInput = document.getElementById('id_description');
    const iconInput = document.getElementById('id_icon');
    const tierInput = document.getElementById('id_tier');
    const previewIcon = document.getElementById('bePreviewIcon');
    const previewName = document.getElementById('bePreviewName');
    const previewDesc = document.getElementById('bePreviewDesc');
    const previewTier = document.getElementById('bePreviewTier');

    function bindLive(input, target, mode) {
      if (!input || !target) return;
      input.addEventListener('input', () => {
        const v = input.value;
        if (mode === 'tier-text') {
          target.textContent = (v || '').toUpperCase();
          target.className = 'be-preview-tier ' + (v || '').toLowerCase();
        } else {
          target.textContent = v || (mode === 'desc' ? '—' : (input.placeholder || ''));
        }
      });
    }
    bindLive(nameInput, previewName);
    bindLive(descInput, previewDesc, 'desc');
    bindLive(iconInput, previewIcon);
    if (tierInput) {
      tierInput.addEventListener('change', () => {
        previewTier.textContent = tierInput.value.toUpperCase();
        previewTier.className = 'be-preview-tier ' + tierInput.value.toLowerCase();
      });
    }
  })();