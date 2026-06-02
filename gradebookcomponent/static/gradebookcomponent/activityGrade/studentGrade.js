    // Initialize DataTable for student grade table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const gradeTable = document.querySelector('.student-grade-table');
      if (gradeTable && !$.fn.DataTable.isDataTable(gradeTable)) {
        $(gradeTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  