  document.addEventListener("DOMContentLoaded", function () {
    // Select-all helper for checkbox groups (kept for backwards compat)
    const selectAllCheckboxes = document.querySelectorAll(".selectAllCheckbox");
    selectAllCheckboxes.forEach(selectAll => {
      selectAll.addEventListener("change", function () {
        const targetGroup = document.querySelectorAll(`.${this.dataset.target} .selectCheckbox`);
        targetGroup.forEach(checkbox => { checkbox.checked = this.checked; });
      });
    });
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrfToken = getCookie('csrftoken');

  // Shared SweetAlert2 confirm-then-submit helper for inline delete forms.
  // Returns false to halt native submit; resubmits the form on confirmation
  // with __gbConfirmed set so this handler skips the second pass.
  function gbSwalConfirmSubmit(event, form, title, text) {
    if (form.__gbConfirmed) return true;
    if (event && event.preventDefault) event.preventDefault();
    if (typeof Swal === 'undefined') return window.confirm(title);
    const isDark = document.body.dataset.theme === 'dark';
    Swal.fire({
      title: title,
      text: text || "This action cannot be undone.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, delete',
      cancelButtonText: 'Cancel',
      reverseButtons: true,
      focusCancel: true,
      background: isDark ? '#1a2420' : '#ffffff',
      color: isDark ? '#e8eaf0' : '#2d3142',
      confirmButtonColor: '#b02a37',
      cancelButtonColor: isDark ? '#3a4540' : '#e5e1d8',
      customClass: {
        popup: 'cl-swal-popup',
        confirmButton: 'cl-swal-confirm',
        cancelButton: 'cl-swal-cancel'
      }
    }).then(function (result) {
      if (result.isConfirmed) {
        form.__gbConfirmed = true;
        form.submit();
      }
    });
    return false;
  }

  function confirmGradeBookDelete(id) {
    Swal.fire({
      title: 'Are you sure?',
      text: "You won't be able to revert this!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
      if (result.isConfirmed) {
        fetch(`/delete-grade-book/${id}/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken }
        })
          .then(response => response.json())
          .then(data => {
            if (data.status === 'success') {
              Swal.fire("Deleted!", data.message || "Gradebook component deleted.", "success");
              setTimeout(() => location.reload(), 1500);
            }
          })
          .catch(error => console.error('Error:', error));
      }
    });
  }

  function confirmTermBookDelete(id) {
    Swal.fire({
      title: 'Are you sure?',
      text: "You won't be able to revert this!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
      if (result.isConfirmed) {
        fetch(`/delete-term-book/${id}/`, {
          method: 'POST',
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
          }
        })
        .then(response => {
          if (!response.ok) { throw new Error("CSRF token missing or invalid"); }
          return response.json();
        })
        .then(data => {
          Swal.fire("Deleted!", "Termbook has been deleted.", "success");
          setTimeout(() => location.reload(), 1500);
        })
        .catch(error => console.error("Error:", error));
      }
    });
  }

  // Calculate and display total percentages for termbooks
  document.querySelectorAll('[class*="total-percentage-"]').forEach(function(element) {
    const raw = element.getAttribute('data-termbooks');
    if (!raw) return;
    const termbooks = JSON.parse(raw);
    const total = termbooks.reduce((sum, percentage) => sum + parseFloat(percentage), 0);
    element.textContent = total.toFixed(0) + '%';
    if (total === 100) {
      element.classList.add('text-success');
    } else if (total > 100) {
      element.classList.add('text-danger');
    } else {
      element.classList.add('text-warning');
    }
  });

  // Initialize DataTables
  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.termbook-table').forEach(function(table) {
      if (!$.fn.DataTable.isDataTable(table)) {
        $(table).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
    document.querySelectorAll('.gradebook-table').forEach(function(table) {
      if (!$.fn.DataTable.isDataTable(table)) {
        $(table).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  });

  // Client-side filter for gradebook/termbook search inputs
  document.querySelectorAll('[data-gb-filter]').forEach(input => {
    input.addEventListener('input', function () {
      const term = this.value.trim().toLowerCase();
      const root = document.querySelector(this.dataset.gbFilter);
      if (!root) return;
      root.querySelectorAll('.gb-accordion-item').forEach(item => {
        const rows = item.querySelectorAll('tr[data-search]');
        let anyMatch = false;
        rows.forEach(r => {
          const match = !term || (r.dataset.search || '').includes(term);
          r.style.display = match ? '' : 'none';
          if (match) anyMatch = true;
        });
        item.style.display = anyMatch || !term ? '' : 'none';
      });
    });
  });