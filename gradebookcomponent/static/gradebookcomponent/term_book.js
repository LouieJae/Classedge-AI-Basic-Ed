  document.querySelectorAll('[data-tb-filter]').forEach(input => {
    input.addEventListener('input', function () {
      const term = this.value.trim().toLowerCase();
      document.querySelectorAll('table.gb-table tbody tr[data-search]').forEach(r => {
        r.style.display = !term || (r.dataset.search || '').includes(term) ? '' : 'none';
      });
    });
  });