  window.MathJax = {
    tex: { inlineMath: [['\\(', '\\)'], ['$', '$']], displayMath: [['\\[', '\\]'], ['$$', '$$']] },
    options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'] }
  };

  document.addEventListener("DOMContentLoaded", function () {
    // Score circle ring (single-student mode)
    document.querySelectorAll('.sga-score-circle').forEach(function (circle) {
      const score = parseFloat(circle.getAttribute('data-score'));
      const max = parseFloat(circle.getAttribute('data-max'));
      const passing = parseFloat(circle.getAttribute('data-passing')) || 0;
      if (isNaN(score) || isNaN(max) || max <= 0) return;
      const pct = Math.max(0, Math.min(100, (score / max) * 100));
      const styles = getComputedStyle(circle);
      const ringColor = (passing > 0 && score < passing)
        ? styles.getPropertyValue('--sga-coral')
        : styles.getPropertyValue('--sga-success');
      const surface2 = styles.getPropertyValue('--sga-surface-2');
      circle.style.background = `conic-gradient(${ringColor.trim()} 0% ${pct}%, ${surface2.trim()} ${pct}% 100%)`;
    });

    // Roster mode interactivity
    const tbody = document.getElementById('sgaTbody');
    if (tbody) {
      // Compute summary stats
      (function computeStats() {
        const rows = Array.from(tbody.querySelectorAll('.sga-row'));
        if (!rows.length) return;
        let sum = 0, max = 0, passing = 0, totalEvaluated = 0;
        rows.forEach((r) => {
          const s = parseFloat(r.dataset.score);
          const m = parseFloat(r.dataset.max);
          const p = parseFloat(r.dataset.passing) || 0;
          if (!isNaN(s)) sum += s;
          if (!isNaN(s) && s > max) max = s;
          if (p > 0) {
            totalEvaluated++;
            if (s >= p) passing++;
          }
        });
        const avg = (sum / rows.length).toFixed(2);
        const setStat = (k, v) => {
          const el = document.querySelector(`[data-stat="${k}"]`);
          if (el) el.textContent = v;
        };
        setStat('avg', avg);
        setStat('top', max.toFixed(2));
        if (totalEvaluated > 0) {
          const rate = ((passing / totalEvaluated) * 100).toFixed(0);
          setStat('passrate', rate + '%');
          setStat('passrate-sub', `${passing} of ${totalEvaluated} passed`);
        } else {
          setStat('passrate', '—');
          setStat('passrate-sub', 'no passing threshold');
        }
      })();

      // Click row to toggle detail panel
      tbody.querySelectorAll('.sga-row').forEach((row) => {
        row.addEventListener('click', (e) => {
          if (e.target.closest('a, button.sga-expand-btn')) return;
          toggleRow(row);
        });
        const btn = row.querySelector('.sga-expand-btn');
        if (btn) btn.addEventListener('click', (e) => { e.stopPropagation(); toggleRow(row); });
      });
      function toggleRow(row) {
        const id = row.dataset.rowId;
        const detail = document.querySelector(`.sga-detail-row[data-detail-for="${id}"]`);
        if (!detail) return;
        const isOpen = row.classList.toggle('expanded');
        detail.classList.toggle('show', isOpen);
      }

      // Search filter
      const search = document.getElementById('sgaSearch');
      if (search) {
        search.addEventListener('input', () => {
          const q = search.value.trim().toLowerCase();
          tbody.querySelectorAll('.sga-row').forEach((row) => {
            const name = (row.dataset.name || '').toLowerCase();
            const show = !q || name.includes(q);
            row.style.display = show ? '' : 'none';
            const id = row.dataset.rowId;
            const detail = document.querySelector(`.sga-detail-row[data-detail-for="${id}"]`);
            if (detail && !show) {
              detail.classList.remove('show');
              row.classList.remove('expanded');
              detail.style.display = 'none';
            } else if (detail) {
              detail.style.display = '';
            }
          });
        });
      }

      // Column sorting
      const table = document.getElementById('sgaTable');
      const sortableThs = table.querySelectorAll('th[data-sort-key]');
      sortableThs.forEach((th) => {
        th.addEventListener('click', () => {
          const key = th.dataset.sortKey;
          const current = th.getAttribute('aria-sort');
          const dir = current === 'ascending' ? 'descending' : 'ascending';
          sortableThs.forEach((other) => other.removeAttribute('aria-sort'));
          th.setAttribute('aria-sort', dir);

          const rows = Array.from(tbody.querySelectorAll('.sga-row'));
          const details = new Map();
          rows.forEach((r) => {
            const det = tbody.querySelector(`.sga-detail-row[data-detail-for="${r.dataset.rowId}"]`);
            if (det) details.set(r, det);
          });

          rows.sort((a, b) => {
            let av, bv;
            if (key === 'name')      { av = a.dataset.name.toLowerCase(); bv = b.dataset.name.toLowerCase(); return av.localeCompare(bv) * (dir === 'ascending' ? 1 : -1); }
            if (key === 'score')     { av = parseFloat(a.dataset.score) || 0; bv = parseFloat(b.dataset.score) || 0; return (av - bv) * (dir === 'ascending' ? 1 : -1); }
            if (key === 'time')      { av = parseInt(a.dataset.time, 10) || 0; bv = parseInt(b.dataset.time, 10) || 0; return (av - bv) * (dir === 'ascending' ? 1 : -1); }
            if (key === 'result')    {
              const order = { pass: 0, pending: 1, fail: 2 };
              av = order[a.querySelector('[data-result]')?.dataset.result] ?? 99;
              bv = order[b.querySelector('[data-result]')?.dataset.result] ?? 99;
              return (av - bv) * (dir === 'ascending' ? 1 : -1);
            }
            return 0;
          });

          // Re-append in new order, with detail rows following each main row
          rows.forEach((r) => {
            tbody.appendChild(r);
            const det = details.get(r);
            if (det) tbody.appendChild(det);
          });
        });
      });
    }

    if (typeof MathJax !== "undefined") {
      setTimeout(() => { MathJax.typesetPromise().catch(() => {}); }, 500);
    }
  });