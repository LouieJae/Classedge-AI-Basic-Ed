    (function () {
      const table = document.getElementById('cslTable');
      if (!table) return;
      const rows = Array.from(table.tBodies[0].rows);
      const search = document.getElementById('cslSearch');
      const chips = document.querySelectorAll('#cslChips .csl-chip');
      const emptyFiltered = document.getElementById('cslEmptyFiltered');
      let activeStatus = 'all';

      // Compute status counts once
      const statusCounts = {};
      rows.forEach(r => {
        const s = r.dataset.status || '';
        statusCounts[s] = (statusCounts[s] || 0) + 1;
      });
      // Update [data-count-status] elements (in chips + stat strip)
      document.querySelectorAll('[data-count-status]').forEach(el => {
        el.textContent = statusCounts[el.dataset.countStatus] || 0;
      });

      function applyFilter() {
        const qRaw = (search.value || '').trim();
        const q = qRaw.toLowerCase();
        let visible = 0;
        rows.forEach(r => {
          const matchesStatus = activeStatus === 'all' || r.dataset.status === activeStatus;
          const matchesSearch = !q || r.dataset.search.includes(q);
          const show = matchesStatus && matchesSearch;
          r.classList.toggle('is-hidden', !show);
          if (show) {
            visible++;
            if (window.ClHighlight) window.ClHighlight.wrap(r, qRaw);
          } else if (window.ClHighlight) {
            window.ClHighlight.clear(r);
          }
        });
        emptyFiltered.style.display = visible === 0 && rows.length > 0 ? '' : 'none';
        table.style.display = visible === 0 ? 'none' : '';
      }

      chips.forEach(c => c.addEventListener('click', () => {
        chips.forEach(x => x.classList.remove('active'));
        c.classList.add('active');
        activeStatus = c.dataset.status;
        applyFilter();
      }));
      search.addEventListener('input', applyFilter);
    })();
  