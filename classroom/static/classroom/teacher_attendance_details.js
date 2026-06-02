    // Initialize DataTable for teacher attendance table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const attendanceTable = document.querySelector('.teacher-attendance-table');
      if (attendanceTable && !$.fn.DataTable.isDataTable(attendanceTable)) {
        $(attendanceTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  