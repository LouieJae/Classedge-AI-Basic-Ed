    // Initialize DataTable for teacher attendance list table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const attendanceListTable = document.querySelector('.teacher-attendance-list-table');
      if (attendanceListTable && !$.fn.DataTable.isDataTable(attendanceListTable)) {
        $(attendanceListTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  