    // Initialize DataTable for activity type table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const typeTable = document.querySelector('.activity-type-table');
      if (typeTable && !$.fn.DataTable.isDataTable(typeTable)) {
        $(typeTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  