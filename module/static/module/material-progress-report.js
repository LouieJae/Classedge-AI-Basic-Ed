  document.addEventListener('DOMContentLoaded', function () {
    /* Media skeleton wiring lives in static/js/cl-media-skeleton.js
       (loaded globally via base_operation.html). Any element with
       [data-skeleton] on this page is auto-bound by that engine. */

    /* Fullscreen handling for PDF & image */
    function bindFullscreen(btnId, targetId, opts) {
      const btn = document.getElementById(btnId);
      const target = document.getElementById(targetId);
      if (!btn || !target) return;
      const isPdf = opts && opts.pdf;
      btn.addEventListener('click', function () {
        if (!document.fullscreenElement) {
          if (isPdf) {
            const base = target.dataset.baseSrc || target.src.split('#')[0];
            target.src = base;
          }
          (target.requestFullscreen || target.webkitRequestFullscreen || target.msRequestFullscreen)?.call(target);
          btn.innerHTML = '<i class="fas fa-compress"></i> Exit fullscreen';
        } else {
          document.exitFullscreen();
        }
      });
    }
    document.addEventListener('fullscreenchange', function () {
      const pdfBtn = document.getElementById('pdf-fullscreen-btn');
      const imgBtn = document.getElementById('image-fullscreen-btn');
      if (!document.fullscreenElement) {
        if (pdfBtn) pdfBtn.innerHTML = '<i class="fas fa-expand"></i> Fullscreen';
        if (imgBtn) imgBtn.innerHTML = '<i class="fas fa-expand"></i> Fullscreen';
      }
    });
    bindFullscreen('pdf-fullscreen-btn', 'pdf-file', { pdf: true });
    bindFullscreen('image-fullscreen-btn', 'image-file');

    /* Stats + search */
    const list = document.getElementById('vspProgressList');
    if (list) {
      const rows = Array.from(list.querySelectorAll('.vsp-progress-row'));
      const noMatch = document.getElementById('vspNoMatch');
      let complete = 0, inProgress = 0, sum = 0;
      rows.forEach(r => {
        const p = parseFloat(r.dataset.progress) || 0;
        sum += p;
        if (p >= 100) complete++;
        else if (p > 0) inProgress++;
      });
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set('vspStatComplete', complete);
      set('vspStatInProgress', inProgress);
      set('vspStatAvg', rows.length ? Math.round(sum / rows.length) + '%' : '—');

      const search = document.getElementById('vspSearch');
      if (search) {
        search.addEventListener('input', function () {
          const qRaw = search.value.trim();
          const q = qRaw.toLowerCase();
          let visible = 0;
          rows.forEach(r => {
            const match = !q || (r.dataset.name || '').includes(q);
            r.style.display = match ? '' : 'none';
            if (match) {
              visible++;
              if (window.ClHighlight) window.ClHighlight.wrap(r, qRaw);
            } else if (window.ClHighlight) {
              window.ClHighlight.clear(r);
            }
          });
          if (noMatch) noMatch.style.display = (q && visible === 0) ? '' : 'none';
        });
      }
    }
  });