    // Initialize DataTable for subject report table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const subjTable = document.querySelector('.subject-report-table');
      if (subjTable && !$.fn.DataTable.isDataTable(subjTable)) {
        $(subjTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  