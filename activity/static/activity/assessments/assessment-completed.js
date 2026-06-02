  (function () {
    const el = document.querySelector('.ac-progress');
    if (!el) return;
    const score = parseFloat(el.dataset.score) || 0;
    const max = parseFloat(el.dataset.max) || 0;
    const pct = max > 0 ? Math.max(0, Math.min(100, (score / max) * 100)) : 0;

    // Color tier
    if (pct >= 75) el.classList.add('high');
    else if (pct >= 50) el.classList.add('mid');
    else el.classList.add('low');

    // Animate the ring (circumference = 2 * π * 75 ≈ 471)
    const C = 471;
    const offset = C - (pct / 100) * C;
    requestAnimationFrame(() => {
      el.querySelector('.bar').style.strokeDashoffset = offset.toFixed(2);
    });

    // Percentage labels
    const pctText = pct.toFixed(0) + '%';
    const pctEl = el.querySelector('[data-pct-text]');
    const statEl = document.querySelector('[data-pct-stat]');
    if (pctEl) pctEl.textContent = pctText;
    if (statEl) statEl.textContent = pctText;
  })();