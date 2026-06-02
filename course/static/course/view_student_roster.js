    document.addEventListener('DOMContentLoaded', function() {
      // Set default date values (last 7 days)
      const today = new Date();
      const lastWeek = new Date();
      lastWeek.setDate(today.getDate() - 6); // 7 days including today
      
      // Format dates as YYYY-MM-DD for input fields
      document.getElementById('end_date').value = formatDate(today);
      document.getElementById('start_date').value = formatDate(lastWeek);
      
      // Validate date range before form submission
      document.getElementById('exportAttendanceForm').addEventListener('submit', function(e) {
        const startDate = new Date(document.getElementById('start_date').value);
        const endDate = new Date(document.getElementById('end_date').value);
        
        if (startDate > endDate) {
          e.preventDefault();
          alert('Start date cannot be after end date');
        }
      });
    });
    
    function formatDate(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    }
  

    // Initialize DataTable for student roster table with safeguard
    document.addEventListener('DOMContentLoaded', function() {
      const rosterTable = document.querySelector('.student-roster-table');
      if (rosterTable && !$.fn.DataTable.isDataTable(rosterTable)) {
        $(rosterTable).DataTable({
          responsive: true,
          autoWidth: false,
          paging: true,
          searching: true,
          ordering: true,
          pageLength: 10
        });
      }
    });
  