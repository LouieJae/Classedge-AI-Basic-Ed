  document.addEventListener('DOMContentLoaded', function () {
    // Replace any underscores in status labels with spaces.
    document.querySelectorAll('.status-text').forEach(function (el) {
      el.textContent = el.textContent.replace(/_/g, ' ');
    });

    // Make the date input use the design-system styling.
    var dateInput = document.querySelector('input[name="date"]');
    if (dateInput) {
      dateInput.classList.add('form-control'); // for legacy CSS that targets it
      dateInput.id = dateInput.id || 'id_date';
      dateInput.required = true;
    }

    // Quick "mark all as" chips
    document.querySelectorAll('.selectAll').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var sid = btn.getAttribute('data-status');
        document.querySelectorAll('.status-' + sid).forEach(function (radio) {
          if (radio.closest('tr').style.display === 'none') return; // skip filtered-out rows
          radio.checked = true;
        });
        updateMarkedCount();
      });
    });

    // Search filter
    var filter = document.getElementById('taFilter');
    var rows = Array.prototype.slice.call(document.querySelectorAll('#taTable tbody tr.ta-row'));
    if (filter) {
      filter.addEventListener('input', function () {
        var q = filter.value.trim().toLowerCase();
        rows.forEach(function (row) {
          var name = row.getAttribute('data-name') || '';
          row.style.display = (!q || name.indexOf(q) !== -1) ? '' : 'none';
        });
      });
    }

    // Marked-count summary
    function updateMarkedCount() {
      var counter = document.getElementById('taMarkedCount');
      if (!counter) return;
      var marked = 0;
      rows.forEach(function (row) {
        var checked = row.querySelector('input[type="radio"]:checked');
        if (checked) marked++;
      });
      counter.textContent = marked;
    }
    document.addEventListener('change', function (e) {
      if (e.target && e.target.matches('input[type="radio"][name^="status_"]')) {
        e.target.closest('tr').classList.remove('is-missing');
        updateMarkedCount();
      }
    });
    updateMarkedCount();

    // Submit validation
    var form = document.getElementById('attendanceForm');
    var alertBox = document.getElementById('taAlert');
    if (form) {
      form.addEventListener('submit', function (e) {
        var ok = true;
        if (dateInput && !dateInput.value) ok = false;
        rows.forEach(function (row) {
          if (row.style.display === 'none') return;
          var checked = row.querySelector('input[type="radio"]:checked');
          if (!checked) {
            ok = false;
            row.classList.add('is-missing');
          } else {
            row.classList.remove('is-missing');
          }
        });
        if (!ok) {
          e.preventDefault();
          if (alertBox) alertBox.classList.add('is-on');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        } else if (alertBox) {
          alertBox.classList.remove('is-on');
        }
      });
    }
  });